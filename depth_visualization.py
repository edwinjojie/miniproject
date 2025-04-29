import cv2
import numpy as np
import torch
import torchvision.transforms as T

class DepthVisualizer:
    def __init__(self):
        """Initialize the MiDaS model for depth estimation."""
        self.midas = torch.hub.load("intel-isl/MiDaS", "MiDaS_small", pretrained=True)
        self.midas.eval()
        self.midas.to('cpu')
        self.transform = T.Compose([
            T.ToTensor(),
            T.Resize((384, 384)),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def visualize_depth(self, frame):
        """Generate and visualize the depth map, returning both raw and color-mapped versions."""
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_input = self.transform(img_rgb).unsqueeze(0).to('cpu')
        with torch.no_grad():
            depth = self.midas(img_input)
            depth = torch.nn.functional.interpolate(
                depth.unsqueeze(1), size=frame.shape[:2], mode="bicubic", align_corners=False
            ).squeeze().cpu().numpy()
        # Normalize depth for visualization
        depth_normalized = (depth - depth.min()) / (depth.max() - depth.min())
        depth_map = (depth_normalized * 255.0).astype(np.uint8)
        color_mapped = cv2.applyColorMap(depth_map, cv2.COLORMAP_JET)
        return depth_normalized, color_mapped  # Return raw normalized depth and color-mapped image