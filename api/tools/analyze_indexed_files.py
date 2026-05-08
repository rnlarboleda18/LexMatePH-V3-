"""Check what files ARE indexed in the corpus vs what's in GCS."""
import vertexai
from vertexai.preview import rag
from google.cloud import storage

vertexai.init(project="gen-lang-client-0176283199", location="europe-west4")
CORPUS = "projects/gen-lang-client-0176283199/locations/europe-west4/ragCorpora/6917529027641081856"

# Get indexed file display names
rag_files = list(rag.list_files(corpus_name=CORPUS))
print(f"Total indexed: {len(rag_files)}")

# Sample display names
names = []
for f in rag_files[:20]:
    dn = getattr(f, "display_name", "") or getattr(f, "name", "")
    names.append(dn)
    print(f"  {dn[:80]}")

# Check sizes of indexed files in GCS
client = storage.Client(project="gen-lang-client-0176283199")
bucket = client.bucket("lexmateph-legal-corpus")

print("\nSampling sizes of indexed files:")
sizes = []
for name in names[:10]:
    filename = name.split("/")[-1] if "/" in name else name
    # Try to find this file
    for prefix in ["cases/full-text-1/", "cases/full-text/"]:
        blobs = list(bucket.list_blobs(prefix=prefix + filename[:20]))
        if blobs:
            sizes.append(blobs[0].size)
            print(f"  {filename[:40]}: {blobs[0].size/1024:.1f} KB")
            break
