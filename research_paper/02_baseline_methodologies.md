# Section 4: Experimental Methodologies & Mathematical Formulations

This document details the exact mathematical formulations, algorithmic implementations, metric definitions, and inference parameters governing the baseline architectures in the **HALO** research framework.

---

## 1. Mathematical Formulations of Baselines

Let $\mathcal{C} = \{p_1, p_2, \dots, p_N\}$ denote the unified legal retrieval corpus of $N = 2,773$ passages.  
Let $q$ denote a user legal query.  
Let $\mathcal{M}_{\theta}$ denote the frozen foundational Large Language Model (`qwen/qwen3.8-27b`).

```text
+-----------------------------------------------------------------------------------------+
|                               BASELINE ARCHITECTURES OVERVIEW                           |
+-------------------+---------------------------------------------------------------------+
| BASELINE          | ARCHITECTURAL DATA FLOW PIPELINE                                    |
+-------------------+---------------------------------------------------------------------+
| Baseline 1 (B1)   | q ──────────────────────────────────────────────> [LLM] ───> y      |
| Baseline 2 (B2)   | q ───> [Dense Encoder: BGE-Large] ──> Top-5 ──> [LLM] ───> y      |
| Baseline 3 (B3)   | q ───> [Sparse Lexical: BM25Okapi] ─> Top-5 ──> [LLM] ───> y      |
| Baseline 4 (B4)   | q ───> [Dense + BM25] ──> [RRF Fusion] ───> Top-5 ─> [LLM] ───> y   |
| Baseline 5 (B5)   | q ───> [Dense + BM25] ──> [RRF] ──> [Reranker] ──> Top-5 ──> [LLM]  |
| HALO (Proposed)   | Dual-Layer Hybrid ──> Verification ──> Fail-Closed Governor ──> [LLM]|
+-------------------+---------------------------------------------------------------------+
```

---

### 1.1 Baseline 1: Pure Parametric Generation (No Retrieval, $K = 0$)
In Baseline 1, the model relies solely on its pre-trained parametric weights $\theta$ to answer legal queries without external statutory context:
$$P(Y \mid q; \theta) = \prod_{t=1}^T P(y_t \mid y_{<t}, q; \theta)$$
* **Context Prompt**: Standard standardized corporate legal expert persona prompt without external text.
* **Purpose**: Serves as the control baseline to measure pre-trained hallucination rates and verify whether retrieval is even necessary.

---

### 1.2 Baseline 2: Dense Vector RAG ($K = 5$, `BAAI/bge-large-en-v1.5`)
Baseline 2 introduces dense bi-encoder vector retrieval:
1. **Query & Passage Encoding**:
   Both queries and passages are projected into a continuous semantic vector space $\mathbb{R}^D$ where $D = 1,024$:
   $$v_q = E_{\phi}(q_{\text{instruct}}), \quad v_p = E_{\phi}(p)$$
   where $q_{\text{instruct}} = \text{"Represent this sentence for searching relevant passages: "} \circ q$.
2. **$L_2$ Normalization**:
   All vectors are normalized onto the unit hypersphere:
   $$\hat{v}_q = \frac{v_q}{\|v_q\|_2}, \quad \hat{v}_p = \frac{v_p}{\|v_p\|_2}, \quad \|\hat{v}\|_2 = 1.0$$
3. **Retrieval Scoring (Cosine Similarity)**:
   The relevance score is computed as the inner product:
   $$s_{\text{dense}}(q, p) = \hat{v}_q^\top \hat{v}_p \in [-1.0, 1.0]$$
4. **Top-$K$ Selection**:
   $$\mathcal{R}_{\text{dense}}(q) = \operatorname{arg\,top-}K_{p \in \mathcal{C}} \left( s_{\text{dense}}(q, p) \right), \quad K = 5$$
5. **Context-Augmented Generation**:
   $$P(Y \mid q, \mathcal{R}_{\text{dense}}(q); \theta) = \prod_{t=1}^T P(y_t \mid y_{<t}, q, \mathcal{R}_{\text{dense}}(q); \theta)$$

---

