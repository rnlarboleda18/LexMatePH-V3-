def prepare_reformat_batches():
    with open("target_reformat_facts.txt", "r") as f:
        target_ids = [line.strip() for line in f if line.strip()]
    
    num_chunks = 10
    chunk_size = len(target_ids) // num_chunks + (1 if len(target_ids) % num_chunks > 0 else 0)
    
    print(f"Splitting {len(target_ids)} cases into {num_chunks} batches...")
    
    for i in range(num_chunks):
        chunk = target_ids[i*chunk_size : (i+1)*chunk_size]
        if not chunk: continue
        
        filename = f"batch_reformat_{i+1}.txt"
        with open(filename, 'w') as f:
            f.write('\n'.join(chunk))
        print(f"Created {filename} with {len(chunk)} IDs")

if __name__ == "__main__":
    prepare_reformat_batches()
