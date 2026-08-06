# mnist_cnn plugin — handwritten digit classification

The platform's third plugin, deliberately chosen to be maximally different from the other two: `samamba` is
tabular (an MLP over engineered features), `gcn_baseline` is graph-structured (a GCN over a citation network),
and this one is image data (a small CNN over 28x28 pixel grids). Exists to prove the plugin interface actually
generalizes across data modalities, not just across model architectures within one modality.

## Dataset

Real MNIST (60,000 train + 10,000 test images), no auth needed:

```bash
python scripts/prepare_mnist_dataset.py --output datasets_registry/mnist.npz
```

Downloads the four raw IDX files and combines them into one `.npz` — consistent with how every other dataset
in this platform registers as a single file.

## Resource declaration

`plugin.yaml` requests `cse-cpu-all` with `gpus: 0` — deliberately CPU-only, to prove the platform respects
per-plugin resource declarations rather than every job requesting the same GPU shape as `samamba`/`gcn_baseline`.

**Known nuance, verified and documented rather than glossed over:** on this cluster, `cse-cpu-all` and
`cse-gpu-all` share the same physical nodes (e.g. `cse-node009` has 2 P100 GPUs and appears in both
partitions). A job that requests 0 GPUs still gets scheduled onto a GPU-equipped node here, and since nothing
requests `gres=gpu:0` to explicitly deny device visibility, CUDA can still see the physical GPU from inside
the job. The *resource request* was correctly honored (Slurm's own `ReqTRES` accounting shows no GPU
requested/billed) — it's device *isolation* that isn't strictly enforced for non-GPU jobs on this particular
cluster configuration. Confirmed via `sinfo -N -o "%N %P %G"` and `sacct ... --format=ReqTRES` after a real run.

## Verified

Trained on the real dataset both locally (`plugin.train()` directly) and through the full platform (dataset
registration → experiment → job → real Slurm job on `cse-node009` → MLflow → model registry as
`mnist-cnn-classifier` → real inference through `inference-service`): **95.2% test accuracy**, and a real
inference call on a real test-set digit predicted correctly with 99.98% confidence.
