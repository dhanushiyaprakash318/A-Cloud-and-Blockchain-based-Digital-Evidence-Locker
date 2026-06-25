import torch
import timm
import torch.nn as nn

class XceptionDetector(nn.Module):
    def __init__(self, pretrained=True, device='cpu'):
        super(XceptionDetector, self).__init__()
        # Load Xception from timm
        # output_stride=8 or 16 usually works well.
        self.model = timm.create_model('xception', pretrained=pretrained)
        
        # Replace classifier for 2 classes: Real vs Fake
        # Check num features
        num_ftrs = self.model.get_classifier().in_features
        self.model.fc = nn.Linear(num_ftrs, 2)
        
        self.device = device
        self.to(device)
        self.eval()

    def forward(self, x):
        return self.model(x)

    def load_weights(self, path):
        if path:
            try:
                state_dict = torch.load(path, map_location=self.device)
                self.load_state_dict(state_dict)
                print(f"Loaded Xception weights from {path}")
            except Exception as e:
                print(f"Could not load custom Xception weights: {e}. Using ImageNet/Random.")
