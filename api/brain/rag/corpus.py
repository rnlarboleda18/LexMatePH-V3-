"""
Vertex AI RAG Engine corpus management via REST API.

Usage:
    python -m api.brain.rag.corpus --action create
    python -m api.brain.rag.corpus --action import
    python -m api.brain.rag.corpus --action import --prefix cases/full-text
    python -m api.brain.rag.corpus --action status
    python -m api.brain.rag.corpus --action list
"""

import argparse
import json
import logging
import os
import sys
import time

import requests
import google.auth
import google.auth.transport.requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

if config.GCP_CREDENTIALS_FILE and os.path.exists(config.GCP_CREDENTIALS_FILE):
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", config.GCP_CREDENTIALS_FILE)

# RAG Engine region — europe-west4 avoids Spanner capacity restrictions on new projects.
# Gemini models are called separately (us-central1) so cross-region is fine.
RAG_REGION = os.getenv("RAG_REGION", "europe-west4")

# Project-scoped base — used only for corpus creation (POST /ragCorpora)
BASE_URL = (
    f"https://{RAG_REGION}-aiplatform.googleapis.com/v1beta1"
    f"/projects/{config.GCP_PROJECT}/locations/{RAG_REGION}"
)
# Root API base — used when corpus_name is already a full resource path
API_ROOT = f"https://{RAG_REGION}-aiplatform.googleapis.com/v1beta1"
CORPUS_FILE = os.path.join(os.path.dirname(__file__), ".corpus_name")


# ── Auth ───────────────────────────────────────────────────────────────────────

def _get_token() -> str:
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
    }


def _raise_for_status(resp: requests.Response) -> None:
    if not resp.ok:
        log.error(f"API error {resp.status_code}: {resp.text[:500]}")
        resp.raise_for_status()


# ── Corpus CRUD ────────────────────────────────────────────────────────────────

def create_corpus() -> str:
    """Create a new RAG corpus and return its resource name."""
    log.info("Creating Vertex AI RAG corpus...")

    body = {
        "display_name": "LexMatePH Legal Corpus",
        "description": (
            "Philippine legal corpus: SC decisions (full text + digests), "
            "statutes (Family Code, Civil Code, RPC, ROC), and legal concepts. "
            "Powers the LexMatePH Legal Expert AI."
        ),
        "rag_embedding_model_config": {
            "vertex_prediction_endpoint": {
                "endpoint": f"projects/{config.GCP_PROJECT}/locations/{RAG_REGION}"
                            f"/publishers/google/models/text-embedding-004"
            }
        },
    }

    resp = requests.post(
        f"{BASE_URL}/ragCorpora",
        headers=_headers(),
        json=body,
    )
    _raise_for_status(resp)
    data = resp.json()

    # CreateRagCorpus returns an LRO — poll until done to get corpus name
    if "name" in data and "/operations/" in data["name"]:
        log.info(f"Waiting for corpus creation LRO: {data['name']}")
        lro_url = f"https://{RAG_REGION}-aiplatform.googleapis.com/v1beta1/{data['name']}"
        op = _poll_operation(lro_url)
        corpus_name = op.get("response", {}).get("name", data["name"])
    else:
        corpus_name = data["name"]

    log.info(f"Corpus created: {corpus_name}")
    _save_corpus_name(corpus_name)
    return corpus_name


def list_corpora() -> list:
    resp = requests.get(f"{BASE_URL}/ragCorpora", headers=_headers())
    _raise_for_status(resp)
    corpora = resp.json().get("ragCorpora", [])
    for c in corpora:
        log.info(f"  {c['name']}  ({c.get('display_name', '')})")
    return corpora


