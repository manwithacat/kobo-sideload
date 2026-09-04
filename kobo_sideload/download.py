"""Download artifacts into a cache directory and verify SHA-256."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .catalog import Artifact
from .http import urlopen


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_artifact(artifact: Artifact, cache_dir: Path, *, force: bool = False) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_dir / artifact.filename
    if dest.is_file() and not force:
        if artifact.sha256:
            actual = sha256_file(dest)
            if actual == artifact.sha256:
                return dest
            dest.unlink()
        else:
            return dest

    tmp = dest.with_suffix(dest.suffix + ".partial")
    with urlopen(artifact.url) as response, tmp.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    if artifact.sha256:
        actual = sha256_file(tmp)
        if actual != artifact.sha256:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(
                f"SHA-256 mismatch for {artifact.filename}: expected {artifact.sha256}, got {actual}"
            )
    tmp.replace(dest)
    return dest
