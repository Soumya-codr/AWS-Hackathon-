"""
Unit Tests for Snapshot & Safety Engine.
"""

import tempfile
from pathlib import Path
from cloudsentinel.core.snapshot import SnapshotEngine


def test_snapshot_creation_and_rollback():
    with tempfile.TemporaryDirectory() as temp_dir:
        dir_path = Path(temp_dir)
        test_file = dir_path / "app_infra.yaml"
        original_content = "Resources:\n  Bucket:\n    Type: AWS::S3::Bucket\n"
        test_file.write_text(original_content, encoding="utf-8")

        engine = SnapshotEngine(base_dir=dir_path)
        snapshot_meta = engine.create_snapshot(test_file)

        assert snapshot_meta is not None
        assert Path(snapshot_meta.backup_path).is_file()
        assert snapshot_meta.sha256 == engine._compute_sha256(test_file)

        # Mutate the file
        mutated_content = "Resources:\n  Bucket:\n    Type: AWS::S3::Bucket\n    Hacked: true\n"
        test_file.write_text(mutated_content, encoding="utf-8")
        assert test_file.read_text(encoding="utf-8") != original_content

        # Generate diff
        diff = engine.generate_diff(mutated_content, snapshot_meta)
        assert "+    Hacked: true" in diff

        # Trigger rollback
        success = engine.rollback(snapshot_meta)
        assert success is True
        assert test_file.read_text(encoding="utf-8") == original_content
        assert engine._compute_sha256(test_file) == snapshot_meta.sha256
