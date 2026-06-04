import os
import torch
import numpy as np
from skimage import measure
import trimesh

# Set deterministic behavior
torch.manual_seed(42)
np.random.seed(42)

class SDFNetwork(torch.nn.Module):
    """A tiny implicit network that maps (x, y, z, latent) -> signed distance.
    For demonstration, we use a simple 4‑layer MLP with ReLU activations.
    In practice you would train this on a dataset of lamp shapes.
    """
    def __init__(self, latent_dim: int = 128, hidden_dim: int = 256):
        super().__init__()
        self.latent_dim = latent_dim
        self.net = torch.nn.Sequential(
            torch.nn.Linear(3 + latent_dim, hidden_dim),
            torch.nn.ReLU(inplace=True),
            torch.nn.Linear(hidden_dim, hidden_dim),
            torch.nn.ReLU(inplace=True),
            torch.nn.Linear(hidden_dim, hidden_dim),
            torch.nn.ReLU(inplace=True),
            torch.nn.Linear(hidden_dim, 1),
        )
        # Initialize weights for reproducibility
        torch.nn.init.xavier_uniform_(self.net[0].weight)
        torch.nn.init.xavier_uniform_(self.net[2].weight)
        torch.nn.init.xavier_uniform_(self.net[4].weight)
        torch.nn.init.xavier_uniform_(self.net[6].weight)

    def forward(self, pts: torch.Tensor, latent: torch.Tensor) -> torch.Tensor:
        # pts: (N, 3), latent: (latent_dim,)
        latent_expanded = latent.unsqueeze(0).expand(pts.shape[0], -1)
        inp = torch.cat([pts, latent_expanded], dim=1)
        return self.net(inp).squeeze(-1)

def generate_sdf_mesh(latent_vec: np.ndarray, bounds: float = 1.0, resolution: int = 128) -> trimesh.Trimesh:
    """Generate a mesh from a latent vector using the SDFNetwork.

    Args:
        latent_vec: (latent_dim,) numpy array describing the shape.
        bounds: Extent of the cubic query volume (±bounds on each axis).
        resolution: Number of voxels per axis for the grid.
    Returns:
        trimesh.Trimesh object of the extracted iso‑surface (level 0).
    """
    device = torch.device('cpu')
    net = SDFNetwork(latent_dim=latent_vec.shape[0]).to(device)
    net.eval()
    latent = torch.from_numpy(latent_vec).float().to(device)

    # Create a dense grid of 3‑D points
    lin = np.linspace(-bounds, bounds, resolution, dtype=np.float32)
    xx, yy, zz = np.meshgrid(lin, lin, lin, indexing='ij')
    pts = np.stack([xx.ravel(), yy.ravel(), zz.ravel()], axis=1)
    pts_tensor = torch.from_numpy(pts).float().to(device)

    # Evaluate SDF in batches to avoid OOM
    batch = 65536
    sdf_vals = []
    with torch.no_grad():
        for i in range(0, pts_tensor.shape[0], batch):
            batch_pts = pts_tensor[i:i+batch]
            sdf = net(batch_pts, latent).cpu().numpy()
            sdf_vals.append(sdf)
    sdf_grid = np.concatenate(sdf_vals).reshape(resolution, resolution, resolution)

    # Marching cubes on the zero‑level set
    verts, faces, normals, _ = measure.marching_cubes(sdf_grid, level=0.0, spacing=(2*bounds/(resolution-1),) * 3)
    # Center the mesh around the origin
    verts = verts - np.mean(verts, axis=0)
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, vertex_normals=normals, process=False)
    return mesh

def save_mesh(mesh: trimesh.Trimesh, filename: str):
    """Export the mesh to STL (binary) for downstream processing."""
    mesh.export(filename)
    print(f"[INFO] Saved SDF‑generated mesh to {filename}")

if __name__ == "__main__":
    # Quick demo: random latent -> mesh
    latent = np.random.randn(128).astype(np.float32)
    mesh = generate_sdf_mesh(latent, bounds=1.0, resolution=128)
    out_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'New art', 'sdf_demo.stl')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    save_mesh(mesh, out_path)
