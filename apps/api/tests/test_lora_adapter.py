import numpy as np

from src.domain.embeddings.lora_adapter import (
    ContrastiveTrainer,
    LoraAdapterConfig,
    LoraEmbeddingAdapter,
)


def test_lora_adapter_initialization_identity():
    dim = 64
    adapter = LoraEmbeddingAdapter(dim=dim, rank=8)

    # Initial state should act as identity mapping (B=0)
    vec = np.random.randn(dim).astype(np.float32)
    vec_norm = (vec / np.linalg.norm(vec)).tolist()

    adapted = adapter.adapt_vector(vec_norm)
    assert np.allclose(vec_norm, adapted, atol=1e-5)


def test_lora_contrastive_training():
    dim = 32
    adapter = LoraEmbeddingAdapter(dim=dim, rank=4)
    trainer = ContrastiveTrainer(
        LoraAdapterConfig(dim=dim, rank=4, learning_rate=0.01, epochs=10)
    )

    rng = np.random.default_rng(42)
    queries = [rng.standard_normal(dim).tolist() for _ in range(8)]
    # Positives are correlated with queries + small noise
    positives = [(np.array(q) + 0.1 * rng.standard_normal(dim)).tolist() for q in queries]

    loss = trainer.train(queries, positives, adapter, epochs=10, lr=0.01)
    assert loss >= 0.0

    state = adapter.state_dict()
    assert "matrix_a" in state
    assert "matrix_b" in state

    new_adapter = LoraEmbeddingAdapter(dim=dim, rank=4, weights=state)
    adapted_orig = adapter.adapt_vector(queries[0])
    adapted_new = new_adapter.adapt_vector(queries[0])
    assert np.allclose(adapted_orig, adapted_new, atol=1e-6)