### 1.3 Baseline 3: Sparse Lexical RAG ($K = 5$, `BM25Okapi`)
Baseline 3 isolates the exact contribution of sparse inverted-index term matching.
1. **Legal-Aware Tokenization**:
   Legal text is tokenized into tokens $\mathcal{T}(q)$ using regex preserving section markers, sub-sections, and currency while filtering standard English stopwords but strictly protecting statutory operators:
   $$\text{Stopwords}_{\text{protected}} = \{\text{shall}, \text{must}, \text{may}, \text{not}, \text{no}, \text{without}, \text{proviso}, \text{omitted}, \text{substituted}\}$$
2. **Okapi BM25 Relevance Scoring**:
   For each passage $p \in \mathcal{C}$, the BM25 score is computed as:
   $$s_{\text{BM25}}(q, p) = \sum_{t \in \mathcal{T}(q) \cap \mathcal{T}(p)} \text{IDF}(t) \cdot \frac{f(t, p) \cdot (k_1 + 1)}{f(t, p) + k_1 \cdot \left(1 - b + b \cdot \frac{|p|}{\text{avgdl}}\right)}$$
   where:
   * $f(t, p)$ is the term frequency of token $t$ in passage $p$.
   * $|p|$ is passage length in tokens, and $\text{avgdl} = \frac{1}{|\mathcal{C}|} \sum_{p \in \mathcal{C}} |p|$.
   * Protocol hyperparameters: $k_1 = 1.5$, $b = 0.75$, $\epsilon = 0.25$.
   * The Inverse Document Frequency with smoothing is:
     $$\text{IDF}(t) = \ln \left( \frac{N - n(t) + 0.5}{n(t) + 0.5} + 1 \right)$$
     where $N = 2,773$ and $n(t)$ is the number of passages containing token $t$.
3. **Deterministic Tie-Breaking Top-$K$ Selection**:
   $$\mathcal{R}_{\text{BM25}}(q) = \operatorname{arg\,top-}K_{p \in \mathcal{C}} \left( s_{\text{BM25}}(q, p), -p.\text{passage\_id} \right), \quad K = 5$$
4. **Context-Augmented Generation**:
   $$P(Y \mid q, \mathcal{R}_{\text{BM25}}(q); \theta) = \prod_{t=1}^T P(y_t \mid y_{<t}, q, \mathcal{R}_{\text{BM25}}(q); \theta)$$

---

### 1.4 Baseline 4: Hybrid RAG (Dense + BM25 via Reciprocal Rank Fusion, $k = 60$)
Baseline 4 integrates dense semantic representations with sparse inverted-index term matching using pure rank-based fusion to isolate the value of retriever complementarity without learned reranking or score calibration.

1. **Dual Candidate Retrieval ($K_m = 5$)**:
   For query $q$, the system queries the dense vector index and sparse BM25 index concurrently:
   $$\mathcal{R}_{\text{dense}}(q) = \operatorname{arg\,top-}K_{p \in \mathcal{C}}(s_{\text{dense}}(q, p)), \quad \mathcal{R}_{\text{BM25}}(q) = \operatorname{arg\,top-}K_{p \in \mathcal{C}}(s_{\text{BM25}}(q, p))$$
   Each candidate list yields 1-indexed ranks $\text{rank}_m(p, q) \in \{1, 2, \dots, K\}$ where $K = 5$.

2. **Reciprocal Rank Fusion (RRF, $k = 60$)**:
   To circumvent score incomparability across cosine similarity $[-1, 1]$ and unbounded BM25 scores $[0, \infty)$, fusion is computed purely on candidate rank positions with standard constant $k = 60$:
   $$s_{\text{RRF}}(p, q) = \sum_{m \in \{\text{dense}, \text{bm25}\}} \frac{\mathbb{I}(p \in \mathcal{R}_K^m(q))}{60 + \text{rank}_m(p, q)}$$
   * If passage $p$ appears in both retrieval lists at ranks $r_{\text{dense}}, r_{\text{BM25}}$:
     $$s_{\text{RRF}}(p, q) = \frac{1}{60 + r_{\text{dense}}} + \frac{1}{60 + r_{\text{BM25}}}$$
     (Maximal agreement score: $r_1=1, r_2=1 \implies \frac{2}{61} \approx 0.032787$)
   * If passage $p$ appears in only one retriever at rank $r$, the missing retriever contributes $0.0$:
     $$s_{\text{RRF}}(p, q) = \frac{1}{60 + r}$$

