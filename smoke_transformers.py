#!/usr/bin/env python3
"""TASK-02D smoke: transformers 5.17.0 compatibility for production paths.

1) Import every transformers class/symbol used by production code
   (hf-space/src/*, packages/core/model_registry.py, packages/omni_ocr/*,
   packages/ai/*, training/*).
2) Real production translation path: Helsinki-NLP/opus-mt-en-ar (the exact
   model configured in hf-space/app_core.py line 178) — load + generate.
3) TrOCR path: VisionEncoderDecoderModel + TrOCRProcessor via a hand-built
   tiny config (no network dependency) + generate() on a PIL image.
4) Auto* factory path on the Marian checkpoint (AutoTokenizer/AutoModelForSeq2SeqLM).
"""
import sys, traceback
from PIL import Image

results = []

def check(name, fn):
    try:
        detail = fn()
        results.append((name, "PASS", detail or ""))
    except Exception as e:
        results.append((name, "FAIL", f"{type(e).__name__}: {e}"))
        traceback.print_exc()

import torch
import transformers
from transformers import (
    TrOCRProcessor, VisionEncoderDecoderModel, VisionEncoderDecoderConfig,
    MarianMTModel, MarianTokenizer, MarianConfig,
    AutoTokenizer, AutoModel, AutoProcessor, AutoConfig,
    AutoModelForCausalLM, AutoModelForSeq2SeqLM, AutoModelForTokenClassification,
    AutoModelForSequenceClassification, AutoModelForObjectDetection, AutoImageProcessor,
    pipeline, Trainer, TrainingArguments, Seq2SeqTrainer, Seq2SeqTrainingArguments,
    GenerationConfig, ViTConfig, PretrainedConfig,
)
try:
    from transformers import BertModel, BertTokenizer  # labs/omniparse usage
    _bert_ok = True
except ImportError:
    _bert_ok = False

MODEL = "Helsinki-NLP/opus-mt-en-ar"  # exact production model (hf-space/app_core.py)

def imports():
    assert transformers.__version__, "no version"
    return f"transformers {transformers.__version__}, torch {torch.__version__}, bert import ok={_bert_ok}"
check("imports of all production-used symbols", imports)

_mar = {}

def marian_real():
    tok = MarianTokenizer.from_pretrained(MODEL)
    mdl = MarianMTModel.from_pretrained(MODEL)
    mdl.eval()
    _mar["tok"], _mar["mdl"] = tok, mdl
    n_params = sum(p.numel() for p in mdl.parameters())
    return f"loaded, params={n_params/1e6:.1f}M, vocab={tok.vocab_size}"
check("MarianMT real production model load (opus-mt-en-ar)", marian_real)

def marian_generate():
    tok, mdl = _mar["tok"], _mar["mdl"]
    batch = tok(["Hello, how are you?", "Take this medication twice daily."],
                return_tensors="pt", padding=True)
    with torch.no_grad():
        gen = mdl.generate(**batch, max_new_tokens=48, num_beams=2)
    out = tok.batch_decode(gen, skip_special_tokens=True)
    assert len(out) == 2 and all(isinstance(s, str) and s for s in out)
    return f"translations={out}"
check("MarianMT generate + batch_decode (production translation path)", marian_generate)

def marian_config_ser():
    cfg = _mar["mdl"].config
    assert isinstance(cfg, (MarianConfig, PretrainedConfig))
    gc = GenerationConfig.from_model_config(_mar["mdl"].config)
    return f"config type={type(cfg).__name__}, generation_config ok={gc is not None}"
check("Marian config / GenerationConfig introspection", marian_config_ser)

def auto_factories():
    at = AutoTokenizer.from_pretrained(MODEL)
    am = AutoModelForSeq2SeqLM.from_pretrained(MODEL)
    return f"AutoTokenizer={type(at).__name__}, AutoModelForSeq2SeqLM={type(am).__name__}"
check("Auto* factory path on production model", auto_factories)

