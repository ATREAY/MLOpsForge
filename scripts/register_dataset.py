#!/usr/bin/env python3
"""CLI for onboarding a dataset into MLOpsForge — the same two-step flow the
frontend's Datasets page will eventually drive through the API directly.

Two storage modes:

  --storage-mode local   Dataset file already lives on shared storage the
                          Slurm cluster can read directly (the common case on
                          an HPC cluster with a shared filesystem — nothing is
                          uploaded, we just register a file:// URI).

  --storage-mode s3      Dataset gets uploaded to MinIO via a presigned URL
                          obtained from the backend, for when the control
                          plane's object storage is the source of truth.

Requires an account — pass --email/--password for an existing user, or
--register to create one on the fly.

Example:
    python scripts/register_dataset.py \\
        --api-url http://localhost:8000/api/v1 \\
        --email you@example.com --password "..." \\
        --dataset-name ethereum-fraud-transactions \\
        --task-type graph-classification \\
        --file datasets_registry/ethereum_txns.csv \\
        --storage-mode local
"""

import argparse
import hashlib
import sys
from pathlib import Path

import httpx


def authenticate(client: httpx.Client, email: str, password: str, register: bool) -> None:
    if register:
        resp = client.post("/auth/register", json={"email": email, "password": password})
        if resp.status_code == 409:
            print(f"user '{email}' already exists, logging in instead")
        else:
            resp.raise_for_status()
            print(f"registered new user '{email}'")

    resp = client.post("/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_or_create_dataset(client: httpx.Client, name: str, description: str, task_type: str) -> dict:
    existing = client.get("/datasets").raise_for_status().json()
    match = next((d for d in existing if d["name"] == name), None)
    if match:
        print(f"dataset '{name}' already exists (id={match['id']})")
        return match

    resp = client.post("/datasets", json={"name": name, "description": description, "task_type": task_type})
    resp.raise_for_status()
    dataset = resp.json()
    print(f"created dataset '{name}' (id={dataset['id']})")
    return dataset


def register_local(client: httpx.Client, dataset: dict, file_path: Path) -> dict:
    payload = {
        "storage_uri": f"file://{file_path.resolve()}",
        "file_hash": sha256_of(file_path),
        "size_bytes": file_path.stat().st_size,
        "stats": {},
    }
    resp = client.post(f"/datasets/{dataset['id']}/versions", json=payload)
    resp.raise_for_status()
    return resp.json()


def register_via_s3(client: httpx.Client, dataset: dict, file_path: Path) -> dict:
    upload_info = client.post(
        f"/datasets/{dataset['id']}/upload-url", params={"filename": file_path.name}
    ).raise_for_status().json()

    with file_path.open("rb") as f:
        put_resp = httpx.put(upload_info["upload_url"], content=f.read())
    put_resp.raise_for_status()

    payload = {
        "storage_uri": upload_info["storage_uri"],
        "file_hash": sha256_of(file_path),
        "size_bytes": file_path.stat().st_size,
        "stats": {},
    }
    resp = client.post(f"/datasets/{dataset['id']}/versions", json=payload)
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--task-type", required=True)
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--storage-mode", choices=["local", "s3"], default="local")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--register", action="store_true", help="create the account if it doesn't exist yet")
    args = parser.parse_args()

    if not args.file.exists():
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 1

    with httpx.Client(base_url=args.api_url, timeout=60) as client:
        authenticate(client, args.email, args.password, args.register)
        dataset = get_or_create_dataset(client, args.dataset_name, args.description, args.task_type)
        register_fn = register_local if args.storage_mode == "local" else register_via_s3
        version = register_fn(client, dataset, args.file)

    print(f"registered version {version['version']} -> {version['storage_uri']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
