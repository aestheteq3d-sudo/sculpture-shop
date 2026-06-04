import torch
import torch.nn as nn
import numpy as np
import os
import glob
from torch.utils.data import Dataset, DataLoader

class PointCloudDataset(Dataset):
    def __init__(self, data_dir):
        self.files = glob.glob(os.path.join(data_dir, "*.npy"))
        
    def __len__(self):
        return len(self.files)
        
    def __getitem__(self, idx):
        # Load point cloud of shape [2048, 3] and transpose to [3, 2048] for Conv1D
        pc = np.load(self.files[idx]).astype(np.float32)
        return torch.tensor(pc).transpose(0, 1)

class PointNetAutoencoder(nn.Module):
    def __init__(self):
        super().__init__()
        # Encoder: [Batch, 3, 2048] -> [Batch, 128]
        self.encoder = nn.Sequential(
            nn.Conv1d(3, 64, kernel_size=1),
            nn.ReLU(),
            nn.Conv1d(64, 128, kernel_size=1),
            nn.ReLU()
        )
        
        # Decoder: [Batch, 128] -> [Batch, 3, 2048]
        self.decoder = nn.Sequential(
            nn.Linear(128, 512),
            nn.ReLU(),
            nn.Linear(512, 2048 * 3)
        )
        
    def forward(self, x):
        B, C, N = x.shape
        
        # Pass through Conv1D and perform Global Max Pooling
        features = self.encoder(x) # [B, 128, N]
        global_features = features.max(dim=2)[0] # [B, 128]
        
        # Decode back into 3D points
        reconstructed = self.decoder(global_features) # [B, 2048*3]
        return reconstructed.view(B, 3, N)

def main():
    print("Initializing PyTorch 3D Training Pipeline...")
    dataset = PointCloudDataset("data")
    if len(dataset) == 0:
        print("ERROR: No point clouds found in 'data/'. Please run data_loader.py first.")
        return
        
    print(f"Found {len(dataset)} 3D models in dataset.")
    
    # We use a tiny batch size because we only downloaded 10 objects
    dataloader = DataLoader(dataset, batch_size=2, shuffle=True)
    
    # Initialize the Neural Network
    model = PointNetAutoencoder()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    # Simple MSE Loss (Note: State-of-the-art 3D uses Chamfer Distance)
    loss_fn = nn.MSELoss()
    
    epochs = 10
    print(f"Starting Training Loop for {epochs} epochs...")
    
    for epoch in range(epochs):
        total_loss = 0
        for batch_idx, batch in enumerate(dataloader):
            optimizer.zero_grad()
            
            # Forward pass
            output = model(batch)
            
            # Calculate loss and backpropagate
            loss = loss_fn(output, batch)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
        avg_loss = total_loss / len(dataloader)
        print(f"Epoch {epoch+1:02d}/{epochs} | Avg Loss: {avg_loss:.6f}")

    print("Training Complete! The network has learned a compressed latent representation of the 3D lamps.")
    
    torch.save(model.state_dict(), "lamp_autoencoder.pth")
    print("Model weights saved to lamp_autoencoder.pth!")

if __name__ == "__main__":
    main()
