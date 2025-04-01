import cv2
import numpy as np
import torch
import torchvision.transforms as T

class DepthVisualizer:
    def __init__(self):
        """Initialize the DepthVisualizer with MiDaS model."""
        self.midas = torch.hub.load("intel-isl/MiDaS", "MiDaS_small", pretrained=True)
        self.midas.eval()
        self.midas.to('cpu')
        self.transform = T.Compose([
            T.ToTensor(),
            T.Resize((384, 384)),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def visualize_depth(self, frame):
        """Generate and visualize the depth map of the frame."""
        # Prepare frame for MiDaS
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_input = self.transform(img_rgb).unsqueeze(0).to('cpu')
        
        # Compute depth
        with torch.no_grad():
            depth = self.midas(img_input)
            depth = torch.nn.functional.interpolate(
                depth.unsqueeze(1), size=frame.shape[:2], mode="bicubic", align_corners=False
            ).squeeze().cpu().numpy()
        
        # Normalize depth to 0-255 for visualization
        depth_normalized = (depth - depth.min()) / (depth.max() - depth.min()) * 255.0
        depth_map = depth_normalized.astype(np.uint8)
        
        # Apply a colormap for better visualization
        depth_colored = cv2.applyColorMap(depth_map, cv2.COLORMAP_JET)
        
        # Overlay depth values at object centers (for reference)
        font = cv2.FONT_HERSHEY_SIMPLEX
        for y in range(0, depth_map.shape[0], 100):  # Sample points every 100 pixels
            for x in range(0, depth_map.shape[1], 100):
                depth_value = depth_map[y, x]
                cv2.putText(depth_colored, f"{depth_value:.0f}", (x, y), font, 0.5, (255, 255, 255), 1)
        
        return depth_colored

def main():
    """Standalone depth visualization test."""
    cap = cv2.VideoCapture("videos/video2.mp4")
    visualizer = DepthVisualizer()
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        depth_frame = visualizer.visualize_depth(frame)
        cv2.imshow("Depth Visualization", depth_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()