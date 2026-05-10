"""Import one small prefix and print verbose result."""
import vertexai
from vertexai.preview import rag
import json

vertexai.init(project="gen-lang-client-0176283199", location="europe-west4")
CORPUS = "projects/gen-lang-client-0176283199/locations/europe-west4/ragCorpora/6917529027641081856"

print("Importing statutes/provisions/ ...")
result = rag.import_files(
    corpus_name=CORPUS,
    paths=["gs://lexmateph-legal-corpus/statutes/provisions/"],
    chunk_size=512,
    chunk_overlap=100,
    max_embedding_requests_per_min=900,
)
print("Result type:", type(result))
print("Result:", result)
print("Dir:", [a for a in dir(result) if not a.startswith("_")])
