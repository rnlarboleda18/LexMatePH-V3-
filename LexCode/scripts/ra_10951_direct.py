"""
One-shot launcher for RA 10951 batch amendment ingest.

Requires env ``VERTEX_AI_ACCESS_TOKEN`` (short-lived OAuth from ``gcloud auth print-access-token``)
or rely on Application Default Credentials per ``lexcode_genai_client``. Never commit tokens.
"""
import os
import subprocess
import sys


def main():
    token = (os.environ.get("VERTEX_AI_ACCESS_TOKEN") or "").strip()
    if not token:
        print(
            "VERTEX_AI_ACCESS_TOKEN is not set. Export it (e.g. from `gcloud auth print-access-token`) "
            "or use ADC; do not paste tokens into source files.",
            file=sys.stderr,
        )
        sys.exit(1)

    env = os.environ.copy()
    env["VERTEX_AI_ACCESS_TOKEN"] = token
    env["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

    cmd = [
        sys.executable,
        "LexCode/scripts/process_amendment_batch_ai.py",
        "LexCode/Codals/md/ra_10951_2017.md",
    ]

    print("Launching RA 10951 Ingestion...")
    subprocess.run(cmd, env=env, check=False)


if __name__ == "__main__":
    main()
