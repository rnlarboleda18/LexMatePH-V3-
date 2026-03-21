import hashlib
import os
import argparse
from pathlib import Path
from collections import defaultdict

def hash_file(filepath):
    """Calculate MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def find_duplicates(directory):
    """Find duplicate files in a directory."""
    hash_map = defaultdict(list)
    files = list(Path(directory).glob("*.html"))
    total_files = len(files)
    
    print(f"Scanning {total_files} files in {directory}...")
    
    for i, file_path in enumerate(files):
        try:
            file_hash = hash_file(file_path)
            hash_map[file_hash].append(file_path)
        except Exception as e:
            print(f"Error hashing {file_path}: {e}")
            
        if (i + 1) % 1000 == 0:
            print(f"Processed {i + 1}/{total_files} files...")
            
    return hash_map

def main(directory, delete=False):
    hash_map = find_duplicates(directory)
    
    duplicate_groups = {k: v for k, v in hash_map.items() if len(v) > 1}
    
    print(f"\nFound {len(duplicate_groups)} groups of duplicates.")
    
    total_duplicates = 0
    total_freed_space = 0
    
    for file_hash, file_list in duplicate_groups.items():
        # Sort by file name (ID) to potential keep the "first" one
        # Assuming lower ID is "original" or just deterministic
        # Extract ID from filename for sorting
        try:
            file_list.sort(key=lambda x: int(x.stem))
        except ValueError:
            file_list.sort() # Fallback to string sort
            
        original = file_list[0]
        duplicates = file_list[1:]
        
        total_duplicates += len(duplicates)
        
        print(f"\nHash: {file_hash}")
        print(f"  Keep: {original.name}")
        for dup in duplicates:
            print(f"  Duplicate: {dup.name}")
            if delete:
                try:
                    size = dup.stat().st_size
                    total_freed_space += size
                    dup.unlink()
                    print(f"    [DELETED] {dup.name}")
                except Exception as e:
                    print(f"    [ERROR DELETING] {dup.name}: {e}")

    print(f"\nSummary:")
    print(f"  Total duplicate files found: {total_duplicates}")
    if delete:
        print(f"  Total space freed: {total_freed_space / 1024 / 1024:.2f} MB")
    else:
        print("  (Run with --delete to remove these files)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deduplicate HTML files.")
    parser.add_argument("directory", help="Target directory")
    parser.add_argument("--delete", action="store_true", help="Delete duplicate files")
    
    args = parser.parse_args()
    
    main(args.directory, args.delete)
