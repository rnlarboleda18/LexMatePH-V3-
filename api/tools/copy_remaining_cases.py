"""Copy remaining case files not yet in any subfolder into full-text-3 and full-text-4."""
from google.cloud import storage
import time

PROJECT = "gen-lang-client-0176283199"
BUCKET_NAME = "lexmateph-legal-corpus"
BATCH_LIMIT = 9000

client = storage.Client(project=PROJECT)
bucket = client.bucket(BUCKET_NAME)

print("Listing all case files in cases/full-text/ ...")
all_blobs = sorted([b.name for b in bucket.list_blobs(prefix="cases/full-text/")])
all_names = {b.split("/")[-1]: b for b in all_blobs}
print(f"  Total: {len(all_blobs)}")

print("Listing already-copied files in subfolders 1 and 2 ...")
copied = set()
for sub in ["cases/full-text-1/", "cases/full-text-2/"]:
    for b in bucket.list_blobs(prefix=sub):
        copied.add(b.name.split("/")[-1])
print(f"  Already copied: {len(copied)}")

remaining = [all_names[name] for name in all_names if name not in copied]
print(f"  Remaining to copy: {len(remaining)}")

batches = [remaining[i:i+BATCH_LIMIT] for i in range(0, len(remaining), BATCH_LIMIT)]
print(f"  Will create {len(batches)} more subfolders (full-text-3, full-text-4, ...)")

for idx, batch in enumerate(batches):
    subfolder = f"cases/full-text-{idx+3}"
    print(f"\nCopying {len(batch)} files to {subfolder}/ ...")
    errors = done = 0
    for j, blob_name in enumerate(batch):
        filename = blob_name.split("/")[-1]
        dest = f"{subfolder}/{filename}"
        try:
            bucket.copy_blob(bucket.blob(blob_name), bucket, dest)
            done += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"  copy error: {e}")
        if (j+1) % 1000 == 0:
            print(f"  {j+1}/{len(batch)} ...")
    print(f"  {subfolder}: {done} copied, {errors} errors")
    time.sleep(3)

print("\nDone.")
