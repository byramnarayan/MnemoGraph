import os
import sys

token = os.getenv("HF_TOKEN")

try:
    from transformers import AutoTokenizer, AutoModelForMaskedLM
    print("Loading model...", flush=True)
    model = AutoModelForMaskedLM.from_pretrained("yukyung/LAnoBERT", subfolder="hdfs", token=token)
    print("Model loaded successfully:", type(model), flush=True)
except Exception as e:
    print("Model error:", e, flush=True)
