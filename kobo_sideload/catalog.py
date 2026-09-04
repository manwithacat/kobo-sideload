"""Discover current KOReader and NickelMenu GitHub releases."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from .config import KOREADER_ASSET, KOREADER_REPO, NICKELMENU_REPO
from .http import get_json

JsonGetter = Callable[[str], Any]


@dataclass(frozen=True)
class Artifact:
    name: str
    project: str
    tag: str
    filename: str
    url: str
    sha256: str | None
    size: int | None
    published_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _github_latest(owner: str, repo: str, getter: JsonGetter) -> dict[str, Any]:
    return getter(f"https://api.github.com/repos/{owner}/{repo}/releases/latest")


def _asset_sha256(asset: dict[str, Any]) -> str | None:
    digest = asset.get("digest")
    if isinstance(digest, str) and digest.startswith("sha256:"):
        return digest.split(":", 1)[1].lower()
    return None


def _find_asset(release: dict[str, Any], filename: str) -> dict[str, Any]:
    for asset in release.get("assets") or []:
        if asset.get("name") == filename:
            return asset
    names = [a.get("name") for a in (release.get("assets") or [])]
    raise RuntimeError(f"Release {release.get('tag_name')!r} has no asset {filename!r}. Assets: {names}")


def discover_koreader(firmware: str = "4", getter: JsonGetter = get_json) -> Artifact:
    if firmware not in KOREADER_ASSET:
        raise ValueError(f"firmware must be one of {sorted(KOREADER_ASSET)}, not {firmware!r}")
    owner, repo = KOREADER_REPO
    release = _github_latest(owner, repo, getter)
    tag = release["tag_name"]
    filename = KOREADER_ASSET[firmware].format(tag=tag)
    asset = _find_asset(release, filename)
    return Artifact(
        name="koreader",
        project=f"{owner}/{repo}",
        tag=tag,
        filename=filename,
        url=asset["browser_download_url"],
        sha256=_asset_sha256(asset),
        size=asset.get("size"),
        published_at=release.get("published_at"),
    )


def discover_nickelmenu(getter: JsonGetter = get_json) -> Artifact:
    owner, repo = NICKELMENU_REPO
    release = _github_latest(owner, repo, getter)
    asset = _find_asset(release, "KoboRoot.tgz")
    return Artifact(
        name="nickelmenu",
        project=f"{owner}/{repo}",
        tag=release["tag_name"],
        filename="KoboRoot.tgz",
        url=asset["browser_download_url"],
        sha256=_asset_sha256(asset),
        size=asset.get("size"),
        published_at=release.get("published_at"),
    )


def discover(firmware: str = "4", getter: JsonGetter = get_json) -> dict[str, Artifact]:
    """Return the two artifacts the default install needs.

    KFMon and Plato are intentionally absent. They are optional extras, not
    required to launch KOReader on firmware 4.6+.
    """
    return {
        "koreader": discover_koreader(firmware, getter),
        "nickelmenu": discover_nickelmenu(getter),
    }
