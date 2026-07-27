"""Resolves a dataset_uri (as stored on a DatasetVersion) into a path the Slurm
job can read. Two schemes are supported:

  file:///abs/path or a bare absolute path — used as-is. This is the common
    case on a real HPC cluster: login and compute nodes share a filesystem, so
    if the dataset already lives under the repo checkout there's nothing to
    transfer.

  s3://bucket/key — downloaded locally (via boto3, from MinIO) then uploaded
    to the job's remote input directory over the same SSH connection. This is
    the path a real deployment uses once dataset files live in MinIO rather
    than directly on the cluster's filesystem.
"""

import posixpath
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from app.slurm_client import SlurmSSHClient


def resolve_dataset_path(dataset_uri: str, ssh: SlurmSSHClient, remote_input_dir: str) -> str:
    parsed = urlparse(dataset_uri)

    if parsed.scheme in ("", "file"):
        return parsed.path or dataset_uri

    if parsed.scheme == "s3":
        import boto3
        from botocore.client import Config

        from app.config import get_settings

        settings = get_settings()
        client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
        )
        bucket, key = parsed.netloc, parsed.path.lstrip("/")

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            client.download_fileobj(bucket, key, tmp)
            local_tmp_path = tmp.name

        remote_path = posixpath.join(remote_input_dir, posixpath.basename(key))
        ssh.ensure_remote_dir(remote_input_dir)
        ssh.write_remote_file(remote_path, Path(local_tmp_path).read_text())
        return remote_path

    raise ValueError(f"unsupported dataset_uri scheme: {dataset_uri!r}")
