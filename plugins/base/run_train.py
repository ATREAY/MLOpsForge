"""CLI entrypoint the generated Slurm job script actually runs:

    python -m plugins.base.run_train \
        --plugin-entrypoint plugins.samamba.plugin:SAMambaPlugin \
        --dataset-path /path/to/dataset \
        --config-path /path/to/config.json \
        --output-dir /path/to/output

Writes result.json to --output-dir on completion (or on failure, with an
"error" key) so training-service can read the outcome back over SFTP without
scraping stdout.
"""

import argparse
import json
import sys
import traceback
from pathlib import Path

# Allow running this file directly (as Slurm's sbatch script does) without the
# repo being pip-installed: make the repo root importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from plugins.base.registry import load_plugin  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin-entrypoint", required=True)
    parser.add_argument("--dataset-path", required=True)
    parser.add_argument("--config-path", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "result.json"

    with open(args.config_path) as f:
        config = json.load(f)

    try:
        plugin = load_plugin(args.plugin_entrypoint)
        result = plugin.train(dataset_path=args.dataset_path, config=config, output_dir=str(output_dir))
    except Exception as exc:  # noqa: BLE001 — deliberately broad: any failure must be reported, not crash silently
        result_path.write_text(json.dumps({"error": str(exc), "traceback": traceback.format_exc()}, indent=2))
        print(f"[run_train] FAILED: {exc}", file=sys.stderr)
        return 1

    result_path.write_text(
        json.dumps(
            {"checkpoint_path": result.checkpoint_path, "metrics": result.metrics, "artifacts": result.artifacts},
            indent=2,
        )
    )
    print(f"[run_train] finished, metrics={result.metrics}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
