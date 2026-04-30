import os
import torch
from typing import Optional

from datasets import load_dataset
from load_model import tokenizer


def format_sample_for_qwen(record, max_seq_len=2048):
    instr = (record.get("instruction") or "").strip()
    ans = (record.get("output") or "").strip()
    if not instr or not ans:
        return {"input_ids": [], "labels": []}

    # 构造不包含答案的prompt
    messages_no_assist = []
    messages_no_assist.append(
        {"role": "system", "content": "你是《黑神话：悟空》领域助手，回答准确、简明。"})
    messages_no_assist.append(
        {"role": "user", "content": instr})

    prompt_ids = tokenizer.apply_chat_template(messages_no_assist,
                                               add_generation_prompt=True,
                                               tokenize=True,
                                               padding=False,
                                               truncation=False,
                                               max_length=None,
                                               return_tensors=None,
                                               return_dict=False)

    # 构造包含答案的prompt
    messages_with_assist = messages_no_assist.copy()
    messages_with_assist.append(
        {"role": "assistant", "content": ans})

    complete_ids = tokenizer.apply_chat_template(messages_with_assist,
                                                 add_generation_prompt=False,
                                                 tokenize=True,
                                                 padding=False,
                                                 truncation=False,
                                                 max_length=None,
                                                 return_tensors=None,
                                                 return_dict=False)
    complete_ids = complete_ids[:max_seq_len]

    cut = min(len(prompt_ids), len(complete_ids))
    # 为啥使用-100来填充？ 因为-100是nn.cross_entropy_loss的ignore_index，不会计算loss
    # https://docs.pytorch.org/docs/stable/generated/torch.nn.CrossEntropyLoss.html
    labels = [-100] * cut + complete_ids[cut:]
    assert len(complete_ids) == len(
        labels), "input_ids and labels length mismatch, record: " + str(record)
    return {"input_ids": complete_ids, "labels": labels}


def _format_sample_fast_with_src_idx(example, idx: int):
    """与 format_sample_for_qwen 一致，并保留原始样本下标便于对照 jsonl 行。"""
    row = format_sample_for_qwen(example)
    row["__source_idx__"] = idx
    return row


def find_misaligned_samples(ds, max_report: Optional[int] = 50):
    """找出 len(input_ids) != len(labels) 的条目；单测只跑 dataset.py 前几项时容易漏掉后面的坏样本。"""
    bad = []
    n = len(ds)
    for i in range(n):
        ex = ds[i]
        li, ll = len(ex["input_ids"]), len(ex["labels"])
        if li != ll:
            src = ex.get("__source_idx__")
            bad.append({
                "processed_idx": i,
                "source_jsonl_row0": src,
                "len_input_ids": li,
                "len_labels": ll,
            })
    if not bad:
        print(f"[find_misaligned_samples] OK: 共 {n} 条（与 Trainer 一致），全部等长")
        return []

    reported = bad if max_report is None else bad[:max_report]
    extra = ""
    if max_report is not None and len(bad) > len(reported):
        extra = f" …… 另有 {len(bad) - len(reported)} 条未列出，可调 max_report=None 打出全部。"
    raise RuntimeError(
        "发现 input_ids / labels 长度不一致（共 {} 条）: ".format(len(bad))
        + str(reported)
        + extra
    )


train_dataset = load_dataset(
    "json", data_files="finetune_data/blackwukong_augmented_20260429.jsonl", split="train")

processed_dataset = train_dataset.map(
    _format_sample_fast_with_src_idx,
    with_indices=True,
    remove_columns=train_dataset.column_names,
)

processed_dataset = processed_dataset.filter(
    lambda x: len(x["input_ids"]) > 0)

# 与 Trainer 完全相同的数据上做一次全表扫描；设为 1 可查坏样本：
# CHECK_ALIGNMENT=1 python finetune.py
_alignment_flag = os.environ.get("CHECK_ALIGNMENT", "").strip().lower()
if _alignment_flag in ("1", "true", "yes", "on"):
    find_misaligned_samples(processed_dataset)

print(processed_dataset)


class QwenDataCollator:
    def __init__(self, pad_id: int, max_seg_len: int = 2048, ignored_id: int = -100):
        self.pad_id = pad_id
        self.max_seg_len = max_seg_len
        self.ignored_id = ignored_id

    def __call__(self, features):
        max_len = min(max(len(f["input_ids"])
                      for f in features), self.max_seg_len)

        padded_input_ids, padded_labels = [], []
        for i, f in enumerate(features):
            input_id = f["input_ids"][:max_len]
            label = f["labels"][:max_len]
            assert len(input_id) == len(label), (
                "batch 内样本 input_ids vs labels 长度不一致: batch_pos=%d len_input_ids=%d len_labels=%s "
                "source_jsonl_row0=%s（设 CHECK_ALIGNMENT=1 重跑可定位数据集行）"
                % (
                    i,
                    len(input_id),
                    len(label),
                    repr(f.get("__source_idx__")),
                )
            )
            padding_len = max_len - len(input_id)
            pad_ids = input_id + [self.pad_id] * padding_len
            pad_labels = label + [self.ignored_id] * padding_len
            padded_input_ids.append(torch.tensor(pad_ids, dtype=torch.long))
            padded_labels.append(torch.tensor(pad_labels, dtype=torch.long))

        return {
            "input_ids": torch.stack(padded_input_ids),
            "labels": torch.stack(padded_labels)
        }


if __name__ == "__main__":
    find_misaligned_samples(processed_dataset, max_report=None)
    collector = QwenDataCollator(tokenizer.pad_token_id, 2048)
    n = len(processed_dataset)
    batch_size = 2  # 与 finetune.py TrainingArguments.per_device_train_batch_size 一致
    for start in range(0, n, batch_size):
        batch_features = [
            processed_dataset[i]
            for i in range(start, min(start + batch_size, n))
        ]
        out = collector(batch_features)
        print(start, "-", min(start + batch_size - 1, n - 1),
              out["input_ids"].shape)
