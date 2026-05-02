"""
Run ``ai_amendment_pipeline.py`` for a single law id with Vertex env flags.

Requires env ``VERTEX_AI_ACCESS_TOKEN`` (short-lived OAuth from ``gcloud auth print-access-token``)
or ADC per project docs. Never commit tokens.

Usage:
  python LexCode/scripts/vertex_runner.py <law_id>
"""
import os
import subprocess
import sys


def run_pipeline(law_id):
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

    cmd = [sys.executable, "LexCode/scripts/ai_amendment_pipeline.py", "--only", law_id]

    print(f"Starting Vertex Pipeline for {law_id}...")
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    for line in process.stdout or []:
        print(line, end="")
        sys.stdout.flush()

    process.wait()
    print(f"\nPipeline for {law_id} finished with exit code {process.returncode}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python vertex_runner.py <law_id>")
        sys.exit(1)
    run_pipeline(sys.argv[1])
