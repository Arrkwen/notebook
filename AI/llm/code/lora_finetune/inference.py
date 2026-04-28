import ipdb
import torch
from pathlib import Path

from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

# 与 train.py 相同的基座模型
model_name = "EleutherAI/pythia-2.8b-deduped"

# 含 adapter_config.json + adapter_model.safetensors 的目录（可与 train 里 save_pretrained / checkpoint 一致）
BASE_DIR = Path(__file__).resolve().parent
ADAPTER_DIR = BASE_DIR / "outputs"  # 或 BASE_DIR / "outputs" / "checkpoint-800"

# 1) 先加载量化基座（与微调时一致，否则 LoRA 权重对不上）
base_model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=BitsAndBytesConfig(load_in_8bit=True),
    dtype=torch.float16,
    device_map="auto",
)
# 2) 在基座上挂载已训练 adapter（不要用 get_peft_model(path)）
model = PeftModel.from_pretrained(base_model, str(ADAPTER_DIR))
model.eval()

# 推理阶段可打开 KV cache 加速 generate（训练时通常关掉）
model.config.use_cache = True

# Tokenizer：优先用 adapter 目录里保存的；没有则回退基座
# try:
#     tokenizer = AutoTokenizer.from_pretrained(str(ADAPTER_DIR))
# except OSError:
tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.pad_token_id = tokenizer.eos_token_id


def _model_device():
    return next(model.parameters()).device


def generate_text(prompt: str) -> str:
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(_model_device()) for k, v in inputs.items()}
    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=100,
            do_sample=True,
            top_p=0.95,
            top_k=40,
            repetition_penalty=1.1,
            temperature=0.6,
            pad_token_id=tokenizer.pad_token_id,
        )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)


if __name__ == "__main__":
    print(generate_text("Be yourself; everyone"))
