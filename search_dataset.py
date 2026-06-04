import objaverse
import json

def search_biomorphic():
    print("Fetching Objaverse UIDs...")
    uids = objaverse.load_uids()
    print(f"Total objects in dataset: {len(uids)}")
    
    # To save memory and time, we'll search the first 50,000 objects
    search_pool = uids[:50000]
    print(f"Downloading metadata for {len(search_pool)} objects to search...")
    
    try:
        annotations = objaverse.load_annotations(search_pool)
    except Exception as e:
        print(f"Failed to load annotations: {e}")
        return

    keywords = ['biomorphic', 'organic', 'fluid', 'blob', 'alien plant', 'coral', 'fungus']
    
    matches = []
    
    print("Scanning for organic/biomorphic keywords...")
    for uid, anno in annotations.items():
        name = anno.get('name', '').lower()
        desc = anno.get('description', '').lower()
        tags = [t.get('name', '').lower() for t in anno.get('tags', [])]
        
        search_text = name + " " + desc + " " + " ".join(tags)
        
        matched_words = [k for k in keywords if k in search_text]
        if matched_words:
            matches.append({
                'uid': uid,
                'name': anno.get('name', 'Unknown'),
                'matched': matched_words,
                'tags': tags
            })
            
    print(f"\nFound {len(matches)} highly organic/biomorphic shapes!")
    print("\n--- Top 10 Matches ---")
    for m in matches[:10]:
        print(f"Name: {m['name']}")
        print(f"UID: {m['uid']}")
        print(f"Tags: {', '.join(m['tags'])}")
        print(f"Matched Keywords: {m['matched']}")
        print("-" * 30)

if __name__ == "__main__":
    search_biomorphic()
