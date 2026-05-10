"""Check size distribution of GCS case files."""
from google.cloud import storage

client = storage.Client(project="gen-lang-client-0176283199")
bucket = client.bucket("lexmateph-legal-corpus")

blobs = list(bucket.list_blobs(prefix="cases/full-text-1/"))
sizes = sorted([b.size for b in blobs])

if not sizes:
    print("No files found")
else:
    print(f"Files: {len(sizes)}")
    print(f"Min: {min(sizes)/1024:.1f} KB")
    print(f"Max: {max(sizes)/1024:.1f} KB")
    print(f"Median: {sizes[len(sizes)//2]/1024:.1f} KB")
    print(f"Mean: {sum(sizes)/len(sizes)/1024:.1f} KB")
    buckets = [0, 10*1024, 50*1024, 100*1024, 500*1024, 1024*1024, float("inf")]
    labels = ["<10KB", "10-50KB", "50-100KB", "100-500KB", "500KB-1MB", ">1MB"]
    counts = [0]*len(labels)
    for s in sizes:
        for i, b in enumerate(buckets[1:]):
            if s < b:
                counts[i] += 1
                break
    print("\nSize distribution:")
    for label, count in zip(labels, counts):
        print(f"  {label}: {count} ({100*count//len(sizes)}%)")
