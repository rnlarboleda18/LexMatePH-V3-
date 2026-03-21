
import os

def main():
    source = 'gemini_enbanc_opinions_ids.txt'
    if not os.path.exists(source):
        print(f"Source {source} not found.")
        return

    with open(source, 'r') as f:
        content = f.read().strip()
        ids = [x.strip() for x in content.split(',') if x.strip()]
        
    print(f"Source has {len(ids)} IDs.")
    
    test_ids = ids[:5]
    print(f"Selected 5: {test_ids}")
    
    with open('test_opinions_ids.txt', 'w') as f:
        f.write(','.join(test_ids))
        
    print("Saved test_opinions_ids.txt")

if __name__ == "__main__":
    main()