3. **Deterministic Tie-Breaking & Top-$K$ Selection**:
   Fused candidates are sorted in descending order by RRF score, with ties strictly broken by lexicographical passage ID:
   $$\mathcal{R}_{\text{hybrid}}(q) = \operatorname{arg\,top-}K_{p \in \mathcal{R}_{\text{dense}} \cup \mathcal{R}_{\text{BM25}}} \left( s_{\text{RRF}}(p, q), -p.\text{passage\_id} \right), \quad K = 5$$

4. **Context-Augmented Generation**:
   $$P(Y \mid q, \mathcal{R}_{\text{hybrid}}(q); \theta) = \prod_{t=1}^T P(y_t \mid y_{<t}, q, \mathcal{R}_{\text{hybrid}}(q); \theta)$$

---

### 1.5 Baseline 5: Hybrid RAG + Cross-Encoder Reranking (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
Baseline 5 introduces a deep sequence cross-encoder downstream of the frozen dual-channel retrieval pool to determine whether full cross-attention over query-passage token pairs resolves the lexical distractor vulnerability of unweighted RRF fusion while preserving grounded generation.

1. **Frozen Upstream Candidate Pool ($\mathcal{U}_K(q), K \le 10$)**:
   To enforce a strictly controlled single-variable ablation, the candidate pool submitted to the cross-encoder is identical to the union of Top-5 Dense and Top-5 BM25 retrievers from Baseline 4:
   $$\mathcal{U}_K(q) = \mathcal{R}_{\text{dense}}^5(q) \cup \mathcal{R}_{\text{BM25}}^5(q), \quad 5 \le |\mathcal{U}_K(q)| \le 10$$
   Crucially, the upstream candidate budget is strictly bounded at $K \le 10$ unique passages (zero expansion to Top-20), isolating the pure mathematical contribution of cross-attention reranking from candidate pool enlargement.

2. **Cross-Attention Sequence Scoring**:
   Unlike bi-encoders which compute independent embedding vectors $\hat{v}_q$ and $\hat{v}_p$, the cross-encoder evaluates the concatenated sequence under full self-attention across all transformer layers:
   $$\mathbf{x}_{q, p} = [\text{CLS}] \circ q \circ [\text{SEP}] \circ p \circ [\text{SEP}]$$
   $$\mathbf{H} = \text{Transformer}(\mathbf{x}_{q, p}) \in \mathbb{R}^{L \times d}$$
   where the backbone is `cross-encoder/ms-marco-MiniLM-L-6-v2` ($L=6$ layers, $d=384$ hidden dimension, 12 attention heads). The classification head projects the $[\text{CLS}]$ representation to emit an uncalibrated scalar relevance logit:
   $$s_{\text{CE}}(q, p) = \mathbf{W}_{\text{cls}} \mathbf{h}_{[\text{CLS}]} + b_{\text{cls}} \in (-\infty, +\infty)$$
   Full cross-attention enables every token in the statutory query to attend directly to every token in the passage text, capturing intricate legal syntax, statutory provisos, and jurisdictional qualifiers that bi-encoder dot products and unweighted RRF compress away.

3. **Deterministic Tie-Breaking & Final Top-$K$ Selection ($K=5$)**:
   Candidate passages in $\mathcal{U}_K(q)$ are sorted in descending order by cross-encoder logit, with identical scores broken deterministically by ascending alphanumeric passage ID:
   $$\mathcal{R}_{\text{rerank}}(q) = \operatorname{arg\,top-}K_{p \in \mathcal{U}_K(q)} \left( s_{\text{CE}}(q, p), -p.\text{passage\_id} \right), \quad K = 5$$

4. **Context-Augmented Generation**:
   $$P(Y \mid q, \mathcal{R}_{\text{rerank}}(q); \theta) = \prod_{t=1}^T P(y_t \mid y_{<t}, q, \mathcal{R}_{\text{rerank}}(q); \theta)$$

5. **Single-Variable Controlled Invariance**:
   Cross-encoder reranking is the sole intended experimental difference between B4 and B5, with all upstream retrieval, candidate pool, prompt, generation, corpus, and evaluation variables invariant. All downstream reasoning, verification, and fail-closed governing modules remain strictly disabled.

---

## 2. Mathematical Formalization of Evaluation Metrics

### 2.1 Retrieval Evaluation Metrics (Families D3-A, D3-B, D3-C)

