"""Shared model loading/generation helpers for compare_eval.py and auto_eval.py."""
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "Qwen/Qwen3-0.6B"
ADAPTER_DIR = "output/adapter_final"


def load_model(model_name=MODEL, adapter_dir=ADAPTER_DIR):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    base_model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float32)
    # PeftModel.from_pretrained replaces base_model's target Linear layers in
    # place with LoRA-wrapped versions - it doesn't leave an untouched copy
    # around. disable_adapter() toggles the LoRA delta off/on on this same
    # instance instead of loading the model twice.
    model = PeftModel.from_pretrained(base_model, adapter_dir)
    return model, tokenizer


def generate(model, tokenizer, question, max_new_tokens=200):
    messages = [{"role": "user", "content": question}]
    prompt_ids = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True, return_tensors="pt",
    )["input_ids"]
    with torch.no_grad():
        out = model.generate(
            prompt_ids,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(out[0, prompt_ids.shape[1]:], skip_special_tokens=True)
