"""Constants that describe the on-device layout and Nickel settings."""

from __future__ import annotations

NICKELMENU_CONFIG_NAME = "koreader"
NICKELMENU_CONFIG = (
    "# Launch KOReader without KFMon. Survives official firmware updates.\n"
    "menu_item:main:KOReader:cmd_spawn:quiet:exec "
    "/mnt/onboard/.adds/koreader/koreader.sh\n"
)

# Firmware 4.17+ indexes hidden folders. This regex tells Nickel to skip
# everything that starts with a dot except .kobo and .adobe.
EXCLUDE_SYNC_FOLDERS = r"(\\.(?!kobo|adobe).+|([^.][^/]*/)+\\..+)"
EXCLUDE_SYNC_SECTION = "FeatureSettings"
EXCLUDE_SYNC_KEY = "ExcludeSyncFolders"

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
