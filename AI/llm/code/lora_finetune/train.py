from transformers import Trainer, TrainingArguments, DataCollatorForLanguageModeling
from datasets import load_dataset
import torch

from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

from datasets import load_dataset


model_name = "EleutherAI/pythia-2.8b-deduped"   # 2.8B参数的模型

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=BitsAndBytesConfig(load_in_8bit=True),
    dtype=torch.float16,
    device_map="auto"
)

tokenizer = AutoTokenizer.from_pretrained(
    model_name)
tokenizer.pad_token = tokenizer.eos_token

print(model)
for name, module in model.named_modules():
    print(name, module)


model = prepare_model_for_kbit_training(model)
# target_modules: 要进行LoRA训练的模块，内部是通过字符串正则表达式来匹配的
#                 如果想要指定的层数或者模块，可以使用更长的、能唯一区分路径的子串
#                 例如，"layers.0.attention.dense" 可以匹配 "gpt_neox.layers.0.attention.dense"

# r: LoRA的秩，即LoRA矩阵的维度
# lora_alpha: LoRA的alpha值，即LoRA矩阵的缩放因子
# lora_dropout: LoRA的dropout率
# bias: LoRA的偏置项
# task_type: 任务类型，这里选择了CAUSAL_LM，即因果语言模型
lora_config = LoraConfig(r=4,
                         lora_alpha=16,
                         target_modules=[
                             "query_key_value", "dense"],
                         lora_dropout=0.1,
                         bias="none",
                         task_type="CAUSAL_LM")

peft_model = get_peft_model(model, lora_config)
print(peft_model)
print(peft_model.print_trainable_parameters())


# 加载数据集
quotes_dataset = load_dataset("Abirate/english_quotes")
print(quotes_dataset["train"][0])
print("len_quotes_dataset:", len(quotes_dataset["train"]))


def preprocess_function(examples):
    return tokenizer(examples["quote"], padding="max_length", truncation=True)


tokenized_datasets = quotes_dataset.map(preprocess_function, batched=True)
print(tokenized_datasets["train"][0])


# 推荐操作：关闭缓存可提高训练效率
peft_model.config.use_cache = False

# 定义训练参数
train_args = TrainingArguments(
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    warmup_steps=100,
    max_steps=800,
    learning_rate=2e-4,
    fp16=True,  # 启用混合精度训练
    logging_steps=1,
    output_dir="outputs",
)

# 数据整理器，用于处理批量数据
quote_collator = DataCollatorForLanguageModeling(tokenizer, mlm=False)

# 实例化 Trainer
trainer = Trainer(
    model=peft_model,
    train_dataset=tokenized_datasets["train"],
    args=train_args,
    data_collator=quote_collator,
)

# 开始训练
trainer.train()

# 保存模型
peft_model.save_pretrained("outputs")
tokenizer.save_pretrained("outputs")
