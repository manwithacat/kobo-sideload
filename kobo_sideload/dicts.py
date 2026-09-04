"""Optional StarDict installs. Not part of the GitHub app zip."""

from __future__ import annotations

import os
import re
import shutil
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path

from .catalog import Artifact
from .download import fetch_artifact, sha256_file

LANG_RE = re.compile(r"^[a-z]{2,3}$")
KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


@dataclass(frozen=True)
class DictSpec:
    key: str
    langs: tuple[str, ...]
    label: str
    name: str
    license: str
    url: str
    filename: str
    sha256: str | None = None


def catalog_path() -> Path:
    return Path(__file__).resolve().parent / "bundled" / "dictionaries.tsv"


def load_catalog(path: Path | None = None) -> tuple[DictSpec, ...]:
    path = path or catalog_path()
    rows: list[DictSpec] = []
    seen_keys: set[str] = set()
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = [part.strip() for part in line.split("\t")]
        if len(parts) not in {7, 8}:
            raise ValueError(f"{path.name}:{lineno}: expected 7 or 8 tab-separated fields, got {len(parts)}")
        key, langs_s, label, name, license_, filename, url = parts[:7]
        sha256 = parts[7] or None if len(parts) == 8 else None
        if not KEY_RE.match(key):
            raise ValueError(f"{path.name}:{lineno}: invalid key {key!r}")
        if key in seen_keys:
            raise ValueError(f"{path.name}:{lineno}: duplicate key {key!r}")
        langs = tuple(lang.strip().lower() for lang in langs_s.split(",") if lang.strip())
        if not langs:
            raise ValueError(f"{path.name}:{lineno}: langs is empty")
        for lang in langs:
            if not LANG_RE.match(lang):
                raise ValueError(f"{path.name}:{lineno}: invalid language code {lang!r}")
        if not label or not name or not license_:
            raise ValueError(f"{path.name}:{lineno}: label, name, and license are required")
        if not filename.endswith(".tar.gz"):
            raise ValueError(f"{path.name}:{lineno}: filename must be a .tar.gz (not .tar.zst)")
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"{path.name}:{lineno}: url must be http(s)")
        seen_keys.add(key)
        rows.append(
            DictSpec(
                key=key,
                langs=langs,
                label=label,
                name=name,
                license=license_,
                url=url,
                filename=filename,
                sha256=sha256,
            )
        )
    if not rows:
        raise ValueError(f"{path.name} contains no dictionary rows")
    return tuple(rows)


CATALOG: tuple[DictSpec, ...] = load_catalog()


def available_langs(catalog: tuple[DictSpec, ...] | None = None) -> list[str]:
    seen: list[str] = []
    for spec in catalog or CATALOG:
        for lang in spec.langs:
            if lang not in seen:
                seen.append(lang)
    return seen


def lang_labels(catalog: tuple[DictSpec, ...] | None = None) -> dict[str, str]:
    labels: dict[str, str] = {}
    for spec in catalog or CATALOG:
        for lang in spec.langs:
            labels.setdefault(lang, spec.label)
    return labels


def lang_choice_hint(catalog: tuple[DictSpec, ...] | None = None) -> str:
    langs = available_langs(catalog)
    if len(langs) > 1:
        return "skip/" + "/".join(langs) + "/all"
    if langs:
        return f"skip/{langs[0]}"
    return "skip"


def format_lang_prompt(catalog: tuple[DictSpec, ...] | None = None) -> list[str]:
    labels = lang_labels(catalog)
    langs = available_langs(catalog)
    lines = [
        "Dictionaries are optional (not in the app zip). Long-press a word in KOReader to look it up.",
        "  skip   none now — download later in KOReader over Wi-Fi",
    ]
    for lang in langs:
        lines.append(f"  {lang:<6} {labels.get(lang, lang)}")
    if len(langs) > 1:
        lines.append("  all    every listed language")
    return lines


