"""
ModelAnalyzer: infers model metadata (architecture, layer info) from a model path.

Production path: load the model (e.g. via PyTorch) and inspect its architecture.
MVP: deterministic name-based inference so the decision engine can pick an
initial detection strategy (e.g. convolutional → STRIP first) without a model
runtime.
"""

import re
from pathlib import Path

from pydantic import BaseModel


class ModelMetadata(BaseModel):
    """Structured model info consumed by the decision engine."""

    path: str
    architecture: str
    is_convolutional: bool
    num_classes: int = 10
    layer_hint: str = ""


# name fragments -> (architecture, is_convolutional)
_ARCH_PATTERNS: list[tuple[re.Pattern, str, bool]] = [
    (re.compile(r"resnet", re.IGNORECASE), "resnet", True),
    (re.compile(r"vgg", re.IGNORECASE), "vgg", True),
    (re.compile(r"densenet", re.IGNORECASE), "densenet", True),
    (re.compile(r"mobilenet", re.IGNORECASE), "mobilenet", True),
    (re.compile(r"conv|cnn", re.IGNORECASE), "cnn", True),
    (re.compile(r"mlp|dense|fc|linear", re.IGNORECASE), "mlp", False),
]


class ModelAnalyzer:
    """
    Deterministic, name-based model metadata inference.

    Usage:
        analyzer = ModelAnalyzer()
        metadata = analyzer.analyze("resnet18.h5")
        # ModelMetadata(path="resnet18.h5", architecture="resnet", is_convolutional=True)
    """

    def analyze(self, model_path: str) -> ModelMetadata:
        stem = Path(model_path).stem
        architecture = "cnn"
        is_convolutional = True

        for pattern, arch, conv in _ARCH_PATTERNS:
            if pattern.search(stem):
                architecture = arch
                is_convolutional = conv
                break

        # name-derived layer hint for activation clustering
        layer_hint = "dense_2" if not is_convolutional else "conv5_block3_out"

        return ModelMetadata(
            path=model_path,
            architecture=architecture,
            is_convolutional=is_convolutional,
            num_classes=10,
            layer_hint=layer_hint,
        )
