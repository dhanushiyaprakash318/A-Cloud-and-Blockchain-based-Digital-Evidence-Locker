import torch
import cv2
import numpy as np

class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        
        # Register hooks
        self.target_layer.register_forward_hook(self.save_activation)
        self.target_layer.register_full_backward_hook(self.save_gradient)
        
    def save_activation(self, module, input, output):
        self.activations = output
        
    def save_gradient(self, module, grad_input, grad_output):
        # grad_output is a tuple
        self.gradients = grad_output[0]
        
    def __call__(self, x, class_idx=None):
        self.model.zero_grad()
        output = self.model(x)
        
        if class_idx is None:
            class_idx = torch.argmax(output, dim=1)
            
        score = output[0, class_idx]
        score.backward()
        
        gradients = self.gradients
        activations = self.activations
        
        # Pool the gradients
        weights = torch.mean(gradients, dim=(2, 3), keepdim=True)
        
        # Multiply activations by weights
        cam = torch.sum(weights * activations, dim=1, keepdim=True)
        cam = torch.relu(cam)
        
        # Upsample to input size
        cam = cam.detach().cpu().numpy()
        cam = cam[0, 0, :, :]
        
        cam = cv2.resize(cam, (x.shape[3], x.shape[2]))
        
        # Normalize
        cam -= np.min(cam)
        cam /= np.max(cam) + 1e-8
        
        return cam, output
