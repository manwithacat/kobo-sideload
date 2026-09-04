"""Find a mounted Kobo and copy a payload onto it."""

from __future__ import annotations

import os
import plistlib
import re
import shutil
import string
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import (
    BOOKS_FOLDER,
    BOOKS_README_NAME,
    EXCLUDE_SYNC_FOLDERS,
    EXCLUDE_SYNC_KEY,
    EXCLUDE_SYNC_SECTION,
    KOBO_CONF_REL,
    KOBO_VOLUME_LABEL,
    NICKELMENU_CONFIG_NAME,
)


@dataclass(frozen=True)
class KoboVolume:
    mountpoint: Path
    kobo_dir: Path
    conf_path: Path


def find_kobo() -> KoboVolume:
    mount = _detect_mount()
    kobo_dir = mount / ".kobo"
    if not kobo_dir.is_dir():
        raise RuntimeError(
            f"{mount} has no .kobo directory, so it is not a Kobo in USB storage mode."
        )
    return KoboVolume(
        mountpoint=mount,
        kobo_dir=kobo_dir,
        conf_path=kobo_dir.joinpath(*KOBO_CONF_REL),
    )


def _detect_mount() -> Path:
    if os.name == "nt":
        found = _windows_mount()
    elif os.uname().sysname == "Darwin":
        found = _darwin_mount()
    else:
        found = _linux_mount()
    if found is None:
        raise RuntimeError(
            "No Kobo volume is mounted. Connect the reader over USB, unlock it if asked, "
            f"and wait until a volume named {KOBO_VOLUME_LABEL} appears."
        )
    return found


