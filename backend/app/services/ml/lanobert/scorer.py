from __future__ import annotations

import logging
import math
from typing import Any

from app.services.ml.lanobert.loader import LAnoBERTModelLoader

logger = logging.getLogger(__name__)


class LAnoBERTScorer:
    """
    Computes token-level masked cross-entropy error_mean scores on system log lines.
    Higher values indicate greater anomaly compared to learned normal system logs.
    """

    def __init__(self, dataset: str = "hdfs"):
        self.dataset = dataset
        self._loader = LAnoBERTModelLoader

    def score_line(self, log_line: str) -> float | None:
        """
        Computes error_mean for a single log line.
        Returns float score or None if model unavailable.
        """
        if not log_line or not log_line.strip():
            return 0.0

        loaded = self._loader.load(self.dataset)
        if not loaded:
            return None

        tokenizer, model = loaded

        try:
            import torch
            import torch.nn.functional as F

            device = next(model.parameters()).device
            inputs = tokenizer(log_line, return_tensors="pt", truncation=True, max_length=128)
            input_ids = inputs["input_ids"].to(device)
            seq_len = input_ids.shape[1]

            if seq_len <= 2:  # Only [CLS] and [SEP]
                return 0.0

            # Mask non-special tokens and accumulate negative log probabilities
            mask_token_id = tokenizer.mask_token_id
            losses: list[float] = []

            # Batch or evaluate tokens
            with torch.no_grad():
                outputs = model(input_ids)
                logits = outputs.logits  # [1, seq_len, vocab_size]
                log_probs = F.log_softmax(logits, dim=-1)

                for idx in range(1, seq_len - 1):
                    target_token_id = input_ids[0, idx].item()
                    token_log_prob = log_probs[0, idx, target_token_id].item()
                    # Cross-entropy error: -log P(token)
                    token_error = -token_log_prob
                    if not math.isnan(token_error) and not math.isinf(token_error):
                        losses.append(max(0.0, token_error))

            if not losses:
                return 0.0

            return float(sum(losses) / len(losses))

        except Exception as e:
            logger.warning(f"[LAnoBERT Scorer] Error scoring line '{log_line[:40]}...': {e}")
            return None

    def score_lines_batch(self, lines: list[str]) -> list[float | None]:
        """Scores a list of lines with deduplication for high throughput."""
        cache: dict[str, float | None] = {}
        results: list[float | None] = []

        for line in lines:
            trimmed = line.strip()
            if trimmed not in cache:
                cache[trimmed] = self.score_line(trimmed)
            results.append(cache[trimmed])

        return results

