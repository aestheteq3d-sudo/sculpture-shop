import objaverse
import trimesh
import numpy as np
import os
import urllib.request
import json

def process_mesh_to_pc(filepath, num_points=2048):
    try:
        scene = trimesh.load(filepath, force='scene')
        meshes = [geom for geom in scene.geometry.values() if isinstance(geom, trimesh.Trimesh)]
        if not meshes:
            return None
        combined = trimesh.util.concatenate(meshes)
        if len(combined.faces) == 0:
            return None
            
        points, _ = trimesh.sample.sample_surface(combined, num_points)
        # Normalize
        centroid = np.mean(points, axis=0)
        points -= centroid
        max_dist = np.max(np.sqrt(np.sum(points**2, axis=1)))
        if max_dist > 0:
            points /= max_dist
        return points
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return None

def main():
    print("Fetching Objaverse UIDs...")
    try:
        uids = objaverse.load_uids()
        print(f"Total UIDs available: {len(uids)}")
        
        # Search the first 50,000 for the curated keywords
        search_pool = uids[:50000]
        print(f"Scanning metadata for {len(search_pool)} objects to find organic & table lamps...")
        annotations = objaverse.load_annotations(search_pool)
        
        keywords = [
            'biomorphic', 'organic', 'fluid', 'blob', 'coral', 'fungus', 
            'table lamp', 'schematic', 'lighting fixture', 'engineering', 'fixture'
        ]
        matches = []
        
        for uid, anno in annotations.items():
            name = anno.get('name', '').lower()
            desc = anno.get('description', '').lower()
            tags = [t.get('name', '').lower() for t in anno.get('tags', [])]
            search_text = name + " " + desc + " " + " ".join(tags)
            
            if any(k in search_text for k in keywords):
                matches.append(uid)
                if len(matches) >= 15: # Cap at 15 to keep the local download fast
                    break
                    
        print(f"Downloading {len(matches)} curated objects...")
        objects = objaverse.load_objects(matches)
        
        os.makedirs("data", exist_ok=True)
        # Clear out old random data
        for f in os.listdir("data"):
            os.remove(os.path.join("data", f))
        
        for uid, filepath in objects.items():
            print(f"Converting {uid} to Point Cloud...")
            pc = process_mesh_to_pc(filepath)
            if pc is not None:
                np.save(f"data/{uid}.npy", pc)
                print(f"Saved: data/{uid}.npy")
    except Exception as e:
        print(f"Objaverse error: {e}")

if __name__ == "__main__":
    main()