def _darwin_mount() -> Path | None:
    try:
        raw = subprocess.check_output(
            ["diskutil", "info", "-plist", KOBO_VOLUME_LABEL],
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    info = plistlib.loads(raw)
    mount = info.get("MountPoint")
    return Path(mount) if mount else None


def _linux_mount() -> Path | None:
    try:
        raw = subprocess.check_output(
            ["findmnt", "-nlo", "TARGET", f"LABEL={KOBO_VOLUME_LABEL}"],
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        raw = b""
    line = raw.decode().strip()
    if line:
        return Path(line.splitlines()[0])
    by_label = Path("/dev/disk/by-label") / KOBO_VOLUME_LABEL
    if by_label.exists():
        try:
            raw = subprocess.check_output(
                ["findmnt", "-nlo", "TARGET", str(by_label.resolve())],
                stderr=subprocess.DEVNULL,
            )
            line = raw.decode().strip()
            if line:
                return Path(line.splitlines()[0])
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    return None


def _windows_mount() -> Path | None:
    import ctypes

    get_volume = ctypes.windll.kernel32.GetVolumeInformationW
    buf = ctypes.create_unicode_buffer(261)
    for letter in string.ascii_uppercase:
        root = Path(f"{letter}:/")
        if not root.exists():
            continue
        if not get_volume(f"{letter}:\\", buf, len(buf), None, None, None, None, 0):
            continue
        if buf.value == KOBO_VOLUME_LABEL and (root / ".kobo").is_dir():
            return root
    return None


def ensure_exclude_sync_folders(conf_path: Path) -> bool:
    """Write ExcludeSyncFolders, replacing an older value if needed. Returns True if changed."""
    conf_path.parent.mkdir(parents=True, exist_ok=True)
    existing = conf_path.read_text(encoding="utf-8", errors="replace") if conf_path.exists() else ""
    needle = f"{EXCLUDE_SYNC_KEY}={EXCLUDE_SYNC_FOLDERS}"
    if needle in existing:
        return False
    updated, count = re.subn(
        rf"^{re.escape(EXCLUDE_SYNC_KEY)}=.*$",
        lambda _match: needle,
        existing,
        count=1,
        flags=re.M,
    )
    if count:
        conf_path.write_text(updated, encoding="utf-8")
        return True
    block = f"\n[{EXCLUDE_SYNC_SECTION}]\n{needle}\n"
    with conf_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(block)
    return True


def ensure_books_folder(payload_dir: Path, volume: KoboVolume) -> None:
    dest = volume.mountpoint / BOOKS_FOLDER
    dest.mkdir(parents=True, exist_ok=True)
    src_readme = payload_dir / BOOKS_FOLDER / BOOKS_README_NAME
    if src_readme.is_file():
        shutil.copy2(src_readme, dest / BOOKS_README_NAME)


def plan_install(payload_dir: Path, volume: KoboVolume) -> list[str]:
    return [
        f"{volume.mountpoint / '.adds' / 'koreader'}  <-  payload/.adds/koreader",
        f"{volume.mountpoint / '.adds' / 'nm' / NICKELMENU_CONFIG_NAME}  <-  NickelMenu launch item",
        f"{volume.mountpoint / BOOKS_FOLDER}  <-  sideload library (created, never wiped)",
        f"{volume.kobo_dir / 'KoboRoot.tgz'}  <-  NickelMenu plugin (applied on eject)",
        f"{volume.conf_path}  <-  ExcludeSyncFolders (idempotent)",
    ]


def install_payload(payload_dir: Path, volume: KoboVolume) -> None:
    src_koreader = payload_dir / ".adds" / "koreader"
    src_nm = payload_dir / ".adds" / "nm" / NICKELMENU_CONFIG_NAME
    src_root = payload_dir / ".kobo" / "KoboRoot.tgz"
    for required in (src_koreader, src_nm, src_root):
        if not required.exists():
            raise RuntimeError(f"payload is incomplete: missing {required}")

    dest_koreader = volume.mountpoint / ".adds" / "koreader"
    dest_nm_dir = volume.mountpoint / ".adds" / "nm"
    dest_nm_dir.mkdir(parents=True, exist_ok=True)
    if dest_koreader.exists():
        shutil.rmtree(dest_koreader)
    shutil.copytree(src_koreader, dest_koreader)
    shutil.copy2(src_nm, dest_nm_dir / NICKELMENU_CONFIG_NAME)
    shutil.copy2(src_root, volume.kobo_dir / "KoboRoot.tgz")
    ensure_books_folder(payload_dir, volume)
    ensure_exclude_sync_folders(volume.conf_path)
    shutil.copy2(payload_dir / "MANIFEST.json", volume.mountpoint / ".adds" / "kobo-sideload-manifest.json")

    if hasattr(os, "sync"):
        os.sync()


def eject_kobo(volume: KoboVolume) -> None:
    """Unmount/eject the USB volume so Nickel can apply KoboRoot.tgz."""
    mount = str(volume.mountpoint)
    if os.name == "nt":
        letter = volume.mountpoint.drive.rstrip("\\/")
        script = (
            "$shell = New-Object -ComObject Shell.Application; "
            f"$item = $shell.NameSpace(17).ParseName('{letter}'); "
            "if (-not $item) { throw 'volume not found' }; "
            "$item.InvokeVerb('Eject')"
        )
        subprocess.check_call(["powershell", "-NoProfile", "-Command", script])
        return
    if os.uname().sysname == "Darwin":
        subprocess.check_call(["diskutil", "eject", mount])
        return
    src = subprocess.check_output(
        ["findmnt", "-nlo", "SOURCE", mount],
        stderr=subprocess.DEVNULL,
        text=True,
    ).strip()
    try:
        subprocess.check_call(["udisksctl", "unmount", "-b", src])
    except (FileNotFoundError, subprocess.CalledProcessError):
        subprocess.check_call(["umount", mount])


def verify_install(volume: KoboVolume) -> list[str]:
    missing = []
    checks = [
        volume.mountpoint / ".adds" / "koreader" / "koreader.sh",
        volume.mountpoint / ".adds" / "nm" / NICKELMENU_CONFIG_NAME,
        volume.mountpoint / BOOKS_FOLDER,
        volume.kobo_dir / "KoboRoot.tgz",
        volume.conf_path,
    ]
    for path in checks:
        if not path.exists():
            missing.append(str(path))
    if volume.conf_path.exists():
        text = volume.conf_path.read_text(encoding="utf-8", errors="replace")
        if f"{EXCLUDE_SYNC_KEY}={EXCLUDE_SYNC_FOLDERS}" not in text:
            missing.append(f"{volume.conf_path} (ExcludeSyncFolders missing)")
    return missing
