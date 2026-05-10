from google.cloud import storage
client = storage.Client(project="gen-lang-client-0176283199")
bucket = client.bucket("lexmateph-legal-corpus")
total = 0
for prefix in ["cases/full-text-1/", "cases/full-text-2/", "cases/full-text-3/",
               "cases/full-text-4/", "statutes/provisions/", "bar-exam/"]:
    count = sum(1 for _ in bucket.list_blobs(prefix=prefix))
    if count:
        print(f"{prefix}: {count}")
        total += count
orig = sum(1 for _ in bucket.list_blobs(prefix="cases/full-text/"))
print(f"\ncases/full-text/ (original): {orig}")
print(f"Batched total: {total}")
