"""Constants that describe the on-device layout and Nickel settings."""

from __future__ import annotations

NICKELMENU_CONFIG_NAME = "koreader"
NICKELMENU_CONFIG = """\
# Firmware 4.23+ removed the old top-left main menu, so NickelMenu adds an
# extra bottom tab. Its default icon is Kobo's More glyph (a second hamburger).
# Label that tab KOReader so it is a launch affordance, not a duplicate More.
experimental:menu_main_15505_label:KOReader

# Same launch from the extra tab's menu, and from My Books overflow.
menu_item:main:KOReader:cmd_spawn:quiet:exec /mnt/onboard/.adds/koreader/koreader.sh
menu_item:library:KOReader:cmd_spawn:quiet:exec /mnt/onboard/.adds/koreader/koreader.sh

# Experiment: hide the extra tab. NickelMenu still intercepts a "Settings"
# item (StatusBarMenuController). If More still creates that item, KOReader
# appears inside More with no extra tab. If KOReader vanishes, comment this
# out and reboot.
# experimental:menu_main_15505_enabled:0
"""

# Firmware 4.17+ indexes hidden folders. Skip those (except .kobo/.adobe)
# and the visible sideload library so Nickel does not ingest FB2/etc.
BOOKS_FOLDER = "KOReader"
EXCLUDE_SYNC_FOLDERS = (
    r"((KOReader)|\\.(?!kobo|adobe).+|([^.][^/]*/)+\\..+)"
)
EXCLUDE_SYNC_SECTION = "FeatureSettings"
EXCLUDE_SYNC_KEY = "ExcludeSyncFolders"

BOOKS_README_NAME = "README.txt"
BOOKS_README = """Sideload library for KOReader
=============================

Put .fb2, .fb2.zip, EPUB, PDF, and other files here. Subfolders are fine.

Nickel (Kobo's own library) ignores this folder, so store-bought books
stay in My Books. These files only show up in KOReader.

In KOReader: open this folder, long-press it, choose Set as HOME directory.

Do not put books in .adds/koreader/ — that is the application, and an
update can replace it.
"""

KOBO_VOLUME_LABEL = "KOBOeReader"
KOBO_CONF_REL = ("Kobo", "Kobo eReader.conf")

USER_AGENT = "kobo-sideload/0.1 (+https://github.com/manwithacat/kobo-sideload)"

DICT_FOLDER = ".adds/dictionaries"
STARDICT_DATA_DIR = "/mnt/onboard/.adds/dictionaries"
STARDICT_LUA_MARKER = "-- kobo-sideload dictionaries"
# KOReader dofile()s this file and uses the returned table (see luadefaults.lua).
# A bare assignment after `return {}` is dead code and is ignored.
STARDICT_LUA_ASSIGN = f'["STARDICT_DATA_DIR"] = "{STARDICT_DATA_DIR}"'
STARDICT_LUA_LINE = STARDICT_LUA_ASSIGN
DICT_README = """StarDict dictionaries for KOReader
==================================

Long-press a word in a book to look it up.

This folder is outside the KOReader app tree so reinstalling the app
does not delete dictionaries.

You can also download dictionaries on the device:
  KOReader → Search (magnifying glass) → Dictionary settings
           → Download dictionaries
  (needs Wi-Fi; the Kobo cannot download while it is plugged in over USB)

Sources used by `kobo-sideload dictionaries` are the same tar.gz files
KOReader itself offers. See NOTICE.md for licences.
"""

KOREADER_REPO = ("koreader", "koreader")
NICKELMENU_REPO = ("pgaskin", "NickelMenu")

# Official KOReader ships two Kobo zips: firmware 4.x (`kobo`) and 5.x (`kobov5`).
KOREADER_ASSET = {
    "4": "koreader-kobo-{tag}.zip",
    "5": "koreader-kobov5-{tag}.zip",
}
