"""Ties the SSH client, job templating, and state store together into the two
operations main.py exposes: submit and cancel."""

import json
import logging
import posixpath

import httpx
from jinja2 import Environment, FileSystemLoader

from app.config import SERVICE_ROOT, get_settings
from app.dataset_resolver import resolve_dataset_path
from app.slurm_client import SlurmSSHClient, classify_state
from app.state_store import JobStateStore

logger = logging.getLogger(__name__)

_jinja_env = Environment(loader=FileSystemLoader(str(SERVICE_ROOT / "slurm_templates")), keep_trailing_newline=True)


def _ssh_client(settings) -> SlurmSSHClient:
    return SlurmSSHClient(
        host=settings.SLURM_SSH_HOST,
        port=settings.SLURM_SSH_PORT,
        user=settings.SLURM_SSH_USER,
        key_path=settings.SLURM_SSH_KEY_PATH,
    )


def submit_job(
    store: JobStateStore,
    job_id: str,
    plugin_entrypoint: str,
    dataset_uri: str,
    config: dict,
    resources: dict,
    callback_url: str,
) -> dict:
    settings = get_settings()
    remote_job_dir = posixpath.join(settings.remote_workdir(), job_id)
    output_dir = posixpath.join(remote_job_dir, "output")
    config_path = posixpath.join(remote_job_dir, "config.json")
    log_path = posixpath.join(remote_job_dir, "slurm.log")

    with _ssh_client(settings) as ssh:
        ssh.ensure_remote_dir(remote_job_dir)
        ssh.write_remote_file(config_path, json.dumps(config, indent=2))

        dataset_path = resolve_dataset_path(dataset_uri, ssh, posixpath.join(remote_job_dir, "input"))

        script = _jinja_env.get_template("train_job.sh.j2").render(
            job_name=f"mlopsforge-{job_id[:8]}",
            partition=resources.get("partition", settings.SLURM_DEFAULT_PARTITION),
            gpus=resources.get("gpus", 0),
            cpus_per_task=resources.get("cpus_per_task", 2),
            mem_gb=resources.get("mem_gb", 8),
            time_limit=resources.get("time_limit", "01:00:00"),
            python_bin=settings.SLURM_PYTHON_BIN,
            repo_path=settings.SLURM_REPO_PATH,
            plugin_entrypoint=plugin_entrypoint,
            dataset_path=dataset_path,
            config_path=config_path,
            output_dir=output_dir,
            log_path=log_path,
        )
        script_path = posixpath.join(remote_job_dir, "job.sh")
        ssh.write_remote_file(script_path, script)

        slurm_job_id = ssh.submit_sbatch(script_path)

    store.put(
        job_id,
        {
            "slurm_job_id": slurm_job_id,
            "status": "submitted",
            "remote_job_dir": remote_job_dir,
            "output_dir": output_dir,
            "log_path": log_path,
            "callback_url": callback_url,
        },
    )
    logger.info("job %s submitted as slurm job %s", job_id, slurm_job_id)
    return {"slurm_job_id": slurm_job_id}


def cancel_job(store: JobStateStore, slurm_job_id: str) -> None:
    settings = get_settings()
    with _ssh_client(settings) as ssh:
        ssh.cancel_job(slurm_job_id)


def reconcile_job(store: JobStateStore, job_id: str, record: dict) -> None:
    """Polls one job's Slurm state, and on a state change, both updates local
    state and calls back into the backend. On completion, also pulls the
    plugin's result.json (checkpoint path + metrics) back over SFTP."""
    settings = get_settings()
    with _ssh_client(settings) as ssh:
        raw_state = ssh.query_job_state(record["slurm_job_id"])
        new_status = classify_state(raw_state)

        if new_status == record.get("status"):
            return

        payload = {"status": new_status}

        if new_status == "finished":
            result_path = posixpath.join(record["output_dir"], "result.json")
            if ssh.remote_file_exists(result_path):
                result = json.loads(ssh.read_remote_file(result_path))
                if "error" in result:
                    new_status = "failed"
                    payload = {"status": "failed", "error_message": result["error"]}
                else:
                    payload["checkpoint_uri"] = result["checkpoint_path"]
                    # Metrics land in MLflow via the backend's callback handler,
                    # not carried in this status payload — see docs/ARCHITECTURE.md.
            payload["logs_uri"] = record.get("log_path")

    store.update(job_id, status=new_status)
    try:
        httpx.patch(record["callback_url"], json=payload, timeout=10).raise_for_status()
    except httpx.HTTPError:
        logger.exception("failed to report status for job %s to %s", job_id, record["callback_url"])
