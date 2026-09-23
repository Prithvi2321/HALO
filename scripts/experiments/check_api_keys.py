import os
import json
import urllib.request
import urllib.error

raw_env_keys = os.environ.get("GROQ_API_KEYS", "") or os.environ.get("GROQ_API_KEY", "")
keys = [(f"Key {i+1}", k.strip()) for i, k in enumerate(raw_env_keys.split(",")) if k.strip()]
if not keys:
    keys = [("Default Env Key", os.environ.get("GROQ_API_KEY", ""))]

url = "https://api.groq.com/openai/v1/chat/completions"

results = []

for name, k in keys:
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
        "temperature": 0.0
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {k}",
            "Content-Type": "application/json",
            "User-Agent": "HALO-KeyCheck/1.0"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            headers = dict(resp.headers)
            rem_req = headers.get("x-ratelimit-remaining-requests", "N/A")
            lim_req = headers.get("x-ratelimit-limit-requests", "N/A")
            rem_tok = headers.get("x-ratelimit-remaining-tokens", "N/A")
            lim_tok = headers.get("x-ratelimit-limit-tokens", "N/A")
            res_req = headers.get("x-ratelimit-reset-requests", "N/A")
            res_tok = headers.get("x-ratelimit-reset-tokens", "N/A")
            results.append({
                "name": name,
                "key_preview": k[:10] + "..." + k[-4:],
                "status": "ACTIVE / READY",
                "remaining_requests": rem_req,
                "limit_requests": lim_req,
                "remaining_tokens": rem_tok,
                "limit_tokens": lim_tok,
                "reset_requests_in": res_req,
                "reset_tokens_in": res_tok,
                "cooldown": "0s (Ready immediately)"
            })
    except urllib.error.HTTPError as e:
        headers = dict(e.headers) if hasattr(e, "headers") and e.headers else {}
        rem_req = headers.get("x-ratelimit-remaining-requests", "0")
        lim_req = headers.get("x-ratelimit-limit-requests", "N/A")
        rem_tok = headers.get("x-ratelimit-remaining-tokens", "0")
        lim_tok = headers.get("x-ratelimit-limit-tokens", "N/A")
        retry_after = headers.get("retry-after", "N/A")
        res_req = headers.get("x-ratelimit-reset-requests", "N/A")
        res_tok = headers.get("x-ratelimit-reset-tokens", "N/A")
        results.append({
            "name": name,
            "key_preview": k[:10] + "..." + k[-4:],
            "status": f"RATE LIMITED ({e.code})",
            "remaining_requests": rem_req,
            "limit_requests": lim_req,
            "remaining_tokens": rem_tok,
            "limit_tokens": lim_tok,
            "reset_requests_in": res_req,
            "reset_tokens_in": res_tok,
            "cooldown": f"{retry_after}s" if retry_after != "N/A" else "Cooling down"
        })
    except Exception as ex:
        results.append({
            "name": name,
            "key_preview": k[:10] + "..." + k[-4:],
            "status": f"ERROR: {str(ex)}",
            "remaining_requests": "N/A",
            "limit_requests": "N/A",
            "remaining_tokens": "N/A",
            "limit_tokens": "N/A",
            "reset_requests_in": "N/A",
            "reset_tokens_in": "N/A",
            "cooldown": "Unknown"
        })

print(json.dumps(results, indent=2))
