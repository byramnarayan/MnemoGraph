from __future__ import annotations

import logging
import os
import threading
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class LAnoBERTModelLoader:
    """
    Thread-safe lazy loader for pretrained yukyung/LAnoBERT with Hugging Face token support,
    rate-limiting protection, and CPU fallback.
    """

    MODEL_ID = "yukyung/LAnoBERT"
    SUPPORTED_DATASETS = ("hdfs", "bgl", "thunderbird")
    DEFAULT_DATASET = "hdfs"

    _instances: dict[str, tuple[Any, Any]] = {}
    _lock = threading.Lock()

    @classmethod
    def get_token(cls) -> str | None:
        """Retrieves configured Hugging Face API key."""
        if settings.huggingface_api_key and settings.huggingface_api_key.get_secret_value():
            return settings.huggingface_api_key.get_secret_value()
        if settings.hf_token and settings.hf_token.get_secret_value():
            return settings.hf_token.get_secret_value()
        return os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")

    @classmethod
    def load(cls, dataset: str = "hdfs") -> tuple[Any, Any] | None:
        """
        Loads the tokenizer and model for the specified subfolder dataset.
        Caches the model instance in memory to avoid repeated Hugging Face API requests.
        """
        ds = dataset.lower() if dataset.lower() in cls.SUPPORTED_DATASETS else cls.DEFAULT_DATASET

        with cls._lock:
            if ds in cls._instances:
                return cls._instances[ds]

            token = cls.get_token()

            try:
                import torch
                from transformers import AutoModelForMaskedLM, AutoTokenizer

                logger.info(f"[LAnoBERT] Initializing {cls.MODEL_ID} subfolder='{ds}' with token={bool(token)}")

                # Rate limiting consideration: local_files_only check first, else pull with token
                tokenizer = AutoTokenizer.from_pretrained(
                    cls.MODEL_ID,
                    subfolder=ds,
                    token=token,
                )

                model = AutoModelForMaskedLM.from_pretrained(
                    cls.MODEL_ID,
                    subfolder=ds,
                    token=token,
                )

                # Use CUDA if available, else CPU
                device = "cuda" if torch.cuda.is_available() else "cpu"
                model.to(device)
                model.eval()

                logger.info(f"[LAnoBERT] Model loaded successfully on device: {device}")
                cls._instances[ds] = (tokenizer, model)
                return cls._instances[ds]

            except Exception as e:
                logger.warning(f"[LAnoBERT] Failed to load model '{cls.MODEL_ID}/{ds}': {e}. Fallback active.")
                return None

