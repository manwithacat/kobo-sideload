"""CLI: discover → fetch → assemble → package → install."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .archive import payload_is_ready
from .assemble import assemble, extract_payload_zip, package_payload
from .catalog import Artifact, discover
from .device import (
    dictionaries_dir,
    eject_kobo,
    ensure_dictionaries_folder,
    ensure_stardict_lua,
    find_kobo,
    install_payload,
    plan_install,
    verify_install,
)
from .dicts import (
    available_langs,
    format_lang_prompt,
    install_specs,
    lang_choice_hint,
    parse_langs,
    specs_for_langs,
)
from .download import fetch_artifact, sha256_file
from .paths import default_home, work_dirs


def _dirs(root: Path) -> dict[str, Path]:
    return work_dirs(root)


def _load_catalog(path: Path) -> dict[str, Artifact]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {key: Artifact(**value) for key, value in data["artifacts"].items()}


def _save_catalog(path: Path, artifacts: dict[str, Artifact], firmware: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "firmware": firmware,
        "artifacts": {key: art.to_dict() for key, art in artifacts.items()},
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cmd_discover(args: argparse.Namespace) -> int:
    dirs = _dirs(args.root)
    artifacts = discover(firmware=args.firmware)
    _save_catalog(dirs["catalog"], artifacts, args.firmware)
    print(f"Firmware family: {args.firmware}.x")
    print(f"Wrote {dirs['catalog']}")
    print()
    print(f"{'component':<12} {'tag':<14} {'file':<40} sha256")
    for name, art in artifacts.items():
        digest = (art.sha256 or "—")[:12]
        print(f"{name:<12} {art.tag:<14} {art.filename:<40} {digest}")
    print()
    print("Not fetched: KFMon, Plato. They are not required to launch KOReader.")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    dirs = _dirs(args.root)
    if not dirs["catalog"].is_file():
        cmd_discover(args)
    artifacts = _load_catalog(dirs["catalog"])
    for name, art in artifacts.items():
        path = fetch_artifact(art, dirs["cache"], force=args.force)
        digest = sha256_file(path)
        print(f"{name:<12} {path}  sha256:{digest}")
    return 0


def cmd_assemble(args: argparse.Namespace) -> int:
    dirs = _dirs(args.root)
    artifacts = _load_catalog(dirs["catalog"])
    payload = assemble(
        koreader_zip=dirs["cache"] / artifacts["koreader"].filename,
        nickelmenu_tgz=dirs["cache"] / artifacts["nickelmenu"].filename,
        payload_dir=dirs["payload"],
        koreader=artifacts["koreader"],
        nickelmenu=artifacts["nickelmenu"],
    )
    print(f"Payload: {payload}")
    for rel in (
        ".adds/koreader/koreader.sh",
        ".adds/nm/koreader",
        ".kobo/KoboRoot.tgz",
        "KOReader/README.txt",
        "MANIFEST.json",
    ):
        print(f"  {rel}")
    return 0


def _ensure_payload(args: argparse.Namespace) -> Path:
    dirs = _dirs(args.root)
    if getattr(args, "from_zip", None):
        extract_payload_zip(Path(args.from_zip), dirs["payload"])
        print(f"Using payload zip {args.from_zip}")
        return dirs["payload"]
    if payload_is_ready(dirs["payload"]) and not args.force:
        return dirs["payload"]
    for command in (cmd_discover, cmd_fetch, cmd_assemble):
        code = command(args)
        if code:
            raise SystemExit(code)
    return dirs["payload"]


def _artifacts_for_payload(dirs: dict[str, Path]) -> dict[str, Artifact]:
    if dirs["catalog"].is_file():
        return _load_catalog(dirs["catalog"])
    manifest_path = dirs["payload"] / "MANIFEST.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {key: Artifact(**value) for key, value in data["artifacts"].items()}


def cmd_package(args: argparse.Namespace) -> int:
    dirs = _dirs(args.root)
    payload = _ensure_payload(args)
    artifacts = _artifacts_for_payload(dirs)
    zip_path = package_payload(payload, dirs["dist"], artifacts["koreader"], artifacts["nickelmenu"])
    print(f"Distributable: {zip_path}")
    print(f"Checksum:      {zip_path.name}.sha256")
    print()
    print("Do not unzip this with Finder/Explorer and drag folders onto the Kobo.")
    print("Install with: kobo-sideload install --from-zip", zip_path)
    return 0


def _prompt_dict_langs() -> list[str]:
    print()
    for line in format_lang_prompt():
        print(line)
    hint = lang_choice_hint()
    try:
        answer = input(f"Choose dictionaries [{hint}] ").strip()
    except EOFError:
        answer = "skip"
    if not answer:
        return []
    try:
        return parse_langs(answer)
    except ValueError as exc:
        print(f"{exc}; skipping dictionaries.")
        return []


def _resolve_dict_langs(args: argparse.Namespace) -> list[str]:
    explicit = getattr(args, "dicts", None)
    if explicit is not None:
        return parse_langs(explicit)
    if args.yes or not sys.stdin.isatty():
        return []
    return _prompt_dict_langs()


def _install_dicts_onto(volume, langs: list[str], cache_dir: Path, *, force: bool = False) -> int:
    if not langs:
        return 0
    koreader = volume.mountpoint / ".adds" / "koreader"
    if not (koreader / "koreader.sh").is_file():
        raise RuntimeError("KOReader is not installed on this Kobo. Run `kobo-sideload install` first.")
    dest = ensure_dictionaries_folder(volume)
    ensure_stardict_lua(koreader)
    specs = specs_for_langs(langs)
    print()
    print(f"Downloading {len(specs)} dictionary archive(s) onto {dest}...")
    for spec in specs:
        print(f"  {spec.key}: {spec.name} ({spec.license})")
    installed = install_specs(specs, dest, cache_dir, force=force)
    for path in installed:
        print(f"    -> {path.name}")
    if hasattr(os, "sync"):
        os.sync()
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    payload = _ensure_payload(args)
    volume = find_kobo()
    print(f"Kobo mount: {volume.mountpoint}")
    print("Plan:")
    for line in plan_install(payload, volume):
        print(f"  {line}")
    if args.dry_run:
        print("Dry run; nothing written.")
        return 0
    if not args.yes:
        answer = input("Write these files to the Kobo? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Aborted.")
            return 1
    install_payload(payload, volume)
    missing = verify_install(volume)
    if missing:
        print("Install wrote files but verification failed:")
        for path in missing:
            print(f"  missing: {path}")
        return 1
    print()
    print("Install complete.")
    dict_ok = True
    try:
        langs = _resolve_dict_langs(args)
        _install_dicts_onto(volume, langs, _dirs(args.root)["cache"], force=args.force)
    except Exception as exc:  # noqa: BLE001
        dict_ok = False
        print(
            f"Dictionary download failed ({exc}). "
            "KOReader is installed; try `kobo-sideload dictionaries --lang en,ru` "
            "or download in KOReader over Wi-Fi."
        )
    if args.yes:
        should_eject = True
    else:
        answer = input("Eject the Kobo now so it can install NickelMenu? [Y/n] ").strip().lower()
        should_eject = answer in {"", "y", "yes"}
    if should_eject:
        try:
            eject_kobo(volume)
            print("Ejected. Leave the cable until it reboots (it looks like a firmware update).")
        except Exception as exc:  # noqa: BLE001
            print(f"Could not eject automatically ({exc}). Eject KOBOeReader from Finder yourself.")
    else:
        print("Eject KOBOeReader from Finder when you are ready.")
    print("Then open NickelMenu on the Home screen and tap KOReader.")
    return 0 if dict_ok else 1


def cmd_dictionaries(args: argparse.Namespace) -> int:
    volume = find_kobo()
    print(f"Kobo mount: {volume.mountpoint}")
    if args.lang is not None:
        langs = parse_langs(args.lang)
    elif args.yes:
        raise RuntimeError("pass --lang with a list number, a language code, or all")
    else:
        langs = _prompt_dict_langs()
    if not langs:
        print("No dictionaries selected.")
        print(f"Folder: {dictionaries_dir(volume)}")
        print("In KOReader: Search → Dictionary settings → Download dictionaries (needs Wi-Fi).")
        return 0
    if args.dry_run:
        for spec in specs_for_langs(langs):
            print(f"  would fetch {spec.key}: {spec.url}")
        return 0
    _install_dicts_onto(volume, langs, _dirs(args.root)["cache"], force=args.force)
    print("Long-press a word in a book to look it up.")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    volume = find_kobo()
    print(f"Kobo mount: {volume.mountpoint}")
    missing = verify_install(volume)
    if missing:
        print("Sideload is incomplete:")
        for path in missing:
            print(f"  missing: {path}")
        return 1
    print("KOReader + NickelMenu files are present.")
    manifest = volume.mountpoint / ".adds" / "kobo-sideload-manifest.json"
    if manifest.is_file():
        print(manifest.read_text(encoding="utf-8"))
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    args.force = True
    return cmd_package(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kobo-sideload",
        description=(
            "Install current KOReader on a USB-mounted Kobo. Downloads KOReader and "
            "NickelMenu from GitHub. Does not use one-click zips, KFMon, or Plato."
        ),
        epilog="Typical use: plug in the Kobo, then run `kobo-sideload install`.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="cache directory (default: platform cache dir, or $KOBO_SIDELOAD_HOME)",
    )
    parser.add_argument(
        "--firmware",
        choices=("4", "5"),
        default="4",
        help="Kobo firmware family. 4.x devices including Libra Colour use 4.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("discover", help="resolve latest GitHub release URLs")

    fetch_p = sub.add_parser("fetch", help="download those artifacts")
    fetch_p.add_argument("--force", action="store_true", help="re-download even if cached")

    sub.add_parser("assemble", help="build a device-shaped tree in the cache")

    package_p = sub.add_parser("package", help="zip the payload for GitHub Releases")
    package_p.add_argument("--force", action="store_true", help="rebuild the payload first")
    package_p.add_argument("--from-zip", type=Path, help="repackage an existing payload zip")

    install_p = sub.add_parser("install", help="copy onto a mounted Kobo (fetches if needed)")
    install_p.add_argument("--yes", action="store_true", help="install without confirmation")
    install_p.add_argument("--dry-run", action="store_true", help="print install plan only")
    install_p.add_argument("--force", action="store_true", help="re-download and rebuild first")
    install_p.add_argument(
        "--from-zip",
        type=Path,
        help="install a payload zip from CI / GitHub Releases instead of fetching",
    )
    langs = ", ".join(available_langs()) or "none"
    install_p.add_argument(
        "--dicts",
        default=None,
        metavar="LANGS",
        help=(
            f"download dictionaries (menu number, {langs}, or all). "
            "--yes skips dictionaries unless this is set"
        ),
    )

    dict_p = sub.add_parser(
        "dictionaries",
        help="download StarDict files onto a mounted Kobo (not in the app zip)",
    )
    dict_p.add_argument(
        "--lang",
        default=None,
        metavar="LANGS",
        help=f"menu number, {langs}, or all. Prompted if omitted",
    )
    dict_p.add_argument("--force", action="store_true", help="re-download even if cached")
    dict_p.add_argument("--yes", action="store_true", help="do not prompt (requires --lang)")
    dict_p.add_argument("--dry-run", action="store_true", help="print URLs only")

    sub.add_parser("status", help="inspect a mounted Kobo")

    build_p = sub.add_parser("build", help="CI: discover + fetch + assemble + package")
    build_p.add_argument("--force", action="store_true", default=True, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.root = (args.root or default_home()).expanduser().resolve()
    args.force = getattr(args, "force", False)
    args.yes = getattr(args, "yes", False)
    args.dry_run = getattr(args, "dry_run", False)
    args.from_zip = getattr(args, "from_zip", None)
    args.dicts = getattr(args, "dicts", None)
    args.lang = getattr(args, "lang", None)
    commands = {
        "discover": cmd_discover,
        "fetch": cmd_fetch,
        "assemble": cmd_assemble,
        "package": cmd_package,
        "install": cmd_install,
        "dictionaries": cmd_dictionaries,
        "status": cmd_status,
        "build": cmd_build,
    }
    try:
        return commands[args.command](args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print(f"error: {exc}", file=sys.stderr)
        return 1


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
