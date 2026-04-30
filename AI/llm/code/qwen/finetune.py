import torch

from load_model import tokenizer, peft_model, adapter_output_dir
from transformers import Trainer, TrainingArguments
from dataset import processed_dataset, QwenDataCollator


collector = QwenDataCollator(tokenizer.pad_token_id)

train_args = TrainingArguments(
    output_dir=adapter_output_dir,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=2e-3,
    warmup_ratio=0.03,
    num_train_epochs=10,
    lr_scheduler_type="cosine",
    save_steps=100,
    save_total_limit=2,
    bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
    fp16=not (torch.cuda.is_available() and torch.cuda.is_bf16_supported()),
    report_to="tensorboard",
    logging_strategy="steps",
    logging_steps=10,
)

trainer = Trainer(
    model=peft_model,
    train_dataset=processed_dataset,
    args=train_args,
    data_collator=collector,
)

trainer.train()

peft_model.save_pretrained(adapter_output_dir)
tokenizer.save_pretrained(adapter_output_dir)
