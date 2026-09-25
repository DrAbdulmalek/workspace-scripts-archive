#!/bin/bash
# Binary-search transformers 5.x for trocr-base-handwritten tokenizer loadability
# (no torch needed — tokenizer loading only; production floor is >=5.10.0)
set -u
for V in 5.10.0 5.12.0 5.14.0 5.15.0 5.16.0; do
  TD=$(mktemp -d)
  uv venv --python 3.11 "$TD/v" --quiet 2>/dev/null
  uv pip install --python "$TD/v/bin/python" --quiet "transformers==$V" sentencepiece tiktoken 2>/dev/null
  R=$("$TD/v/bin/python" - <<'EOF'
try:
    from transformers import AutoTokenizer
    t = AutoTokenizer.from_pretrained("microsoft/trocr-base-handwritten")
    print("OK", type(t).__name__)
except Exception as e:
    print("FAIL", repr(e)[:110])
EOF
  2>/dev/null | tail -1)
  echo "transformers $V :: $R"
  rm -rf "$TD"
done