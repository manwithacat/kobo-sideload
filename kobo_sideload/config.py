"""Constants that describe the on-device layout and Nickel settings."""

from __future__ import annotations

NICKELMENU_CONFIG_NAME = "koreader"
NICKELMENU_CONFIG = (
    "# Launch KOReader without KFMon. Survives official firmware updates.\n"
    "menu_item:main:KOReader:cmd_spawn:quiet:exec "
    "/mnt/onboard/.adds/koreader/koreader.sh\n"
)

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

KOREADER_REPO = ("koreader", "koreader")
NICKELMENU_REPO = ("pgaskin", "NickelMenu")

# Official KOReader ships two Kobo zips: firmware 4.x (`kobo`) and 5.x (`kobov5`).
KOREADER_ASSET = {
    "4": "koreader-kobo-{tag}.zip",
    "5": "koreader-kobov5-{tag}.zip",
}