Let $\mathcal{G}(q)$ denote the set of ground-truth relevant passage IDs for query $q$.  
Let $\mathcal{R}_K(q) = [r_1, r_2, \dots, r_K]$ denote the ranked list of top-$K$ retrieved passage IDs.

* **Recall@$K$**:
  $$\text{Recall@}K(q) = \frac{|\mathcal{R}_K(q) \cap \mathcal{G}(q)|}{|\mathcal{G}(q)|}$$
  $$\text{Macro Recall@}K = \frac{1}{|Q|} \sum_{q \in Q} \text{Recall@}K(q)$$

* **Hit Rate@$K$ (Success Rate)**:
  $$\text{Hit@}K(q) = \mathbb{I}\left(|\mathcal{R}_K(q) \cap \mathcal{G}(q)| > 0\right)$$
  $$\text{Macro Hit Rate@}K = \frac{1}{|Q|} \sum_{q \in Q} \text{Hit@}K(q)$$

* **Mean Reciprocal Rank (MRR)**:
  $$\text{RR}(q) = \begin{cases} \frac{1}{\min \{ k \mid r_k \in \mathcal{G}(q) \}}, & \text{if } \mathcal{R}_K(q) \cap \mathcal{G}(q) \neq \emptyset \\ 0, & \text{otherwise} \end{cases}$$
  $$\text{MRR} = \frac{1}{|Q|} \sum_{q \in Q} \text{RR}(q)$$

* **Hard-Negative Fallback Acceptance Rate (HNFAR on Family D3-C)**:
  Let $\mathcal{H}(q)$ denote the set of adversarial hard-negative distractor passage IDs.
  $$\text{HNFAR}(q) = \mathbb{I}\left( \mathcal{R}_K(q) \cap \mathcal{H}(q) \neq \emptyset \land \mathcal{R}_K(q) \cap \mathcal{G}(q) = \emptyset \right)$$
  Measures the rate at which the retriever falls into the adversarial distractor trap without retrieving the gold provision.

---

### 2.2 Grounding and Answer Quality Metrics (Family D3-D)

Let $\mathcal{A}(q) = \{a_1, a_2, \dots, a_m\}$ denote the canonical acceptable answer points (atomic legal facts) required for complete compliance.  
Let $\mathcal{U}(q) = \{u_1, u_2, \dots, u_k\}$ denote unacceptable legal claims (explicit statutory misconceptions or false legal statements).  
Let $\hat{y}$ denote the model's generated answer text.

* **Atomic Fact Precision/Recall (AFPR)**:
  $$\text{AFPR}(\hat{y}, q) = \frac{\sum_{i=1}^m \mathbb{I}(\hat{y} \models a_i)}{m}$$
  where $\hat{y} \models a_i$ denotes semantic factual entailment of acceptable point $a_i$ by the generated answer.

* **Complete Answer Rate**:
  $$\text{CompleteRate} = \frac{1}{|Q|} \sum_{q \in Q} \mathbb{I}\left( \sum_{i=1}^m \mathbb{I}(\hat{y} \models a_i) = m \right)$$
  Measures the percentage of answers that capture 100% of all required statutory elements.

* **Hallucination / Unsupported Claim Rate**:
  $$\text{HallucinationRate} = \frac{1}{|Q|} \sum_{q \in Q} \mathbb{I}\left( \exists u_j \in \mathcal{U}(q) : \hat{y} \models u_j \right)$$
  Measures the percentage of generated answers asserting a legally unacceptable or fabricated claim.

---

## 3. Standardized LLM Generation Configuration

To maintain strict scientific comparability, the generative model and inference hyper-parameters are fixed across all baselines:

```json
{
  "provider": "groq",
  "model_name": "qwen/qwen3.8-27b",
  "temperature": 0.0,
  "top_p": 1.0,
  "max_tokens": 512,
  "seed": 42,
  "system_prompt": "You are HALO, an authoritative legal intelligence system specializing in Indian Corporate Law, the Companies Act, 2013, and landmark precedents of the Supreme Court of India and NCLAT. Provide accurate, precise, and legally sound answers based on the authoritative evidence provided. Avoid speculation, cite specific sections where applicable, and state clearly when evidence is insufficient."
}
```
Zero temperature ensures deterministic token decoding across all experimental runs.
