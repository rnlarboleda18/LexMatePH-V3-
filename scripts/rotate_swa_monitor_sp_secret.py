"""
Rotate an Entra app registration client secret and push AZURE_CLIENT_SECRET to a Static Web App.

Purpose: Admin Monitor uses a service principal when SWA Free SKU blocks managed identity.

Usage:
  python scripts/rotate_swa_monitor_sp_secret.py \\
    --app-id <GUID> --subscription <GUID> \\
    --swa-name <name> --resource-group <rg>

Requires: Azure CLI, az login. Does not print the new secret.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--app-id", required=True, dest="app_id")
    p.add_argument("--subscription", required=True)
    p.add_argument("--swa-name", required=True)
    p.add_argument("--resource-group", required=True)
    p.add_argument(
        "--display-name",
        default="cli-rotate",
        help="Label for the new password credential in Entra.",
    )
    args = p.parse_args()

    az = shutil.which("az.cmd") or shutil.which("az")
    if not az:
        sys.exit("Azure CLI not found on PATH.")

    def run_az(argv: list[str]) -> str:
        r = subprocess.run([az] + argv, capture_output=True, text=True)
        if r.returncode != 0:
            sys.stderr.write(r.stderr or r.stdout or "")
            sys.exit(r.returncode)
        return r.stdout

    raw = json.loads(run_az(["ad", "app", "credential", "list", "--id", args.app_id, "-o", "json"]))
    creds = raw if isinstance(raw, list) else raw.get("passwordCredentials", [])
    old_ids = [c["keyId"] for c in creds]

    reset_out = json.loads(
        run_az(
            [
                "ad",
                "app",
                "credential",
                "reset",
                "--id",
                args.app_id,
                "--display-name",
                args.display_name,
                "-o",
                "json",
            ]
        )
    )
    pwd = reset_out["password"]

    subprocess.run(
        [
            az,
            "staticwebapp",
            "appsettings",
            "set",
            "-n",
            args.swa_name,
            "-g",
            args.resource_group,
            "--subscription",
            args.subscription,
            "--setting-names",
            f"AZURE_CLIENT_SECRET={pwd}",
        ],
        check=True,
    )

    for kid in old_ids:
        subprocess.run(
            [az, "ad", "app", "credential", "delete", "--id", args.app_id, "--key-id", kid],
            capture_output=True,
            text=True,
        )

    print("OK: SWA AZURE_CLIENT_SECRET updated; removed prior Entra password credentials listed before rotation.")


if __name__ == "__main__":
    main()
