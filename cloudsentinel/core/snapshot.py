"""
CloudSentinel Snapshot & Safety Engine
Provides atomic filesystem backups in '.cloudguard/snapshot/', sha256 checksums,
and guaranteed clean rollbacks if autonomous repair loops fail or exceed limits.
"""

import difflib
import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from cloudsentinel.core.exceptions import SnapshotRollbackError
from cloudsentinel.core.models import SnapshotMetadata


class SnapshotEngine:
    """
    Transactional safety engine managing pre-processor snapshots and rollbacks.
    Guarantees that no file modifications persist if security verification fails.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or Path.cwd()
        self.snapshot_root = self.base_dir / ".cloudguard" / "snapshot"
        self.snapshot_root.mkdir(parents=True, exist_ok=True)
        self.active_snapshot: Optional[SnapshotMetadata] = None

    def _compute_sha256(self, file_path: Path) -> str:
        """Compute SHA256 checksum of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def create_snapshot(self, target_file_path: Path) -> SnapshotMetadata:
        """
        Creates an immutable snapshot of the target IaC file before any mutation.
        Saves the copy and metadata inside '.cloudguard/snapshot/<snapshot_id>/'.
        """
        resolved_path = target_file_path.resolve()
        if not resolved_path.is_file():
            raise SnapshotRollbackError(
                str(resolved_path), f"Cannot snapshot non-existent file: {resolved_path}"
            )

        now_utc = datetime.now(timezone.utc)
        snapshot_id = f"snap_{now_utc.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        snapshot_dir = self.snapshot_root / snapshot_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        backup_file_path = snapshot_dir / resolved_path.name
        shutil.copy2(resolved_path, backup_file_path)

        sha256_hash = self._compute_sha256(resolved_path)
        file_size = resolved_path.stat().st_size

        metadata = SnapshotMetadata(
            snapshot_id=snapshot_id,
            created_at=now_utc,
            original_path=str(resolved_path),
            backup_path=str(backup_file_path),
            sha256=sha256_hash,
            file_size_bytes=file_size,
        )

        # Write metadata.json alongside the backup
        with open(snapshot_dir / "metadata.json", "w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json(indent=2))

        self.active_snapshot = metadata
        return metadata

    def rollback(self, snapshot_metadata: Optional[SnapshotMetadata] = None) -> bool:
        """
        Rolls back the target file to its exact snapshot baseline.
        Verifies SHA256 after restoring to guarantee complete fidelity.
        """
        target_meta = snapshot_metadata or self.active_snapshot
        if not target_meta:
            raise SnapshotRollbackError(
                str(self.base_dir), "No active snapshot available for rollback."
            )

        orig_path = Path(target_meta.original_path)
        backup_path = Path(target_meta.backup_path)

        if not backup_path.is_file():
            raise SnapshotRollbackError(
                str(backup_path), "Snapshot backup file missing or corrupted."
            )

        try:
            # Atomic replacement
            temp_path = orig_path.with_suffix(f".tmp_rollback_{uuid.uuid4().hex[:6]}")
            shutil.copy2(backup_path, temp_path)
            temp_path.replace(orig_path)

            # Integrity check
            restored_sha = self._compute_sha256(orig_path)
            if restored_sha != target_meta.sha256:
                raise SnapshotRollbackError(
                    str(orig_path),
                    f"Integrity check failed post-rollback! Expected {target_meta.sha256}, got {restored_sha}",
                )
            return True
        except Exception as e:
            if isinstance(e, SnapshotRollbackError):
                raise
            raise SnapshotRollbackError(str(orig_path), f"Rollback operation failed: {str(e)}") from e

    def generate_diff(self, modified_content: str, snapshot_metadata: Optional[SnapshotMetadata] = None) -> str:
        """
        Generates a unified diff comparing the baseline snapshot with modified content.
        """
        target_meta = snapshot_metadata or self.active_snapshot
        if not target_meta or not Path(target_meta.backup_path).is_file():
            return ""

        with open(target_meta.backup_path, "r", encoding="utf-8", errors="replace") as f:
            baseline_lines = f.readlines()

        modified_lines = modified_content.splitlines(keepends=True)
        diff_lines = difflib.unified_diff(
            baseline_lines,
            modified_lines,
            fromfile=f"a/{Path(target_meta.original_path).name} (baseline snapshot)",
            tofile=f"b/{Path(target_meta.original_path).name} (repaired candidate)",
            n=3,
        )
        return "".join(diff_lines)
