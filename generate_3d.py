import torch
import numpy as np
import os
from train_3d import PointNetAutoencoder

def save_point_cloud_obj(points, filename):
    # A simple .obj file that only contains vertices (point cloud)
    with open(filename, 'w') as f:
        for p in points:
            f.write(f"v {p[0]} {p[1]} {p[2]}\n")

def main():
    if not os.path.exists("lamp_autoencoder.pth"):
        print("Please run train_3d.py first to train the model.")
        return
        
    print("Loading Trained AI Model...")
    model = PointNetAutoencoder()
    model.load_state_dict(torch.load("lamp_autoencoder.pth", weights_only=True))
    model.eval()
    
    print("Generating 3 brand new AI lamp concepts from raw math (Latent Space)...")
    
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "New art")
    os.makedirs(desktop_path, exist_ok=True)
    
    with torch.no_grad():
        for i in range(3):
            # Sample random "imagination" noise [Batch=1, Features=128]
            random_latent = torch.randn(1, 128)
            
            # Push the noise through the trained decoder to hallucinate a 3D shape
            generated_pc = model.decoder(random_latent)
            generated_pc = generated_pc.view(3, 2048).transpose(0, 1).numpy()
            
            output_file = os.path.join(desktop_path, f"AI_Generated_Lamp_{i+1}.obj")
            save_point_cloud_obj(generated_pc, output_file)
            print(f"-> Successfully exported: {output_file}")
            
    print("\nDone! You can double click these .obj files to view the raw point clouds in Windows 3D Viewer or Blender.")

if __name__ == "__main__":
    main()
