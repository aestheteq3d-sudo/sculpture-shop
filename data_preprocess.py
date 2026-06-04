import os
import argparse
import numpy as np
import trimesh
from pathlib import Path

# ------------------------------------------------------------
# Utility functions for converting STL meshes to AI‑friendly formats
# ------------------------------------------------------------

def load_mesh(stl_path: str) -> trimesh.Trimesh:
    """Load an STL file using trimesh.
    Returns a Trimesh object (will be watertight if possible)."""
    mesh = trimesh.load_mesh(stl_path, force='mesh')
    if not isinstance(mesh, trimesh.Trimesh):
        # Some STL files load as Scene; merge them into a single mesh
        mesh = trimesh.util.concatenate(mesh.geometry.values())
    return mesh

def mesh_to_point_cloud(mesh: trimesh.Trimesh, num_points: int = 2048) -> np.ndarray:
    """Sample a uniform point cloud from the mesh surface.
    Returns an (N, 3) numpy array.
    """
    # trimesh.sample.sample_surface returns (points, face_idx)
    points, _ = trimesh.sample.sample_surface(mesh, num_points)
    return points.astype(np.float32)

def mesh_to_voxel_grid(mesh: trimesh.Trimesh, resolution: int = 32) -> np.ndarray:
    """Voxelize the mesh into a binary occupancy grid.
    *resolution* is the number of voxels per axis (cube). Returns a
    (resolution, resolution, resolution) boolean ndarray.
    """
    # Compute pitch (size of each voxel) to fill the bounding box
    bounds = mesh.bounds
    max_extent = np.max(bounds[1] - bounds[0])
    pitch = max_extent / resolution
    vox = mesh.voxelized(pitch)
    # The voxel grid may be larger than the exact resolution; trim / pad
    grid = vox.matrix.astype(np.uint8)
    # Center-crop or pad to exactly `resolution`
    # Pad if smaller
    if grid.shape[0] < resolution:
        pad = (resolution - grid.shape[0]) // 2
        grid = np.pad(grid, ((pad, resolution - grid.shape[0] - pad),
                             (pad, resolution - grid.shape[1] - pad),
                             (pad, resolution - grid.shape[2] - pad)), mode='constant')
    # Crop if larger
    elif grid.shape[0] > resolution:
        start = (grid.shape[0] - resolution) // 2
        grid = grid[start:start+resolution, start:start+resolution, start:start+resolution]
    return grid

def process_stl(stl_path: str, out_dir: str, mode: str = "point", count: int = 2048, res: int = 32) -> None:
    """Convert a single STL file to the requested representation and save.
    *mode* can be "point" for point clouds or "voxel" for voxel grids.
    Saves a .npz file containing the array under the key 'data'.
    """
    mesh = load_mesh(stl_path)
    if mode == "point":
        data = mesh_to_point_cloud(mesh, num_points=count)
    elif mode == "voxel":
        data = mesh_to_voxel_grid(mesh, resolution=res)
    else:
        raise ValueError(f"Unsupported mode: {mode}")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, Path(stl_path).stem + f"_{mode}.npz")
    np.savez_compressed(out_path, data=data)
    print(f"[INFO] Saved {mode} representation to {out_path}")

def batch_process(input_dir: str, out_dir: str, mode: str, count: int, res: int) -> None:
    """Process all *.stl files in *input_dir* recursively.
    The resulting .npz files are placed under *out_dir* preserving the
    relative directory tree.
    """
    input_path = Path(input_dir)
    for stl_file in input_path.rglob('*.stl'):
        # Preserve sub‑folder hierarchy in the output directory
        relative = stl_file.relative_to(input_path).parent
        target_dir = Path(out_dir) / relative
        process_stl(str(stl_file), str(target_dir), mode=mode, count=count, res=res)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert STL files to point clouds or voxel grids for neural‑network training.")
    parser.add_argument("--input", required=True, help="Folder containing STL files (recursively scanned).")
    parser.add_argument("--output", required=True, help="Destination folder for .npz files.")
    parser.add_argument("--mode", choices=["point", "voxel"], default="point", help="Representation type.")
    parser.add_argument("--points", type=int, default=2048, help="Number of points for point‑cloud mode.")
    parser.add_argument("--resolution", type=int, default=32, help="Voxel grid resolution per axis for voxel mode.")
    args = parser.parse_args()
    batch_process(args.input, args.output, args.mode, args.points, args.resolution)
