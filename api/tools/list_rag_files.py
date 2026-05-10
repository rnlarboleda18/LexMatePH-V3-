import vertexai
from vertexai.preview import rag
vertexai.init(project="gen-lang-client-0176283199", location="europe-west4")
corpus = "projects/gen-lang-client-0176283199/locations/europe-west4/ragCorpora/6917529027641081856"
files = list(rag.list_files(corpus_name=corpus))
print(f"Total RAG files in corpus: {len(files)}")
for f in files[:5]:
    print(f"  {f.name}")
