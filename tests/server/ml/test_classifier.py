import os
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import torch

from tests.support.path import setup_server_import_path

setup_server_import_path()

from classifier import Classifier, load_classifier  # noqa: E402


class TestClassifier(unittest.TestCase):
    @patch("classifier._load_pytorch_classifier")
    def test_load_classifier_pytorch_backend(self, mock_load_pytorch):
        expected = Classifier(MagicMock(), MagicMock(), backend="pytorch")
        mock_load_pytorch.return_value = expected

        with patch.dict(
            os.environ,
            {
                "HUGGINGFACE_MODEL": "kayaaaa/ad-classifier",
                "CLASSIFIER_BACKEND": "pytorch",
            },
            clear=False,
        ):
            classifier = load_classifier()

        self.assertIs(classifier, expected)
        mock_load_pytorch.assert_called_once_with("kayaaaa/ad-classifier")

    @patch("classifier._load_onnx_classifier")
    def test_load_classifier_onnx_backend(self, mock_load_onnx):
        expected = Classifier(MagicMock(), MagicMock(), backend="onnx")
        mock_load_onnx.return_value = expected

        with patch.dict(
            os.environ,
            {
                "HUGGINGFACE_MODEL": "kayaaaa/ad-classifier-quantised",
                "CLASSIFIER_BACKEND": "onnx",
            },
            clear=False,
        ):
            classifier = load_classifier()

        self.assertIs(classifier, expected)
        mock_load_onnx.assert_called_once_with(
            "kayaaaa/ad-classifier-quantised")

    def test_predict_batches_inputs(self):
        batch_sizes = []

        def tokenizer_fn(batch_texts, **kwargs):
            batch_sizes.append(len(batch_texts))
            tensor = MagicMock()
            tensor.to.return_value = tensor
            return {"input_ids": tensor, "attention_mask": tensor}

        mock_tokenizer = MagicMock(side_effect=tokenizer_fn)
        mock_model = MagicMock()
        call_index = {"value": 0}

        def fake_model(**_inputs):
            batch_size = batch_sizes[call_index["value"]]
            call_index["value"] += 1
            outputs = MagicMock()
            outputs.logits = torch.zeros(batch_size, 2)
            return outputs

        mock_model.side_effect = fake_model
        classifier = Classifier(
            mock_tokenizer,
            mock_model,
            backend="pytorch",
            device=torch.device("cpu"),
        )
        classifier.batch_size = 8

        labels = classifier.predict(["text"] * 20)

        self.assertEqual(labels, [0] * 20)
        self.assertEqual(mock_tokenizer.call_count, 3)
        self.assertEqual(mock_model.call_count, 3)

    def test_predict_onnx_backend(self):
        mock_tokenizer = MagicMock(
            return_value={"input_ids": np.zeros((2, 4), dtype=np.int64)}
        )
        mock_model = MagicMock(
            return_value=MagicMock(
                logits=np.array([[0.1, 0.9], [0.8, 0.2]], dtype=np.float32)
            )
        )
        classifier = Classifier(mock_tokenizer, mock_model, backend="onnx")
        classifier.batch_size = 32

        labels = classifier.predict(["ad read", "normal speech"])

        self.assertEqual(labels, [1, 0])
        mock_tokenizer.assert_called_once()
        mock_model.assert_called_once()


if __name__ == "__main__":
    unittest.main()
