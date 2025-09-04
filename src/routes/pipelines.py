from flask import Blueprint, request, jsonify
import os, requests, uuid, time
from concurrent.futures import ThreadPoolExecutor, as_completed

pipelines_bp = Blueprint("pipelines", __name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

def call_llm(model, messages, temp=0.7, top_p=0.95, max_tokens=1200, timeout=90):
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY missing")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {"model": model, "messages": messages, "temperature": temp, "top_p": top_p, "max_tokens": max_tokens}
    r = requests.post(OPENROUTER_URL, headers=headers, json=body, timeout=timeout)
    r.raise_for_status()
    j = r.json()
    return j["choices"][0]["message"]["content"]

def summarize_with_gpt5(title, prompt, traces, gpt5_model="openai/gpt-5"):
    bullets = []
    for t in traces:
        bullets.append(f"- [{t['agent']}] {t['last_text'][:900]}")
    msg = (
        f"You are a senior editor. Title: {title}\n"
        f"Original prompt:\n{prompt}\n\n"
        f"Below are outputs from multiple agents. Remove redundancy, resolve conflicts, and produce a concise, well-structured report with sections, bullet points, and a short exec summary.:\n\n"
        + "\n".join(bullets)
    )
    return call_llm(gpt5_model, [{"role":"system","content":"Concise, structured, no fluff."},
                                 {"role":"user","content":msg}], temp=0.2, max_tokens=1600)

@pipelines_bp.route("/api/pipelines/pairs-run", methods=["POST"])
def pairs_run():
    """
    Body: {
      "prompt": "...",
      "pairs": [["modelA","modelB"], ... up to 10],
      "rounds": 3,
      "system": "You are ...",            # optional system
      "aggregator_model": "openai/gpt-5"  # optional
    }
    """
    data = request.get_json(force=True) or {}
    prompt = data.get("prompt","").strip()
    pairs  = data.get("pairs") or []
    rounds = int(data.get("rounds") or 3)
    sysmsg = data.get("system") or "Be rigorous, cite assumptions, keep responses tight."
    agg    = data.get("aggregator_model") or "openai/gpt-5"
    if not prompt or not pairs:
        return jsonify({"error":"prompt and pairs[] required"}), 400

    # Run debates in parallel
    traces = []
    def run_pair(ai, bi):
        msg = [{"role":"system","content":sysmsg},{"role":"user","content":prompt}]
        a_last, b_last = "", ""
        for r in range(rounds):
            a_last = call_llm(ai, msg)
            msg.append({"role":"assistant","content":a_last})
            msg.append({"role":"user","content":"Respond to the above, challenge assumptions briefly."})
            b_last = call_llm(bi, msg)
            msg.append({"role":"assistant","content":b_last})
            msg.append({"role":"user","content":"Short rebuttal to the last point."})
        return [
            {"agent": ai, "last_text": a_last},
            {"agent": bi, "last_text": b_last},
        ]

    with ThreadPoolExecutor(max_workers=min(10, len(pairs))) as ex:
        futs = [ex.submit(run_pair, a, b) for a, b in pairs[:10]]
        for f in as_completed(futs):
            for item in f.result():
                traces.append(item)

    report = summarize_with_gpt5("Pairs Debate Report", prompt, traces, gpt5_model=agg)
    return jsonify({"status":"ok","traces":traces,"report":report})

@pipelines_bp.route("/api/pipelines/chain-run", methods=["POST"])
def chain_run():
    """
    Body: {
      "prompt": "...",
      "agents": ["model1","model2","model3", ...],
      "system": "optional system",
      "aggregator_model": "openai/gpt-5"
    }
    Behavior: Agent1 answers; pass (initial prompt + prev reply) to Agent2; continue to AgentN; summarize with GPT-5.
    """
    data = request.get_json(force=True) or {}
    prompt = data.get("prompt","").strip()
    agents = data.get("agents") or []
    sysmsg = data.get("system") or "You are part of a relay; be precise and cite assumptions."
    agg    = data.get("aggregator_model") or "openai/gpt-5"
    if not prompt or not agents:
        return jsonify({"error":"prompt and agents[] required"}), 400

    traces = []
    prev = ""
    for i, m in enumerate(agents):
        tag = (
            f"Initial prompt (do not lose context):\n{prompt}\n\n"
            f"Previous reply (if any):\n{prev or '[none]'}\n\n"
            "Your task: advance the solution. Be incremental, avoid restating prior content."
        )
        msg = [{"role":"system","content":sysmsg},{"role":"user","content":tag}]
        out = call_llm(m, msg)
        traces.append({"agent": m, "last_text": out})
        prev = out

    report = summarize_with_gpt5("Conference Chain Report", prompt, traces, gpt5_model=agg)
    return jsonify({"status":"ok","traces":traces,"report":report})
