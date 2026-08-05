from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.dataset import Dataset, DatasetVersion
from app.models.job import Job
from app.models.user import User
from app.schemas.dataset import (
    DatasetCreate,
    DatasetRead,
    DatasetVersionCreate,
    DatasetVersionRead,
    DatasetWithVersions,
)
from app.services.storage import object_uri, presigned_put_url

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetRead])
def list_datasets(db: Session = Depends(get_db)):
    return db.query(Dataset).order_by(Dataset.created_at.desc()).all()


@router.post("", response_model=DatasetRead, status_code=201)
def create_dataset(
    payload: DatasetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if db.query(Dataset).filter(Dataset.name == payload.name).first():
        raise HTTPException(409, f"dataset '{payload.name}' already exists")
    dataset = Dataset(**payload.model_dump(), owner_id=current_user.id)
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


@router.get("/{dataset_id}", response_model=DatasetWithVersions)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(404, "dataset not found")
    return dataset


@router.delete("/{dataset_id}", status_code=204)
def delete_dataset(
    dataset_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(404, "dataset not found")

    # owner_id is NULL on datasets created before auth existed (e.g. the
    # Cora/Ethereum datasets from early testing) — anyone can clean those up.
    # Datasets created since must be deleted by their owner.
    if dataset.owner_id is not None and dataset.owner_id != current_user.id:
        raise HTTPException(403, "only the dataset's owner can delete it")

    version_ids = [v.id for v in dataset.versions]
    in_use = db.query(Job).filter(Job.dataset_version_id.in_(version_ids)).first() if version_ids else None
    if in_use is not None:
        raise HTTPException(409, "cannot delete a dataset with a version referenced by an existing job")

    db.delete(dataset)  # cascades to DatasetVersion rows (see Dataset.versions relationship)
    db.commit()


@router.post("/{dataset_id}/upload-url")
def get_upload_url(dataset_id: str, filename: str, db: Session = Depends(get_db)):
    """Step 1 of registering a new version: client asks for a presigned URL,
    uploads the file directly to MinIO, then calls POST .../versions with the
    resulting key + a hash it computed client-side."""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(404, "dataset not found")
    next_version = len(dataset.versions) + 1
    key = f"datasets/{dataset.name}/v{next_version}/{filename}"
    return {"upload_url": presigned_put_url(key), "storage_uri": object_uri(key)}


@router.post("/{dataset_id}/versions", response_model=DatasetVersionRead, status_code=201)
def register_dataset_version(
    dataset_id: str, payload: DatasetVersionCreate, db: Session = Depends(get_db)
):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(404, "dataset not found")
    if not (32 <= len(payload.file_hash) <= 64):
        raise HTTPException(422, "file_hash must be a sha256 hex digest")

    next_version = len(dataset.versions) + 1
    version = DatasetVersion(
        dataset_id=dataset.id,
        version=next_version,
        storage_uri=payload.storage_uri,
        file_hash=payload.file_hash,
        size_bytes=payload.size_bytes,
        stats=payload.stats,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version
