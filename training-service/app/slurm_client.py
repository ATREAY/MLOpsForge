"""SSH-based Slurm client. This is the one place in the platform that talks to
the compute plane — see docs/ARCHITECTURE.md. Nothing here assumes it's running
on the same machine as Slurm; every operation is an SSH exec or SFTP transfer.
"""

import logging
import posixpath
import re
import shlex

import paramiko

logger = logging.getLogger(__name__)

# Slurm job states we care about, collapsed from squeue/sacct's full state set.
_RUNNING_STATES = {"RUNNING", "COMPLETING", "CONFIGURING"}
_PENDING_STATES = {"PENDING", "REQUEUED", "RESIZING"}
_FAILED_STATES = {"FAILED", "TIMEOUT", "NODE_FAIL", "OUT_OF_MEMORY", "BOOT_FAIL", "DEADLINE"}
_CANCELLED_STATES = {"CANCELLED"}
_COMPLETED_STATES = {"COMPLETED"}


class SlurmCommandError(RuntimeError):
    def __init__(self, command: str, exit_code: int, stderr: str):
        super().__init__(f"remote command failed (exit {exit_code}): {command}\n{stderr}")
        self.command = command
        self.exit_code = exit_code
        self.stderr = stderr


class SlurmSSHClient:
    def __init__(self, host: str, port: int, user: str, key_path: str):
        self._host = host
        self._port = port
        self._user = user
        self._key_path = key_path
        self._client: paramiko.SSHClient | None = None

    def __enter__(self) -> "SlurmSSHClient":
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(
            hostname=self._host,
            port=self._port,
            username=self._user,
            key_filename=self._key_path,
            timeout=15,
        )
        return self

    def __exit__(self, *exc_info) -> None:
        if self._client is not None:
            self._client.close()

    def _run(self, command: str) -> str:
        assert self._client is not None, "SlurmSSHClient must be used as a context manager"
        logger.debug("remote exec: %s", command)
        _, stdout, stderr = self._client.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        out, err = stdout.read().decode(), stderr.read().decode()
        if exit_code != 0:
            raise SlurmCommandError(command, exit_code, err)
        return out

    def ensure_remote_dir(self, remote_dir: str) -> None:
        self._run(f"mkdir -p {shlex.quote(remote_dir)}")

    def write_remote_file(self, remote_path: str, content: str) -> None:
        assert self._client is not None
        self.ensure_remote_dir(posixpath.dirname(remote_path))
        sftp = self._client.open_sftp()
        try:
            with sftp.open(remote_path, "w") as f:
                f.write(content)
        finally:
            sftp.close()

    def read_remote_file(self, remote_path: str) -> str:
        assert self._client is not None
        sftp = self._client.open_sftp()
        try:
            with sftp.open(remote_path, "r") as f:
                return f.read().decode()
        finally:
            sftp.close()

    def remote_file_exists(self, remote_path: str) -> bool:
        assert self._client is not None
        sftp = self._client.open_sftp()
        try:
            sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False
        finally:
            sftp.close()

    def fetch_file(self, remote_path: str, local_path: str) -> None:
        assert self._client is not None
        sftp = self._client.open_sftp()
        try:
            sftp.get(remote_path, local_path)
        finally:
            sftp.close()

    def submit_sbatch(self, remote_script_path: str) -> str:
        """Runs `sbatch <script>` and parses the job id out of Slurm's
        'Submitted batch job 12345' response."""
        output = self._run(f"sbatch {shlex.quote(remote_script_path)}")
        match = re.search(r"Submitted batch job (\d+)", output)
        if not match:
            raise SlurmCommandError(f"sbatch {remote_script_path}", 0, f"unexpected sbatch output: {output!r}")
        return match.group(1)

    def query_job_state(self, slurm_job_id: str) -> str:
        """Checks squeue first (active jobs), falls back to sacct (Slurm drops
        finished jobs from squeue almost immediately). Returns a raw Slurm
        state string; caller maps it to MLOpsForge's JobStatus."""
        squeue_out = self._run(
            f"squeue -j {shlex.quote(slurm_job_id)} --noheader --format=%T || true"
        ).strip()
        if squeue_out:
            return squeue_out.splitlines()[0].strip()

        sacct_out = self._run(
            f"sacct -j {shlex.quote(slurm_job_id)} --noheader --format=State --parsable2 || true"
        ).strip()
        if sacct_out:
            # sacct also returns step rows (e.g. "12345.batch"); the bare job id row is first.
            return sacct_out.splitlines()[0].strip().split()[0]
        return "UNKNOWN"

    def cancel_job(self, slurm_job_id: str) -> None:
        self._run(f"scancel {shlex.quote(slurm_job_id)}")


def classify_state(raw_state: str) -> str:
    """Maps a raw Slurm state string to one of MLOpsForge's JobStatus values
    (as plain strings, so training-service doesn't depend on backend's enum)."""
    state = raw_state.upper()
    if state in _RUNNING_STATES:
        return "running"
    if state in _PENDING_STATES:
        return "submitted"
    if state in _COMPLETED_STATES:
        return "finished"
    if state in _CANCELLED_STATES:
        return "cancelled"
    if state in _FAILED_STATES:
        return "failed"
    return "submitted"  # unknown/transient states default to "still going"
