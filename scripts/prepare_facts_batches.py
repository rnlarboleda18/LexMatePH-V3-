import os

def prepare_facts_batches():
    # Read all targets
    with open("target_fix_facts.txt", "r") as f:
        all_ids = set(line.strip() for line in f if line.strip())
    
    # Read processed test targets
    test_ids = set()
    if os.path.exists("target_test_facts_10.txt"):
        with open("target_test_facts_10.txt", "r") as f:
            test_ids = set(line.strip() for line in f if line.strip())
            
    # Filter
    remaining_ids = list(all_ids - test_ids)
    print(f"Total IDs: {len(all_ids)}")
    print(f"Already Processed: {len(test_ids)}")
    print(f"Remaining to Process: {len(remaining_ids)}")
    
    # Split into 20 chunks
    num_chunks = 20
    chunk_size = len(remaining_ids) // num_chunks + (1 if len(remaining_ids) % num_chunks > 0 else 0)
    
    for i in range(num_chunks):
        chunk = remaining_ids[i*chunk_size : (i+1)*chunk_size]
        if not chunk:
            continue
            
        filename = f"batch_facts_{i+1}.txt"
        with open(filename, 'w') as f:
            f.write('\n'.join(chunk))
        print(f"Created {filename} with {len(chunk)} IDs")

if __name__ == "__main__":
    prepare_facts_batches()
