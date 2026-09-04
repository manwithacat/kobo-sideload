"""Optional StarDict installs. Not part of the GitHub app zip."""

from __future__ import annotations

import shutil
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path

from .catalog import Artifact
from .download import fetch_artifact, sha256_file


@dataclass(frozen=True)
class DictSpec:
    key: str
    langs: tuple[str, ...]
    name: str
    license: str
    url: str
    filename: str
    sha256: str | None = None


# Same archives KOReader lists in frontend/ui/data/dictionaries.lua.
# Keep install.sh URLs in sync.
CATALOG: tuple[DictSpec, ...] = (
    DictSpec(
        key="gcide",
        langs=("en",),
        name="GNU Collaborative International Dictionary of English",
        license="GPLv3+",
        url="http://build.koreader.rocks/download/dict/gcide.tar.gz",
        filename="gcide.tar.gz",
    ),
    DictSpec(
        key="rus-eng-short",
        langs=("ru",),
        name="Russian-English short dictionary",
        license="GPL",
        url=(
            "https://gitlab.com/avsej/dicts-stardict-form-xdxf/raw/"
            "d636cc5e8d4a47e22ac7466f4af6d435a8a3f650/002c/"
            "stardict-comn_sdict05_rus_eng_short-2.4.2.tar.gz"
        ),
        filename="stardict-rus-eng-short.tar.gz",
    ),
    DictSpec(
        key="ushakov",
        langs=("ru",),
        name="Ushakov explanatory dictionary (Russian)",
        license="see upstream ifo",
        url=(
            "https://gitlab.com/avsej/dicts-stardict-form-xdxf/raw/"
            "d636cc5e8d4a47e22ac7466f4af6d435a8a3f650/001/"
            "stardict-comn_dictd03_ushakov-2.4.2.tar.gz"
        ),
        filename="stardict-ushakov.tar.gz",
    ),
)


def parse_langs(value: str) -> list[str]:
    raw = (value or "").strip().lower().replace(";", ",")
    if raw in {"", "skip", "none", "no", "n"}:
        return []
    if raw in {"both", "all"}:
        return ["en", "ru"]
    parts = [part.strip() for part in raw.replace(" ", ",").split(",") if part.strip()]
    specs_for_langs(parts)
    seen: list[str] = []
    for part in parts:
        if part not in seen:
            seen.append(part)
    return seen


def specs_for_langs(langs: list[str]) -> list[DictSpec]:
    wanted = {lang.strip().lower() for lang in langs if lang.strip()}
    unknown = wanted - {"en", "ru"}
    if unknown:
        raise ValueError(f"unknown dictionary language(s): {', '.join(sorted(unknown))}")
    return [spec for spec in CATALOG if wanted.intersection(spec.langs)]


def _extract_tar(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    kwargs = {}
    if sys.version_info >= (3, 12):
        kwargs["filter"] = "data"
    with tarfile.open(archive) as tar:
        tar.extractall(dest, **kwargs)


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
