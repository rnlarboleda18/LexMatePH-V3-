"""
full-text-3/ has 17,506 files (exceeds 10k limit).
Split: keep first 9,000 in full-text-3/, move rest to full-text-5/.
"""
import time, sys
sys.path.insert(0, ".")
from google.cloud import storage

PROJECT = "gen-lang-client-0545071081"
BUCKET = "lexmateph-legal-corpus"
SRC_PREFIX = "cases/full-text-3/"
DEST_PREFIX = "cases/full-text-5/"
KEEP = 9000

client = storage.Client(project=PROJECT)
bucket = client.bucket(BUCKET)

print(f"Listing {SRC_PREFIX}...")
all_blobs = sorted([b.name for b in bucket.list_blobs(prefix=SRC_PREFIX)])
print(f"Total: {len(all_blobs)}")

to_move = all_blobs[KEEP:]
print(f"Keeping first {KEEP} in full-text-3/, moving {len(to_move)} to full-text-5/")

errors = 0
for i, blob_name in enumerate(to_move):
    filename = blob_name.split("/")[-1]
    dest_name = DEST_PREFIX + filename
    try:
        bucket.copy_blob(bucket.blob(blob_name), bucket, dest_name)
        bucket.blob(blob_name).delete()
    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f"  ERR {blob_name}: {e}")
    if (i + 1) % 500 == 0:
        print(f"  {i+1}/{len(to_move)} moved...", flush=True)

print(f"\nDone. Moved {len(to_move)-errors}, errors={errors}")

# Verify
count3 = sum(1 for _ in bucket.list_blobs(prefix=SRC_PREFIX))
count5 = sum(1 for _ in bucket.list_blobs(prefix=DEST_PREFIX))
print(f"full-text-3/: {count3}  full-text-5/: {count5}")