def parse_langs(value: str, catalog: tuple[DictSpec, ...] | None = None) -> list[str]:
    catalog = catalog or CATALOG
    known = available_langs(catalog)
    raw = (value or "").strip().lower().replace(";", ",")
    if raw in {"", "skip", "none", "no", "n"}:
        return []
    if raw in {"both", "all"}:
        return list(known)
    parts = [part.strip() for part in raw.replace(" ", ",").split(",") if part.strip()]
    unknown = [part for part in parts if part not in known]
    if unknown:
        raise ValueError(
            f"unknown dictionary language(s): {', '.join(unknown)}. "
            f"Known: {', '.join(known) or '(none)'}"
        )
    seen: list[str] = []
    for part in parts:
        if part not in seen:
            seen.append(part)
    return seen


def specs_for_langs(langs: list[str], catalog: tuple[DictSpec, ...] | None = None) -> list[DictSpec]:
    catalog = catalog or CATALOG
    known = set(available_langs(catalog))
    wanted = {lang.strip().lower() for lang in langs if lang.strip()}
    unknown = wanted - known
    if unknown:
        raise ValueError(
            f"unknown dictionary language(s): {', '.join(sorted(unknown))}. "
            f"Known: {', '.join(available_langs(catalog)) or '(none)'}"
        )
    return [spec for spec in catalog if wanted.intersection(spec.langs)]


def _ensure_readable(root: Path) -> None:
    """Python 3.9 keeps tar directory modes; 0o644 dirs cannot be traversed."""

    def fix(path: Path, directory: bool) -> None:
        try:
            path.chmod(path.stat().st_mode | (0o700 if directory else 0o600))
        except OSError:
            pass

    fix(root, True)
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        for name in dirnames:
            fix(current / name, True)
        for name in filenames:
            fix(current / name, False)


def _extract_tar(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    kwargs = {}
    if sys.version_info >= (3, 12):
        kwargs["filter"] = "data"
    with tarfile.open(archive) as tar:
        tar.extractall(dest, **kwargs)
    _ensure_readable(dest)


def unpack_stardict_archive(archive: Path, dest_dir: Path) -> list[Path]:
    scratch = dest_dir / ".unpack"
    if scratch.exists():
        shutil.rmtree(scratch)
    _extract_tar(archive, scratch)
    installed: list[Path] = []
    for ifo in scratch.rglob("*.ifo"):
        target = dest_dir / ifo.stem
        target.mkdir(parents=True, exist_ok=True)
        for sibling in ifo.parent.iterdir():
            if sibling.is_file():
                shutil.copy2(sibling, target / sibling.name)
            elif sibling.is_dir() and sibling.name == "res":
                shutil.copytree(sibling, target / "res", dirs_exist_ok=True)
        installed.append(target)
    shutil.rmtree(scratch, ignore_errors=True)
    if not installed:
        raise RuntimeError(f"{archive.name} contained no StarDict .ifo files")
    return installed


def fetch_dict(spec: DictSpec, cache_dir: Path, *, force: bool = False) -> Path:
    artifact = Artifact(
        name=spec.key,
        project="koreader/dictionaries",
        tag=spec.key,
        filename=spec.filename,
        url=spec.url,
        sha256=spec.sha256,
        size=None,
        published_at=None,
    )
    path = fetch_artifact(artifact, cache_dir, force=force)
    if spec.sha256:
        actual = sha256_file(path)
        if actual != spec.sha256:
            raise RuntimeError(f"SHA-256 mismatch for {spec.filename}")
    return path


def install_specs(
    specs: list[DictSpec],
    dest_dir: Path,
    cache_dir: Path,
    *,
    force: bool = False,
) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    installed: list[Path] = []
    for spec in specs:
        archive = fetch_dict(spec, cache_dir, force=force)
        installed.extend(unpack_stardict_archive(archive, dest_dir))
    return installed
