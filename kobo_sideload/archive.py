"""Safe zip extract/create for payload trees that contain hidden folders."""

from __future__ import annotations

import hashlib
import stat
import time
import zipfile
from pathlib import Path

EXECUTABLE_NAMES = {"install.sh"}


def safe_extract_zip(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    dest = dest.resolve()
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            target = (dest / info.filename).resolve()
            if dest not in target.parents and target != dest:
                raise RuntimeError(f"Refusing path traversal in {archive.name}: {info.filename}")
        zf.extractall(dest)


def _zip_info(path: Path, arcname: str) -> zipfile.ZipInfo:
    mtime = time.localtime(path.stat().st_mtime)
    info = zipfile.ZipInfo(arcname, date_time=mtime[:6])
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    mode = 0o755 if path.name in EXECUTABLE_NAMES else 0o644
    info.external_attr = (mode | stat.S_IFREG) << 16
    return info


def write_zip(source_dir: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue
            arcname = path.relative_to(source_dir).as_posix()
            zf.writestr(_zip_info(path, arcname), path.read_bytes())
    tmp.replace(dest)
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    dest.with_name(dest.name + ".sha256").write_text(
        f"{digest}  {dest.name}\n", encoding="utf-8"
    )
    return dest


def payload_is_ready(payload_dir: Path) -> bool:
    return (payload_dir / ".adds" / "koreader" / "koreader.sh").is_file() and (
        payload_dir / ".kobo" / "KoboRoot.tgz"
    ).is_file()
