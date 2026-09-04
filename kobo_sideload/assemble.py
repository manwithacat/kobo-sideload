"""Turn downloaded GitHub artifacts into a device-shaped payload tree."""

from __future__ import annotations

import json
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .archive import payload_is_ready, safe_extract_zip, write_zip
from .catalog import Artifact
from .config import NICKELMENU_CONFIG, NICKELMENU_CONFIG_NAME


def _require_koreader_dir(extracted: Path) -> Path:
    candidate = extracted / "koreader"
    if (candidate / "koreader.sh").is_file():
        return candidate
    matches = list(extracted.rglob("koreader.sh"))
    if len(matches) == 1:
        return matches[0].parent
    raise RuntimeError(f"{extracted} does not contain koreader/koreader.sh")


def _copytree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def assemble(
    *,
    koreader_zip: Path,
    nickelmenu_tgz: Path,
    payload_dir: Path,
    koreader: Artifact,
    nickelmenu: Artifact,
) -> Path:
    """Build payload/.adds/koreader, payload/.adds/nm/koreader, payload/.kobo/KoboRoot.tgz."""
    if payload_dir.exists():
        shutil.rmtree(payload_dir)
    payload_dir.mkdir(parents=True)

    scratch = payload_dir / ".scratch"
    safe_extract_zip(koreader_zip, scratch)
    koreader_src = _require_koreader_dir(scratch)
    _copytree(koreader_src, payload_dir / ".adds" / "koreader")
    shutil.rmtree(scratch)

    nm_dir = payload_dir / ".adds" / "nm"
    nm_dir.mkdir(parents=True)
    (nm_dir / NICKELMENU_CONFIG_NAME).write_text(NICKELMENU_CONFIG, encoding="utf-8")

    kobo_dir = payload_dir / ".kobo"
    kobo_dir.mkdir()
    kobo_root = kobo_dir / "KoboRoot.tgz"
    shutil.copy2(nickelmenu_tgz, kobo_root)
    _assert_nickelmenu_tarball(kobo_root)

    if not (payload_dir / ".adds" / "koreader" / "koreader.sh").is_file():
        raise RuntimeError("assembled payload is missing .adds/koreader/koreader.sh")

    manifest = {
        "sideload_version": __version__,
        "assembled_at": datetime.now(timezone.utc).isoformat(),
        "launcher": "nickelmenu",
        "omitted": ["kfmon", "plato"],
        "artifacts": {
            "koreader": koreader.to_dict(),
            "nickelmenu": nickelmenu.to_dict(),
        },
        "on_device": {
            ".adds/koreader/": "KOReader application",
            f".adds/nm/{NICKELMENU_CONFIG_NAME}": "NickelMenu item that execs koreader.sh",
            ".kobo/KoboRoot.tgz": "NickelMenu Qt plugin; applied on eject/reboot",
        },
        "how_to_launch": (
            "After the Kobo finishes its 'update' reboot, open NickelMenu "
            "from the Home screen and tap KOReader."
        ),
        "upstream_licenses": {
            "koreader": "AGPL-3.0-or-later — https://github.com/koreader/koreader",
            "nickelmenu": "MIT — https://github.com/pgaskin/NickelMenu",
        },
    }
    (payload_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload_dir


def _assert_nickelmenu_tarball(path: Path) -> None:
    with tarfile.open(path, "r:gz") as tar:
        names = tar.getnames()
    if not any(name.endswith("libnm.so") for name in names):
        raise RuntimeError(f"{path} does not look like a NickelMenu KoboRoot.tgz (no libnm.so)")


def bundled_dir() -> Path:
    return Path(__file__).resolve().parent / "bundled"


def package_payload(payload_dir: Path, dist_dir: Path, koreader: Artifact, nickelmenu: Artifact) -> Path:
    if not payload_is_ready(payload_dir):
        raise RuntimeError(f"{payload_dir} is not an assembled payload")
    name = (
        f"kobo-koreader-{koreader.tag}-nickelmenu-{nickelmenu.tag}"
        f"-sideload-{__version__}.zip"
    )
    stage = dist_dir / ".stage"
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(payload_dir, stage, ignore=shutil.ignore_patterns(".scratch"))
    for src in bundled_dir().iterdir():
        if src.is_file():
            shutil.copy2(src, stage / src.name)
    try:
        return write_zip(stage, dist_dir / name)
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def extract_payload_zip(archive: Path, payload_dir: Path) -> Path:
    if payload_dir.exists():
        shutil.rmtree(payload_dir)
    safe_extract_zip(archive, payload_dir)
    if not payload_is_ready(payload_dir):
        raise RuntimeError(
            f"{archive} is not a kobo-sideload payload zip "
            "(expected .adds/koreader/koreader.sh and .kobo/KoboRoot.tgz)"
        )
    return payload_dir
