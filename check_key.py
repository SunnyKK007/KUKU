"""Check that the API key in .env works. Usage: python3 check_key.py"""
from common.llm import LLM, first_available_spec

spec = first_available_spec()
if spec == "offline":
    print("No key found. Open 2_Code/.env and paste your key after GEMINI_API_KEY= (or GROQ_API_KEY=).")
    raise SystemExit(1)
llm = LLM(spec)
print("Using:", llm.label())
try:
    out = llm.json("Reply with JSON only.", 'Return {"ok": true, "model_says": "<three words>"}', max_tokens=50)
    print("Key works. Model replied:", out)
except Exception as e:
    print("Key did not work:", str(e)[:300])
    raise SystemExit(1)
