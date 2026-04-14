"""
Create 6 PayMongo subscription plans and print the plan IDs.
Run from repo root: python api/tools/create_paymongo_plans.py
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def load_settings():
    here = Path(__file__).resolve().parent
    for candidate in (here / "local.settings.json", here.parent / "local.settings.json"):
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
            for k, v in (data.get("Values") or {}).items():
                if k not in os.environ:
                    os.environ[k] = str(v) if v is not None else ""
            return
        except OSError:
            continue


PLANS = [
    {"key": "AMICUS_MONTHLY",    "name": "Amicus Monthly",    "amount": 19900,   "interval": "month", "interval_count": 1},
    {"key": "AMICUS_YEARLY",     "name": "Amicus Yearly",     "amount": 199000,  "interval": "year",  "interval_count": 1},
    {"key": "JURIS_MONTHLY",     "name": "Juris Monthly",     "amount": 49900,   "interval": "month", "interval_count": 1},
    {"key": "JURIS_YEARLY",      "name": "Juris Yearly",      "amount": 499000,  "interval": "year",  "interval_count": 1},
    {"key": "BARRISTER_MONTHLY", "name": "Barrister Monthly", "amount": 99900,   "interval": "month", "interval_count": 1},
    {"key": "BARRISTER_YEARLY",  "name": "Barrister Yearly",  "amount": 999000,  "interval": "year",  "interval_count": 1},
]


def main():
    load_settings()
    secret = os.environ.get("PAYMONGO_SECRET_KEY", "")
    if not secret or secret.startswith("sk_test_REPLACE"):
        print("ERROR: PAYMONGO_SECRET_KEY not set in local.settings.json")
        sys.exit(1)

    encoded = base64.b64encode(f"{secret}:".encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    results = {}
    errors = []

    for p in PLANS:
        payload = json.dumps({
            "data": {
                "attributes": {
                    "name": p["name"],
                    "amount": p["amount"],
                    "currency": "PHP",
                    "interval": p["interval"],
                    "interval_count": p["interval_count"],
                }
            }
        }).encode()

        req = urllib.request.Request(
            "https://api.paymongo.com/v1/subscriptions/plans",
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read())
                plan_id = data["data"]["id"]
                results[p["key"]] = plan_id
                print(f"  OK  PAYMONGO_PLAN_{p['key']:<20s} -> {plan_id}")
        except urllib.error.HTTPError as e:
            body = json.loads(e.read())
            errs = body.get("errors", [])
            # If 'duplicate' or name already exists, try to list plans
            if any("duplicate" in (err.get("code") or "") or "already" in (err.get("detail") or "").lower() for err in errs):
                print(f"  SKIP PAYMONGO_PLAN_{p['key']:<20s} -> already exists (fetch manually from dashboard)")
            else:
                msg = json.dumps(errs)
                print(f"  ERR  PAYMONGO_PLAN_{p['key']:<20s} -> HTTP {e.code}: {msg}")
                errors.append(p["key"])

    print()
    print("=" * 60)
    print("Paste these into api/local.settings.json:")
    print("=" * 60)
    for key, plan_id in results.items():
        print(f'  "PAYMONGO_PLAN_{key}": "{plan_id}",')

    if errors:
        print(f"\n  WARNING: {len(errors)} plan(s) failed: {errors}")
        print("  Check the PayMongo Dashboard -> Products -> Plans.")
        sys.exit(1)

    print("\nDone.")


if __name__ == "__main__":
    main()
