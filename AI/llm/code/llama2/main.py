import torch
from src.transformer import Llama2Transformer


if __name__ == "__main__":
    hparams = {
        "d_model": 512,
        "d_ff": 2048,
        "n_heads": 8,
        "n_kv_heads": 4,
        "n_layers": 6,
        "vocab_size": 10000,
        "max_batch_size": 1024,
        "max_seq_len": 2048,
        "dropout": 0.1
    }

    model = Llama2Transformer(
        d_model=hparams["d_model"],
        d_ff=hparams["d_ff"],
        n_heads=hparams["n_heads"],
        n_kv_heads=hparams["n_kv_heads"],
        n_layers=hparams["n_layers"],
        vocab_size=hparams["vocab_size"],
        max_batch_size=hparams["max_batch_size"],
        max_seq_len=hparams["max_seq_len"],
        dropout=hparams["dropout"])
    print(model)

    torch.manual_seed(1234)
    batch_size = 2
    seq_len = 10
    tokens = torch.randint(0, hparams["vocab_size"], (batch_size, seq_len))
    start_pos = 0
    logits = model(tokens, start_pos)
    print(logits.shape)  # [batch_size, seq_len, vocab_size]
