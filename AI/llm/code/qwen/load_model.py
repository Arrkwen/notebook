import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import get_peft_model, LoraConfig, prepare_model_for_kbit_training, PeftModel

model_name = "Qwen/Qwen2.5-3B-Instruct"  # 3B参数的模型
adapter_output_dir = "outputs"
# 同时保留纯基座、训练分支、适配器推理分支时需多次 from_pretrained；
# 4bit 各占一份显存，显存紧张时可删掉 base_model 或改为按需惰性加载某一枝。


def load_tokenizer(model_name):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    return tokenizer


def load_base_model(model_name):
    compute_dtype = torch.bfloat16 if torch.cuda.is_available(
    ) and torch.cuda.is_bf16_supported() else torch.float16
    bnb_config = BitsAndBytesConfig(load_in_4bit=True,
                                    bnb_4bit_quant_type="nf4",
                                    bnb_4bit_compute_dtype=compute_dtype,
                                    bnb_4bit_use_double_quant=True)
    base_model = AutoModelForCausalLM.from_pretrained(model_name,
                                                      trust_remote_code=True,
                                                      quantization_config=bnb_config,
                                                      device_map="auto")
    print(base_model)
    return base_model


def load_peft_model(base_model):
    base_model.config.use_cache = False
    base_model = prepare_model_for_kbit_training(base_model)

    lora_config = LoraConfig(r=16,
                             lora_alpha=24,
                             lora_dropout=0.05,
                             target_modules=[
                                 "q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "down_proj", "up_proj"],
                             bias="none",
                             task_type="CAUSAL_LM")

    peft_model = get_peft_model(base_model, lora_config)
    peft_model.config.use_cache = False
    peft_model.enable_input_require_grads()

    print(peft_model)
    print(peft_model.print_trainable_parameters())
    return peft_model


def load_adapter_model(adapter_base_model, adapter_dir):
    adapter_model = PeftModel.from_pretrained(adapter_base_model, adapter_dir)
    adapter_model.eval()
    adapter_model.config.use_cache = True
    return adapter_model


tokenizer = load_tokenizer(model_name)

# 纯基座：不参与 PEFT attach，供 baseline 推理等与训练隔离
base_model = load_base_model(model_name)

# 训练链路：独占另一份加载，避免与下方推理 adapter 共享同一份 quantized 权重
base_training = load_base_model(model_name)
peft_model = load_peft_model(base_training)

# 推理（LoRA）：再独占一份基座 + outputs 适配器（不可与上面 base_training 共用同一对象）
base_inference = load_base_model(model_name)
adapter_model = load_adapter_model(base_inference, adapter_output_dir)


if __name__ == "__main__":
    print(tokenizer)
    print(base_model)
    print(peft_model)
    print(adapter_model)
