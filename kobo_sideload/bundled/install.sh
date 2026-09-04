#!/usr/bin/env bash
# Copy this release onto a USB-mounted Kobo. No Python required.
set -euo pipefail

HERE="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)"
LABEL="KOBOeReader"
EXCLUDE_LINE='ExcludeSyncFolders=(\\.(?!kobo|adobe).+|([^.][^/]*/)+\\..+)'

die() {
	echo "error: $*" >&2
	exit 1
}

need() {
	[[ -e "$1" ]] || die "This folder is not a complete release (missing $1). Unzip the whole archive first."
}

need "$HERE/.adds/koreader/koreader.sh"
need "$HERE/.adds/nm/koreader"
need "$HERE/.kobo/KoboRoot.tgz"

find_kobo() {
	local mount=""
	case "$(uname -s)" in
		Darwin)
			if command -v plutil >/dev/null 2>&1; then
				mount="$(diskutil info -plist "$LABEL" 2>/dev/null | plutil -extract MountPoint raw - 2>/dev/null || true)"
			fi
			if [[ -z "$mount" ]]; then
				mount="$(diskutil info -plist "$LABEL" 2>/dev/null | awk -F'[<>]' '/<key>MountPoint<\/key>/{getline; print $3}')"
			fi
			;;
		Linux)
			if command -v findmnt >/dev/null 2>&1; then
				mount="$(findmnt -nlo TARGET "LABEL=$LABEL" 2>/dev/null | head -n 1 || true)"
			fi
			;;
		*)
			die "Unsupported OS $(uname -s). On Windows run install.ps1 instead."
			;;
	esac
	[[ -n "$mount" ]] || die "No Kobo volume is mounted. Plug it in, unlock it, and wait for \"$LABEL\"."
	[[ -d "$mount/.kobo" ]] || die "$mount has no .kobo directory, so it is not a Kobo in USB mode."
	printf '%s' "$mount"
}

copy_tree() {
	mkdir -p "$2"
	if command -v rsync >/dev/null 2>&1; then
		rsync -a "$1/" "$2/"
	else
		cp -R "$1/." "$2/"
	fi
}

ensure_exclude() {
	local conf="$1"
	mkdir -p "$(dirname "$conf")"
	if [[ -f "$conf" ]] && grep -Fq "$EXCLUDE_LINE" "$conf"; then
		return 0
	fi
	{
		printf '\n[FeatureSettings]\n'
		printf '%s\n' "$EXCLUDE_LINE"
	} >>"$conf"
}

KOBO="$(find_kobo)"
echo "Kobo mount: $KOBO"
echo "Copying KOReader..."
copy_tree "$HERE/.adds/koreader" "$KOBO/.adds/koreader"
mkdir -p "$KOBO/.adds/nm"
cp "$HERE/.adds/nm/koreader" "$KOBO/.adds/nm/koreader"
cp "$HERE/.kobo/KoboRoot.tgz" "$KOBO/.kobo/KoboRoot.tgz"
if [[ -f "$HERE/MANIFEST.json" ]]; then
	cp "$HERE/MANIFEST.json" "$KOBO/.adds/kobo-sideload-manifest.json"
fi
ensure_exclude "$KOBO/.kobo/Kobo/Kobo eReader.conf"
sync 2>/dev/null || true

[[ -f "$KOBO/.adds/koreader/koreader.sh" ]] || die "Copy failed: koreader.sh missing on device."
[[ -f "$KOBO/.kobo/KoboRoot.tgz" ]] || die "Copy failed: KoboRoot.tgz missing on device."

echo
echo "Install complete."
echo "Eject the Kobo safely and wait for it to reboot (it looks like a firmware update)."
echo "Then open NickelMenu on the Home screen and tap KOReader."