def get_corpus_status(corpus_name: str = None) -> dict:
    if not corpus_name:
        corpus_name = _load_corpus_name()
    if not corpus_name:
        raise ValueError("No corpus name. Run --action create first.")

    files = []
    page_token = None
    while True:
        params = {"pageSize": 1000}
        if page_token:
            params["pageToken"] = page_token
        resp = requests.get(f"{API_ROOT}/{corpus_name}/ragFiles", headers=_headers(), params=params)
        _raise_for_status(resp)
        data = resp.json()
        files.extend(data.get("ragFiles", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    status = {
        "corpus_name": corpus_name,
        "total_files": len(files),
        "sample":      [f["name"] for f in files[:5]],
    }
    log.info(f"Corpus status: {json.dumps(status, indent=2)}")
    return status


# ── Import ─────────────────────────────────────────────────────────────────────

def import_files(corpus_name: str = None, gcs_prefix: str = None) -> list:
    """
    Import GCS files into the RAG corpus.
    Returns list of LRO (long-running operation) names.
    """
    if not corpus_name:
        corpus_name = _load_corpus_name()
    if not corpus_name:
        raise ValueError("No corpus name. Run --action create first.")

    bucket_base = f"gs://{config.GCS_CORPUS_BUCKET}"

    if gcs_prefix:
        prefixes = {gcs_prefix: f"{bucket_base}/{gcs_prefix}/"}
    else:
        prefixes = {
            "cases":      f"{bucket_base}/{config.GCS_CASES_PREFIX}/",
            "statutes":   f"{bucket_base}/{config.GCS_PROVISIONS_PREFIX}/",
            "flashcards": f"{bucket_base}/{config.GCS_BAR_PREFIX}/",
        }

    lros = []
    for label, gcs_uri in prefixes.items():
        log.info(f"Importing {label} from {gcs_uri}")

        body = {
            "import_rag_files_config": {
                "gcs_source": {
                    "uris": [gcs_uri]
                },
                "rag_file_chunking_config": {
                    "fixed_length_chunking_config": {
                        "chunk_size":    config.RAG_CHUNK_SIZE,
                        "chunk_overlap": config.RAG_CHUNK_OVERLAP,
                    }
                },
                "max_embedding_requests_per_min": 30,
            }
        }

        resp = requests.post(
            f"{API_ROOT}/{corpus_name}:importRagFiles",
            headers=_headers(),
            json=body,
        )
        _raise_for_status(resp)
        lro = resp.json()
        lro_name = lro.get("name", "unknown")
        log.info(f"Import LRO for {label}: {lro_name}")
        lros.append({"label": label, "lro": lro_name})

    return lros


def _poll_operation(lro_url: str, timeout_sec: int = 120) -> dict:
    """Poll an LRO URL until done. Returns the completed operation."""
    deadline = time.time() + timeout_sec
    interval = 3
    while time.time() < deadline:
        resp = requests.get(lro_url, headers=_headers())
        _raise_for_status(resp)
        op = resp.json()
        if op.get("done"):
            return op
        log.info(f"Operation pending... retrying in {interval}s")
        time.sleep(interval)
        interval = min(interval * 1.5, 15)
    raise TimeoutError(f"Operation did not complete in {timeout_sec}s")


def poll_lro(lro_name: str, timeout_sec: int = 3600) -> dict:
    """Poll a long-running operation until done."""
    url = f"https://{config.GCP_LOCATION}-aiplatform.googleapis.com/v1beta1/{lro_name}"
    deadline = time.time() + timeout_sec
    interval = 10

    while time.time() < deadline:
        resp = requests.get(url, headers=_headers())
        _raise_for_status(resp)
        op = resp.json()

        if op.get("done"):
            if "error" in op:
                log.error(f"LRO failed: {op['error']}")
            else:
                log.info(f"LRO complete: {json.dumps(op.get('response', {}), indent=2)}")
            return op

        log.info(f"LRO pending... checking again in {interval}s")
        time.sleep(interval)
        interval = min(interval * 1.5, 60)

    raise TimeoutError(f"LRO {lro_name} did not complete in {timeout_sec}s")


# ── Persistence ────────────────────────────────────────────────────────────────

def _save_corpus_name(name: str) -> None:
    with open(CORPUS_FILE, "w") as f:
        f.write(name)
    log.info(f"Saved corpus name to {CORPUS_FILE}")
    log.info(f"Add to local.settings.json: RAG_CORPUS_NAME = {name}")


def _load_corpus_name() -> str | None:
    if config.RAG_CORPUS_NAME:
        return config.RAG_CORPUS_NAME
    if os.path.exists(CORPUS_FILE):
        with open(CORPUS_FILE) as f:
            return f.read().strip()
    return None


def load_corpus_name() -> str | None:
    return _load_corpus_name()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Manage Vertex AI RAG Engine corpus")
    parser.add_argument("--action", choices=["create", "import", "status", "list"],
                        required=True)
    parser.add_argument("--corpus-name", help="Override corpus resource name")
    parser.add_argument("--prefix", help="Only import a specific GCS prefix folder")
    parser.add_argument("--poll", action="store_true",
                        help="Poll import LROs until complete (blocking)")
    args = parser.parse_args()

    if args.action == "create":
        name = create_corpus()
        print(f"\nCorpus created: {name}")
        print("Next: run --action import once GCS export finishes")

    elif args.action == "import":
        lros = import_files(args.corpus_name, args.prefix)
        print(f"\nStarted {len(lros)} import job(s):")
        for lro in lros:
            print(f"  {lro['label']}: {lro['lro']}")
        if args.poll:
            for lro in lros:
                print(f"\nPolling {lro['label']}...")
                result = poll_lro(lro["lro"])
                print(json.dumps(result, indent=2))

    elif args.action == "status":
        status = get_corpus_status(args.corpus_name)
        print(json.dumps(status, indent=2))

    elif args.action == "list":
        corpora = list_corpora()
        print(json.dumps(corpora, indent=2))


if __name__ == "__main__":
    main()
