"""Import available GCS prefixes into the Vertex AI RAG corpus."""
import vertexai
from vertexai.preview import rag
import time

vertexai.init(project="gen-lang-client-0176283199", location="europe-west4")

CORPUS = "projects/gen-lang-client-0176283199/locations/europe-west4/ragCorpora/6917529027641081856"

PREFIXES = [
    "gs://lexmateph-legal-corpus/cases/full-text-1/",
    "gs://lexmateph-legal-corpus/cases/full-text-2/",
    "gs://lexmateph-legal-corpus/statutes/provisions/",
]

for path in PREFIXES:
    print(f"\nImporting {path} ...")
    try:
        result = rag.import_files(
            corpus_name=CORPUS,
            paths=[path],
            chunk_size=512,
            chunk_overlap=100,
            max_embedding_requests_per_min=30,
        )
        print(f"  Done: {result}")
    except Exception as e:
        print(f"  FAILED: {e}")
    time.sleep(5)

print("\nAll imports submitted.")
