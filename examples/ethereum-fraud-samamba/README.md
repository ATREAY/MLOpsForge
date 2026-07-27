# Example: Ethereum fraud detection with the SAMamba plugin

An end-to-end walkthrough of the platform's flagship workload, using the pieces already built:
`plugins/samamba`, the backend's dataset/job APIs, and `training-service`'s Slurm integration.

## 1. Get a dataset

The `samamba` plugin expects a CSV with one row per Ethereum address: numeric behavioral features plus a
binary `FLAG` label column (see [`plugins/samamba/README.md`](../../plugins/samamba/README.md) for the exact
shape). Any of the public Ethereum Fraud Detection datasets with this shape work — e.g. search for
"Ethereum Fraud Detection Dataset" on Kaggle. Download it to somewhere on the same filesystem the Slurm
cluster can read (e.g. under `datasets_registry/`).

## 2. Register it with the platform

```bash
python scripts/register_dataset.py \
    --api-url http://localhost:8000/api/v1 \
    --dataset-name ethereum-fraud-transactions \
    --description "Public Ethereum Fraud Detection dataset" \
    --task-type graph-classification \
    --file datasets_registry/ethereum_fraud.csv \
    --storage-mode local
```

This creates the `Dataset` + a `DatasetVersion` row via the backend API. Note the returned dataset id and
version id (or fetch them with `GET /api/v1/datasets`).

## 3. Create an experiment and submit a training job

```bash
curl -X POST localhost:8000/api/v1/experiments -H 'content-type: application/json' \
    -d '{"name": "samamba-ethereum-baseline"}'
# -> note the experiment id

curl -X POST localhost:8000/api/v1/jobs -H 'content-type: application/json' -d '{
    "experiment_id": "<experiment id>",
    "plugin_name": "samamba",
    "dataset_version_id": "<dataset version id>",
    "config": {"learning_rate": 0.001, "epochs": 20, "batch_size": 64, "hidden_dim": 64}
}'
```

The backend validates the plugin/dataset exist, creates a `Job` row, and delegates to `training-service`,
which renders and submits a real `sbatch` job to the `cse-gpu-all` partition.

## 4. Watch it run

```bash
squeue -u $USER            # on the Slurm cluster directly
curl localhost:8000/api/v1/jobs/<job id>   # via the platform
```

Once `status` reaches `finished`, the job's `checkpoint_uri` points at the trained model.

## 5. Promote it to the model registry

```bash
curl -X POST "localhost:8000/api/v1/models/from-job/<job id>?name=samamba-ethereum-fraud-detector"
```

This is the same sequence the frontend's Training/Models pages will drive through the UI once built.
