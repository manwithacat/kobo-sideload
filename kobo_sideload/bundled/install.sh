#!/usr/bin/env bash
# Copy this release onto a USB-mounted Kobo. No Python required.
set -euo pipefail

HERE="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)"
LABEL="KOBOeReader"
EXCLUDE_LINE='ExcludeSyncFolders=((KOReader)|\\.(?!kobo|adobe).+|([^.][^/]*/)+\\..+)'
STARDICT_MARKER='-- kobo-sideload dictionaries'
STARDICT_LINE='STARDICT_DATA_DIR = "/mnt/onboard/.adds/dictionaries"'
CATALOG_FILE="$HERE/dictionaries.tsv"

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
	local tmp
	mkdir -p "$(dirname "$conf")"
	touch "$conf"
	if grep -Fq "$EXCLUDE_LINE" "$conf"; then
		return 0
	fi
	if grep -q '^ExcludeSyncFolders=' "$conf"; then
		tmp="$(mktemp)"
		EXCLUDE_LINE="$EXCLUDE_LINE" awk '
			!done && /^ExcludeSyncFolders=/ { print ENVIRON["EXCLUDE_LINE"]; done=1; next }
			{ print }
		' "$conf" >"$tmp" && mv "$tmp" "$conf"
		return 0
	fi
	{
		printf '\n[FeatureSettings]\n'
		printf '%s\n' "$EXCLUDE_LINE"
	} >>"$conf"
}

eject_kobo() {
	local mount="$1"
	case "$(uname -s)" in
		Darwin)
			diskutil eject "$mount" || return 1
			;;
		Linux)
			local src=""
			src="$(findmnt -nlo SOURCE "$mount" 2>/dev/null || true)"
			if [[ -n "$src" ]] && command -v udisksctl >/dev/null 2>&1; then
				udisksctl unmount -b "$src" || umount "$mount" || return 1
			else
				umount "$mount" || return 1
			fi
			;;
		*)
			return 1
			;;
	esac
	return 0
}

dict_cache_dir() {
	if [[ -n "${KOBO_SIDELOAD_HOME:-}" ]]; then
		printf '%s' "$KOBO_SIDELOAD_HOME/cache"
	elif [[ "$(uname -s)" == Darwin ]]; then
		printf '%s' "$HOME/Library/Caches/kobo-sideload/cache"
	else
		printf '%s' "${XDG_CACHE_HOME:-$HOME/.cache}/kobo-sideload/cache"
	fi
}

ensure_stardict_lua() {
	local lua="$1"
	mkdir -p "$(dirname "$lua")"
	if [[ -f "$lua" ]] && grep -Fq "$STARDICT_MARKER" "$lua"; then
		return 0
	fi
	if [[ -s "$lua" ]]; then
		printf '\n%s\n%s\n' "$STARDICT_MARKER" "$STARDICT_LINE" >>"$lua"
	else
		printf '%s\n%s\n' "$STARDICT_MARKER" "$STARDICT_LINE" >"$lua"
	fi
}

ensure_dictionaries_folder() {
	local dest="$1"
	mkdir -p "$dest"
	cat >"$dest/README.txt" <<'EOF'
StarDict dictionaries for KOReader
==================================

Long-press a word in a book to look it up.

This folder is outside the KOReader app tree so reinstalling the app
does not delete dictionaries.

You can also download dictionaries on the device:
  KOReader → Search (magnifying glass) → Dictionary settings
           → Download dictionaries
  (needs Wi-Fi; the Kobo cannot download while it is plugged in over USB)
EOF
}

