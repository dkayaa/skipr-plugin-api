import os
from typing import Any

import numpy as np
import torch
from transformers import DistilBertForSequenceClassification, DistilBertTokenizer

SUPPORTED_BACKENDS = frozenset({"pytorch", "onnx"})


def _get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class Classifier:
    def __init__(
        self,
        tokenizer: Any,
        model: Any,
        *,
        backend: str,
        device: torch.device | None = None,
    ) -> None:
        self.tokenizer = tokenizer
        self.model = model
        self.backend = backend
        self.device = device
        self.batch_size = int(os.getenv("CLASSIFIER_BATCH_SIZE", "32"))

    def predict(self, texts: list[str]) -> list[int]:
        labels: list[int] = []
        for index in range(0, len(texts), self.batch_size):
            batch_texts = texts[index: index + self.batch_size]
            if self.backend == "pytorch":
                labels.extend(self._predict_pytorch(batch_texts))
            else:
                labels.extend(self._predict_onnx(batch_texts))
        return labels

    def _predict_pytorch(self, batch_texts: list[str]) -> list[int]:
        inputs = self.tokenizer(
            batch_texts,
            return_tensors="pt",
            truncation=True,
            padding=True,
        )
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch.no_grad():
            outputs = self.model(**inputs)
        return torch.argmax(outputs.logits, dim=1).tolist()

    def _predict_onnx(self, batch_texts: list[str]) -> list[int]:
        inputs = self.tokenizer(
            batch_texts,
            return_tensors="np",
            truncation=True,
            padding=True,
        )
        outputs = self.model(**inputs)
        logits = outputs.logits
        if not isinstance(logits, np.ndarray):
            logits = np.asarray(logits)
        return np.argmax(logits, axis=1).tolist()


def _load_pytorch_classifier(model_name: str) -> Classifier:
    tokenizer = DistilBertTokenizer.from_pretrained(model_name)
    model = DistilBertForSequenceClassification.from_pretrained(model_name)
    device = _get_device()
    model.to(device)
    model.eval()
    return Classifier(tokenizer, model, backend="pytorch", device=device)


def _load_onnx_classifier(model_name: str) -> Classifier:
    from optimum.onnxruntime import ORTModelForSequenceClassification
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = ORTModelForSequenceClassification.from_pretrained(model_name)
    return Classifier(tokenizer, model, backend="onnx")


def load_classifier() -> Classifier:
    model_name = os.getenv("HUGGINGFACE_MODEL")
    if not model_name:
        raise ValueError("HUGGINGFACE_MODEL is not set")

    backend = os.getenv("CLASSIFIER_BACKEND", "pytorch").lower()
    if backend not in SUPPORTED_BACKENDS:
        raise ValueError(
            f"Unsupported CLASSIFIER_BACKEND={backend!r}; "
            f"expected one of {sorted(SUPPORTED_BACKENDS)}"
        )

    if backend == "onnx":
        return _load_onnx_classifier(model_name)
    return _load_pytorch_classifier(model_name)