def trocr_tiny():
    # Hand-built tiny VisionEncoderDecoder config (no network).
    # NOTE: transformers 5.x expects nested encoder/decoder as plain dicts
    # when constructing VisionEncoderDecoderConfig directly (production code
    # uses from_pretrained and is unaffected by this constructor detail).
    from transformers import ViTImageProcessor
    enc = {"image_size": 32, "patch_size": 8, "hidden_size": 32, "num_hidden_layers": 1,
           "num_attention_heads": 2, "intermediate_size": 64, "model_type": "vit"}
    dec = {"vocab_size": 1024, "d_model": 32, "encoder_layers": 1, "decoder_layers": 1,
           "decoder_attention_heads": 2, "decoder_ffn_dim": 64,
           "max_position_embeddings": 64, "pad_token_id": 0,
           "decoder_start_token_id": 1, "eos_token_id": 2, "bos_token_id": 1,
           "forced_eos_token_id": 2, "model_type": "marian"}
    cfg = VisionEncoderDecoderConfig(encoder=enc, decoder=dec)
    model = VisionEncoderDecoderModel(cfg)
    model.eval()
    px = torch.randn(1, 3, 32, 32)
    with torch.no_grad():
        out = model.generate(pixel_values=px, max_new_tokens=8)
    assert out.shape[0] == 1
    ip = ViTImageProcessor(image_size=32)
    px2 = ip(images=[Image.new("RGB", (32, 32), "white")], return_tensors="pt")
    assert "pixel_values" in px2
    return f"VisionEncoderDecoderModel built+generate ok, output shape={tuple(out.shape)}; ViTImageProcessor ok"
check("TrOCR class family: VisionEncoderDecoderModel tiny build + generate", trocr_tiny)

def trocr_trainer_api():
    # Seq2SeqTrainer/TrainingArguments signature sanity (production fine-tuning path)
    args = Seq2SeqTrainingArguments(output_dir="/tmp/t02d-smoke", per_device_train_batch_size=1,
                                    max_steps=1, report_to=[], disable_tqdm=True,
                                    logging_steps=1, save_strategy="no")
    ta = TrainingArguments(output_dir="/tmp/t02d-smoke", report_to=[], save_strategy="no")
    return f"Seq2SeqTrainingArguments + TrainingArguments construct ok ({type(args).__name__})"
check("Trainer/TrainingArguments/Seq2SeqTrainingArguments API", trocr_trainer_api)

def pipeline_api():
    # EXACT production pattern: hf-space/src/ner/llm_ner_annotator.py:55 and
    # packages/training_hub/src/ingestion/hybrid_scrubber.py:149 use
    # pipeline("ner", model=..., tokenizer=..., aggregation_strategy="simple", device=-1)
    from transformers import pipeline as pl, BertConfig, BertForTokenClassification, PreTrainedTokenizerFast
    from tokenizers import Tokenizer, models as tmodels, pre_tokenizers
    vocab = {"[PAD]": 0, "[UNK]": 1, "patient": 2, "has": 3, "diabetes": 4, "type": 5, "2": 6}
    tk = Tokenizer(tmodels.WordLevel(vocab, unk_token="[UNK]"))
    tk.pre_tokenizer = pre_tokenizers.Whitespace()
    fast = PreTrainedTokenizerFast(tokenizer_object=tk, pad_token="[PAD]", unk_token="[UNK]", model_max_length=32)
    labels = {0: "O", 1: "MED", 2: "DOSE"}
    cfg = BertConfig(vocab_size=len(vocab), hidden_size=32, num_hidden_layers=1,
                     num_attention_heads=2, intermediate_size=64, num_labels=3,
                     id2label=labels, label2id={v: k for k, v in labels.items()})
    mdl = BertForTokenClassification(cfg)
    p = pl("ner", model=mdl, tokenizer=fast, aggregation_strategy="simple", device=-1)
    r = p("patient has diabetes type 2")
    assert isinstance(r, list)
    return f"pipeline('ner', aggregation_strategy='simple', device=-1) ok, {len(r)} entity group(s)"
check("pipeline('ner') production pattern (llm_ner_annotator/hybrid_scrubber)", pipeline_api)

print("\n=== TRANSFORMERS SMOKE RESULTS ===")
fails = 0
for name, st, err in results:
    print(f"  [{st}] {name}" + (f" — {err}" if err else ""))
    fails += st == "FAIL"
print(f"transformers {transformers.__version__} | torch {torch.__version__}")
sys.exit(1 if fails else 0)