migrate_legacy_dicts() {
	local old="$1/data/dict"
	local dest="$2"
	[[ -d "$old" ]] || return 0
	local item base
	for item in "$old"/*; do
		[[ -e "$item" ]] || continue
		base="$(basename "$item")"
		if [[ ! -e "$dest/$base" ]]; then
			cp -R "$item" "$dest/$base"
		fi
	done
}

download_file() {
	local url="$1"
	local dest="$2"
	if [[ -f "$dest" ]]; then
		return 0
	fi
	mkdir -p "$(dirname "$dest")"
	if command -v curl >/dev/null 2>&1; then
		curl -L --fail --retry 3 --connect-timeout 30 -o "$dest.partial" "$url" || return 1
		mv "$dest.partial" "$dest"
	elif command -v wget >/dev/null 2>&1; then
		wget -O "$dest.partial" "$url" || return 1
		mv "$dest.partial" "$dest"
	else
		echo "Need curl or wget to download dictionaries." >&2
		return 1
	fi
}

unpack_stardict() {
	local archive="$1"
	local dest="$2"
	local scratch found ifo stem srcdir f
	scratch="$(mktemp -d "${TMPDIR:-/tmp}/kobo-dict.XXXXXX")"
	tar -xzf "$archive" -C "$scratch" || { rm -rf "$scratch"; return 1; }
	found=0
	while IFS= read -r -d '' ifo; do
		stem="$(basename "$ifo" .ifo)"
		srcdir="$(dirname "$ifo")"
		mkdir -p "$dest/$stem"
		for f in "$srcdir"/*; do
			if [[ -f "$f" ]]; then
				cp "$f" "$dest/$stem/"
			elif [[ -d "$f" && "$(basename "$f")" == res ]]; then
				mkdir -p "$dest/$stem/res"
				cp -R "$f/." "$dest/$stem/res/"
			fi
		done
		found=1
	done < <(find "$scratch" -name '*.ifo' -print0)
	rm -rf "$scratch"
	if [[ "$found" -eq 0 ]]; then
		echo "$archive contained no StarDict .ifo files" >&2
		return 1
	fi
}

install_one_dict() {
	local url="$1"
	local filename="$2"
	local dest="$3"
	local cache="$4"
	echo "  $filename"
	download_file "$url" "$cache/$filename" || return 1
	unpack_stardict "$cache/$filename" "$dest" || return 1
}

catalog_langs() {
	[[ -f "$CATALOG_FILE" ]] || return 0
	awk -F'\t' 'NF>=7 && $1 !~ /^#/ {
		n=split($2, a, ",")
		for (i=1;i<=n;i++) {
			gsub(/ /, "", a[i])
			if (a[i] != "" && !seen[a[i]]++) {
				if (out != "") out = out "," a[i]
				else out = a[i]
			}
		}
	}
	END { print out }' "$CATALOG_FILE"
}

print_catalog_prompt() {
	echo "Dictionaries are optional (not in this zip). Long-press a word in KOReader to look it up." >&2
	echo "  skip   none now — download later in KOReader over Wi-Fi" >&2
	if [[ -f "$CATALOG_FILE" ]]; then
		awk -F'\t' 'NF>=7 && $1 !~ /^#/ {
			n=split($2, a, ",")
			for (i=1;i<=n;i++) {
				gsub(/ /, "", a[i])
				if (a[i] != "" && !seen[a[i]]++) printf "  %-6s %s\n", a[i], $3
			}
		}' "$CATALOG_FILE" >&2
		echo "  all    every listed language" >&2
	fi
}

normalize_dict_langs() {
	local raw known wanted part
	raw="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -d ' ')"
	case "$raw" in
		""|skip|none|no|n) printf ''; return 0 ;;
		both|all) catalog_langs; return 0 ;;
	esac
	known=",$(catalog_langs),"
	wanted=""
	IFS=',' read -ra parts <<<"$raw"
	for part in "${parts[@]}"; do
		[[ -n "$part" ]] || continue
		case "$known" in
			*",$part,"*)
				case ",$wanted," in
					*",$part,"*) ;;
					*) wanted="${wanted:+$wanted,}$part" ;;
				esac
				;;
			*)
				echo "unknown dictionary choice: $part (use skip, language codes, or all); skipping." >&2
				printf ''
				return 0
				;;
		esac
	done
	printf '%s' "$wanted"
}

choose_dict_langs() {
	local raw hint
	if [[ -n "${KOBO_SIDELOAD_DICTS:-}" ]]; then
		normalize_dict_langs "$KOBO_SIDELOAD_DICTS"
		return 0
	fi
	if [[ ! -t 0 ]]; then
		hint="$(catalog_langs)"
		echo "No terminal for a dictionary prompt; skipping. Later: KOBO_SIDELOAD_DICTS=${hint:-all} bash install.sh" >&2
		printf ''
		return 0
	fi
	echo >&2
	print_catalog_prompt
	hint="$(catalog_langs)"
	if [[ -n "$hint" ]]; then
		hint="skip/${hint}/all"
	else
		hint="skip"
	fi
	read -r -p "Download dictionaries now? [$hint] " raw || raw="skip"
	normalize_dict_langs "${raw:-skip}"
}

install_dicts() {
	local langs="$1"
	local dest="$2"
	local cache key spec_langs label name license filename url want lang
	[[ -n "$langs" ]] || return 0
	if [[ ! -f "$CATALOG_FILE" ]]; then
		echo "No dictionaries.tsv next to install.sh; skipping dictionary download." >&2
		return 1
	fi
	cache="$(dict_cache_dir)"
	mkdir -p "$cache" "$dest"
	echo
	echo "Downloading dictionaries onto $dest ..."
	while IFS=$'\t' read -r key spec_langs label name license filename url; do
		[[ -n "$key" ]] || continue
		want=0
		IFS=',' read -ra spec_lang_arr <<<"$spec_langs"
		for lang in "${spec_lang_arr[@]}"; do
			lang="${lang// /}"
			case ",$langs," in
				*",$lang,"*) want=1 ;;
			esac
		done
		if [[ "$want" -eq 1 ]]; then
			install_one_dict "$url" "$filename" "$dest" "$cache" || return 1
		fi
	done < <(awk -F'\t' 'NF>=7 && $1 !~ /^#/ { print }' "$CATALOG_FILE")
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
mkdir -p "$KOBO/KOReader"
if [[ -f "$HERE/KOReader/README.txt" ]]; then
	cp "$HERE/KOReader/README.txt" "$KOBO/KOReader/README.txt"
fi
ensure_dictionaries_folder "$KOBO/.adds/dictionaries"
migrate_legacy_dicts "$KOBO/.adds/koreader" "$KOBO/.adds/dictionaries"
ensure_stardict_lua "$KOBO/.adds/koreader/defaults.custom.lua"
ensure_exclude "$KOBO/.kobo/Kobo/Kobo eReader.conf"
sync 2>/dev/null || true

[[ -f "$KOBO/.adds/koreader/koreader.sh" ]] || die "Copy failed: koreader.sh missing on device."
[[ -f "$KOBO/.kobo/KoboRoot.tgz" ]] || die "Copy failed: KoboRoot.tgz missing on device."
[[ -f "$KOBO/.adds/koreader/defaults.custom.lua" ]] || die "Copy failed: defaults.custom.lua missing on device."

echo
echo "Install complete."
echo "Put FB2 and other sideloads in the KOReader folder on the USB volume."
DICT_STATUS=0
DICT_LANGS="$(choose_dict_langs)"
if ! install_dicts "$DICT_LANGS" "$KOBO/.adds/dictionaries"; then
	echo "Dictionary download failed. KOReader is installed; download later in KOReader over Wi-Fi."
	DICT_STATUS=1
fi
sync 2>/dev/null || true
echo
if [[ -t 0 ]]; then
	read -r -p "Eject the Kobo now so it can install NickelMenu? [Y/n] " ans || ans="n"
else
	echo "No terminal for a prompt; eject KOBOeReader yourself."
	ans="n"
fi
ans="${ans:-Y}"
case "$ans" in
	Y|y|yes|YES)
		if eject_kobo "$KOBO"; then
			echo "Ejected. Leave the cable until it reboots (it looks like a firmware update)."
		else
			echo "Could not eject automatically. Eject KOBOeReader from Finder yourself."
		fi
		;;
	*)
		echo "Eject KOBOeReader from Finder when you are ready."
		;;
esac
echo "Then open NickelMenu on the Home screen and tap KOReader."
exit "$DICT_STATUS"
