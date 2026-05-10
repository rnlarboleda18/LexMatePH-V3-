from google.cloud import storage
client = storage.Client(project="gen-lang-client-0176283199")
bucket = client.bucket("lexmateph-legal-corpus")
for prefix in ["cases/full-text-1/", "cases/full-text-2/", "cases/full-text-3/", "statutes/provisions/"]:
    count = sum(1 for _ in bucket.list_blobs(prefix=prefix))
    print(f"{prefix}: {count} files")
