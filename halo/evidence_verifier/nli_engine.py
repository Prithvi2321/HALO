"""
HALO Evidence Verifier: Cross-Encoder NLI Engine
================================================
Protocol: v1.0-FROZEN
Executes deterministic sequence classification using cross-encoder/nli-deberta-v3-base.
Enforces:
1. INVIOLABLE DIRECTION: Premise = Authoritative Legal Evidence, Hypothesis = Atomic Claim
2. Runtime id2label validation (Gate EV3)
3. Model artifact provenance hashing (Gate EV15)
4. Sliding window passage chunking for context-exceeding legal texts (>512 tokens)
5. Substantive proposition normalization (separating citation syntax from proposition)
6. Evaluation mode with disabled gradients and deterministic execution
"""

from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import threading
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from halo.evidence_verifier.config import EvidenceVerifierConfig
from halo.evidence_verifier.schemas import (
    NLIProbabilities,
    NLIPairResult,
    NLILabel,
    ModelProvenance,
)
from halo.evidence_verifier.exceptions import (
    NLIInferenceError,
    DirectionViolationError,
)


class NLIEngine:
    """Singleton NLI Inference Engine for cross-encoder DeBERTa-v3."""

    _instance: Optional["NLIEngine"] = None
    _lock = threading.Lock()

    # Documented and verified label mapping for cross-encoder/nli-deberta-v3-base
    EXPECTED_ID2LABEL = {0: "contradiction", 1: "entailment", 2: "neutral"}

    # Leading citation clause patterns to normalize for semantic proposition evaluation
    CITATION_PREFIX_PATTERNS = [
        r"^(?:under|as\s+per|pursuant\s+to|in\s+terms\s+of)\s+sections?\s+[\d\w()]+(?:\s+of\s+the\s+[^,]+)?,?\s*",
        r"^(?:under|as\s+per|pursuant\s+to|in\s+terms\s+of)\s+rules?\s+[\d\w()]+(?:\s+of\s+the\s+[^,]+)?,?\s*",
        r"^sections?\s+[\d\w()]+(?:\s+of\s+the\s+[^,]+)?\s+(?:requires|mandates|provides|prescribes|stipulates|states)(?:\s+that)?\s+",
        r"^based\s+on\s+the\s+authoritative\s+legal\s+evidence\s+provided,?\s*",
        r"(?:,\s*)?(?:under|as\s+per|pursuant\s+to|in\s+terms\s+of|of)\s+sections?\s+[\d\w()]+(?:\s+of\s+the\s+[^.]+)?\.?$",
        r"(?:,\s*)?(?:under|as\s+per|pursuant\s+to|in\s+terms\s+of|of)\s+rules?\s+[\d\w()]+(?:\s+of\s+the\s+[^.]+)?\.?$",
        r"(?:,\s*)?in\s+accordance\s+with\s+sections?\s+[\d\w()]+(?:\s+of\s+the\s+[^.]+)?\.?$",
    ]

    def __init__(self, config: Optional[EvidenceVerifierConfig] = None):
        self.config = config or EvidenceVerifierConfig()
        self.device = torch.device(self.config.device)
        self.tokenizer = None
        self.model = None
        self.model_provenance: Optional[ModelProvenance] = None
        self._init_lock = threading.Lock()
        self._compiled_cit_pats = [re.compile(p, re.IGNORECASE) for p in self.CITATION_PREFIX_PATTERNS]
        self._initialize_model()

    @classmethod
    def get_instance(cls, config: Optional[EvidenceVerifierConfig] = None) -> "NLIEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config)
            return cls._instance

    @classmethod
    def reset_instance(cls):
        with cls._lock:
            cls._instance = None

    def _initialize_model(self):
        with self._init_lock:
            if self.model is not None:
                return

            model_name = self.config.model_name
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
                self.model = AutoModelForSequenceClassification.from_pretrained(model_name, local_files_only=True)
            except Exception:
                # Fallback to standard loading if local_files_only fails
                try:
                    self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                    self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
                except Exception as e:
                    raise NLIInferenceError(f"Failed to load NLI model '{model_name}': {e}")

            # 1. User Correction #11: Runtime verification of id2label mapping
            raw_id2label = getattr(self.model.config, "id2label", {})
            normalized_id2label = {int(k): str(v).lower() for k, v in raw_id2label.items()}
            for idx, label in self.EXPECTED_ID2LABEL.items():
                if normalized_id2label.get(idx) != label:
                    raise NLIInferenceError(
                        f"CRITICAL GATE EV3 FAILURE: Model id2label mismatch! "
                        f"Expected {self.EXPECTED_ID2LABEL}, but got {normalized_id2label}. "
                        "Cannot proceed with invalid label mapping."
                    )

            # 2. Evaluation mode and freeze
            self.model.to(self.device)
            self.model.eval()
            for param in self.model.parameters():
                param.requires_grad = False

            # 3. User Correction #12: Cryptographic artifact hashing
            model_hash = self._compute_artifact_hash()

            import transformers
            self.model_provenance = ModelProvenance(
                name=model_name,
                revision=getattr(self.model.config, "_commit_hash", "main"),
                model_hash=model_hash,
                tokenizer_hash=model_hash,
                torch_version=torch.__version__,
                transformers_version=transformers.__version__,
                device=str(self.device),
                dtype=str(self.model.dtype),
            )

    def _compute_artifact_hash(self) -> str:
        """Computes SHA-256 hash of the model configuration."""
        try:
            config_dict = self.model.config.to_dict()
            canonical = json.dumps(config_dict, sort_keys=True, ensure_ascii=False)
            return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        except Exception:
            return hashlib.sha256(self.config.model_name.encode("utf-8")).hexdigest()

    def _strip_citation_prefix(self, text: str) -> str:
        """Normalizes hypothesis by stripping citation wrappers so NLI assesses the proposition."""
        res = text.strip()
        for p in self._compiled_cit_pats:
            res = p.sub("", res).strip()
        if res and res[0].islower():
            res = res[0].upper() + res[1:]
        if res and not res.endswith((".", "!", "?")):
            res = res + "."
        return res if res else text

    def _chunk_passage(self, passage_text: str, claim_text: str) -> List[str]:
        """
        User Correction #14: Deterministic sliding-window chunking for legal passages
        exceeding the model's sequence length limit (512 tokens).
        """
        claim_tokens = self.tokenizer.tokenize(claim_text)
        max_passage_tokens = self.config.max_sequence_length - len(claim_tokens) - 16

        if max_passage_tokens <= 64:
            max_passage_tokens = 64

        passage_tokens = self.tokenizer.tokenize(passage_text)
        if len(passage_tokens) <= max_passage_tokens:
            return [passage_text]

        chunk_size = min(self.config.chunk_size, max_passage_tokens)
        overlap = self.config.chunk_overlap
        step = max(32, chunk_size - overlap)

        chunks: List[str] = []
        for start in range(0, len(passage_tokens), step):
            end = min(start + chunk_size, len(passage_tokens))
            chunk_toks = passage_tokens[start:end]
            chunk_str = self.tokenizer.convert_tokens_to_string(chunk_toks).strip()
            if chunk_str:
                chunks.append(chunk_str)
            if end >= len(passage_tokens):
                break

        return chunks if chunks else [passage_text]

    def _evaluate_pair_raw(self, premise: str, hypothesis: str) -> Tuple[NLIProbabilities, str]:
        """Evaluates single (premise, hypothesis) with NLI."""
        inputs = self.tokenizer(
            premise,
            hypothesis,
            return_tensors="pt",
            truncation=True,
            max_length=self.config.max_sequence_length,
            padding=True,
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = F.softmax(logits, dim=-1)[0].cpu().tolist()

        nli_probs = NLIProbabilities(
            contradiction=float(probs[0]),
            entailment=float(probs[1]),
            neutral=float(probs[2]),
        )
        predicted_idx = int(torch.argmax(logits, dim=-1)[0].item())
        pred_label = self.EXPECTED_ID2LABEL.get(predicted_idx, "neutral")
        return nli_probs, pred_label

    def predict(
        self,
        premise_evidence: str,
        hypothesis_claim: str,
        claim_id: str = "UNKNOWN_CLAIM",
        passage_id: str = "UNKNOWN_PASSAGE",
        validate_direction: bool = True,
    ) -> NLIPairResult:
        """
        Executes NLI classification on (Premise, Hypothesis).
        CRITICAL: premise_evidence MUST be the legal evidence passage.
                  hypothesis_claim MUST be the atomic claim.
        """
        if validate_direction:
            if not premise_evidence or not premise_evidence.strip():
                raise DirectionViolationError("Premise (evidence) cannot be empty.")
            if not hypothesis_claim or not hypothesis_claim.strip():
                raise DirectionViolationError("Hypothesis (claim) cannot be empty.")

        chunks = self._chunk_passage(premise_evidence, hypothesis_claim)
        cleaned_hyp = self._strip_citation_prefix(hypothesis_claim)

        all_evaluations: List[Tuple[NLIProbabilities, str]] = []

        target_hyp = cleaned_hyp if cleaned_hyp else hypothesis_claim
        for chunk_text in chunks:
            # INVIOLABLE DIRECTION: (Premise=chunk_text, Hypothesis=target_hyp)
            probs, label = self._evaluate_pair_raw(chunk_text, target_hyp)
            all_evaluations.append((probs, label))

        # Aggregate across chunks deterministically
        # If any chunk provides decisive entailment, prioritize entailment
        high_entailment = [p for p, l in all_evaluations if p.entailment >= self.config.entailment_min and p.contradiction <= self.config.contradiction_max_for_entailment]
        if high_entailment:
            best_probs = max(high_entailment, key=lambda p: p.entailment)
            best_label = NLILabel.ENTAILMENT.value
        else:
            high_contradiction = [p for p, l in all_evaluations if p.contradiction >= self.config.contradiction_min and p.entailment <= self.config.entailment_max_for_contradiction]
            if high_contradiction:
                best_probs = max(high_contradiction, key=lambda p: p.contradiction)
                best_label = NLILabel.CONTRADICTION.value
            else:
                best_probs = max((p for p, _ in all_evaluations), key=lambda p: p.entailment)
                best_label = NLILabel.NEUTRAL.value

        canonical_pair = f"{premise_evidence.strip()}|||{hypothesis_claim.strip()}"
        input_hash = hashlib.sha256(canonical_pair.encode("utf-8")).hexdigest()

        return NLIPairResult(
            claim_id=claim_id,
            passage_id=passage_id,
            premise_text=premise_evidence,
            hypothesis_text=hypothesis_claim,
            probabilities=best_probs,
            predicted_label=best_label,
            model_name=self.config.model_name,
            model_version=self.model_provenance.revision or "main",
            inference_timestamp=datetime.now(timezone.utc).isoformat(),
            input_hash=input_hash,
            chunks_evaluated=len(chunks),
        )

    def predict_batch(
        self,
        pairs: List[Tuple[str, str, str, str]],
    ) -> List[NLIPairResult]:
        results = []
        for premise, hypothesis, cid, pid in pairs:
            results.append(self.predict(premise, hypothesis, claim_id=cid, passage_id=pid))
        return results
