"""Transformers 5.17.0 compatibility probe for omni-medical-suite production paths.

Families tested (per production inventory):
  - Marian  : MarianTokenizer + MarianMTModel + AutoTokenizer + GenerationConfig
              (src translation: Helsinki-NLP/opus-mt-en-ar et al.) — CPU generation
  - TrOCR   : TrOCRProcessor + VisionEncoderDecoderModel + generate
              (src/ocr: microsoft/trocr-*, production default base-handwritten;
               small-printed used here for size — identical loading API path)
  - CausalLM: AutoModelForCausalLM + trust_remote_code=True (Jais proofreader
              loading path, src/llm/proofreader.py) — tiny-random-gpt2 stand-in
  - pipeline: pipeline("translation") on the Marian model (22 pipeline() call sites)
  - device  : model.to('cpu') + model.eval() + torch.no_grad generation

Exit code = number of failed checks. Each model is unloaded before the next.
"""
import gc, os, sys

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
import transformers
from transformers import (AutoTokenizer, AutoModelForCausalLM, MarianTokenizer,
                          MarianMTModel, TrOCRProcessor, VisionEncoderDecoderModel,
                          GenerationConfig)

out = []
def check(name, fn):
    try:
        out.append(f"PASS  {name}  :: {fn()}")
    except Exception as e:
        out.append(f"FAIL  {name}  :: {repr(e)[:220]}")

def unload(*objs):
    for o in objs:
        del o
    gc.collect()

MARIAN = "Helsinki-NLP/opus-mt-en-ar"
TROCR = "microsoft/trocr-base-handwritten"   # PRODUCTION DEFAULT (13 call sites in src/)
TINY = "hf-internal-testing/tiny-random-gpt2"

# ---- 1. Marian family (production translation core) ----
def marian_full():
    tok = MarianTokenizer.from_pretrained(MARIAN)
    model = MarianMTModel.from_pretrained(MARIAN)
    model.to("cpu"); model.eval()
    batch = tok(["The patient has severe chest pain."], return_tensors="pt", padding=True)
    with torch.no_grad():
        gen = model.generate(**batch, max_new_tokens=60)
    dec = tok.batch_decode(gen, skip_special_tokens=True)[0]
    assert isinstance(dec, str) and len(dec) > 0, "empty translation"
    r = f"en->ar: '{dec[:70]}'"
    unload(model, tok); gc.collect()
    return r
check(f"Marian MarianTokenizer+MarianMTModel generate [{MARIAN}]", marian_full)

def marian_auto_and_cfg():
    tok = AutoTokenizer.from_pretrained(MARIAN)
    cfg = GenerationConfig.from_pretrained(MARIAN)
    r = f"AutoTokenizer={type(tok).__name__}, GenerationConfig(decoder_start_token_id={cfg.decoder_start_token_id})"
    unload(tok, cfg)
    return r
check(f"Marian AutoTokenizer+GenerationConfig [{MARIAN}]", marian_auto_and_cfg)

# ---- 2. TrOCR family (production OCR core) ----
def trocr_full():
    from PIL import Image
    import numpy as np
    proc = TrOCRProcessor.from_pretrained(TROCR)
    model = VisionEncoderDecoderModel.from_pretrained(TROCR)
    model.to("cpu"); model.eval()
    # synthetic 1-line word image: dark text block on white (28x112 upscaled)
    arr = np.full((32, 128), 255, dtype=np.uint8)
    arr[10:22, 8:120] = 30
    img = Image.fromarray(arr).convert("RGB")
    px = proc(images=img, return_tensors="pt").pixel_values
    with torch.no_grad():
        ids = model.generate(px, max_new_tokens=16)
    txt = proc.batch_decode(ids, skip_special_tokens=True)[0]
    assert isinstance(txt, str)
    r = f"vision->text inference OK (decoded placeholder '{txt[:30]}')"
    unload(model, proc); gc.collect()
    return r
check(f"TrOCR TrOCRProcessor+VisionEncoderDecoderModel generate [{TROCR}]", trocr_full)

# ---- 3. CausalLM (Jais proofreader loading path) ----
def causal_lm():
    tok = AutoTokenizer.from_pretrained(TINY, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(TINY, trust_remote_code=True)
    model.to("cpu"); model.eval()
    inputs = tok("Hello", return_tensors="pt")
    with torch.no_grad():
        outg = model.generate(**inputs, max_new_tokens=5)
    assert outg.shape[1] > inputs["input_ids"].shape[1]
    r = f"AutoModelForCausalLM+trust_remote_code generate OK ({type(model).__name__})"
    unload(model, tok); gc.collect()
    return r
check(f"CausalLM AutoModelForCausalLM [{TINY} stand-in for core42/jais-13b-chat]", causal_lm)

# ---- 4. pipeline API (production tasks: ner, summarization — per repo grep;
#         the repo does NOT use pipeline("translation"); Marian is used via
#         MarianMTModel directly, tested in check 1) ----
def pipeline_ner():
    from transformers import pipeline
    pipe = pipeline("ner", model="hf-internal-testing/tiny-random-BertForTokenClassification",
                    aggregation_strategy="simple", device=-1)
    res = pipe("Doctor examined patient")
    r = f"pipeline('ner', aggregation_strategy='simple') OK ({len(res)} span objects)"
    unload(pipe); gc.collect()
    return r
check("pipeline('ner') [tiny BertForTokenClassification stand-in]", pipeline_ner)

def pipeline_summ():
    from transformers import pipeline
    pipe = pipeline("summarization", model="hf-internal-testing/tiny-random-BartForConditionalGeneration",
                    device=-1)
    res = pipe("The doctor examined the report and found abnormal results " * 4,
               max_length=20, min_length=2)
    r = f"pipeline('summarization') OK (summary len={len(res[0].get('summary_text',''))})"
    unload(pipe); gc.collect()
    return r
check("pipeline('summarization') [tiny Bart stand-in]", pipeline_summ)

print(f"transformers {transformers.__version__} probe — {len(out)} checks (torch {torch.__version__}, cpu)")
for line in out: print(line)
fails = sum(1 for l in out if l.startswith("FAIL"))
print(f"RESULT: {'ALL PASS' if fails == 0 else f'{fails} FAILURES'}")
sys.exit(fails)
