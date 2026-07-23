import logging
import os
from pathlib import Path
from typing import Optional

import timm
import torch

log = logging.getLogger(__name__)


def load_classification_model(model_name: str, weights_path: Optional[str], device: torch.device) -> torch.nn.Module:
    """Load a classification model with custom weights or ImageNet pretraining."""
    weights_path = str(weights_path) if weights_path else ''
    model = None
    if weights_path and os.path.isfile(weights_path):
        try:
            model = timm.create_model(model_name, pretrained=False, num_classes=2)
            state = torch.load(weights_path, map_location=device)
            if isinstance(state, dict) and 'model_state_dict' in state:
                state = state['model_state_dict']
            model.load_state_dict(state)
            log.info(f"Loaded {model_name} weights from {weights_path}")
        except Exception as exc:
            log.warning(f"Could not load {model_name} weights from {weights_path}: {exc}")
            model = None

    if model is None:
        log.info(f"Creating {model_name} with pretrained ImageNet weights.")
        try:
            model = timm.create_model(model_name, pretrained=True, num_classes=2)
        except Exception:
            # Some timm models require a separate reset_classifier call after loading pretrained weights
            model = timm.create_model(model_name, pretrained=True)
            if hasattr(model, 'reset_classifier'):
                model.reset_classifier(2)

    model.to(device)
    model.eval()
    return model
