# kobo-sideload

KOReader on a Kobo, assembled automatically from GitHub releases.

No MobileRead one-click zip. No KFMon. No Plato. No Python on your computer unless you want it.

## Install (this is the whole user path)

1. Plug the Kobo in over USB. Stay on the Home screen. Wait for a drive named **KOBOeReader**.
2. Download the zip from **[the latest release](https://github.com/manwithacat/kobo-sideload/releases/latest)**.
3. Unzip it **on your computer** (not onto the Kobo).
4. Run the installer that came in the zip:

   | Computer | What to run |
   | --- | --- |
   | macOS | Open Terminal, type `bash ` (with a space), drag `install.sh` onto the window, press Return. Do **not** double-click a `.command` file — Gatekeeper blocks unsigned downloads and Right-click → Open often cannot override it. |
   | Windows | Right-click `install.ps1` → Run with PowerShell |
   | Linux | `bash install.sh` |

5. Optional: when asked, type a language code (**en**, **ru**, …), comma-separated codes, or **all** to download dictionaries (the computer fetches them; USB mode has no Wi-Fi). Skip and download later in KOReader: **Search → Dictionary settings → Download dictionaries**.
6. When the installer asks to eject, say yes. The Kobo reboots as if applying an update — that is NickelMenu installing.
7. Open **NickelMenu** on the Home screen and tap **KOReader**. Long-press a word to look it up.

Sideloads go in the **`KOReader/`** folder the installer creates on the USB volume. Nickel is configured to ignore it, so store books stay in My Books. In KOReader, open that folder and long-press → **Set as HOME directory**. Drop `.fb2` / `.fb2.zip` there over USB; do not put books in `.adds/koreader/`.

Firmware **4.6–4.x** (Libra Colour 4.45 included). Firmware **5.x** is not supported yet (NickelMenu does not load).

The extra bottom-nav tab is NickelMenu (firmware 4.23 removed the old top-left menu). We label it **KOReader** instead of a second hamburger. There is also a KOReader item in **My Books**. Putting it inside stock **More** is not a NickelMenu config option; `.adds/nm/koreader` has a commented experiment to hide the extra tab in case More still receives the Settings hook.

## What GitHub Actions builds

Every week, and on every push to `main`, [`.github/workflows/build.yml`](.github/workflows/build.yml):

1. Asks GitHub for the current `koreader-kobo-*.zip` and NickelMenu `KoboRoot.tgz`
2. Verifies SHA-256
3. Writes the NickelMenu launch line **enabled** (the old one-click zip leaves it commented)
4. Sets `ExcludeSyncFolders` instructions into the bundled installer
5. Publishes a **versioned** GitHub Release, e.g. `koreader-v2026.07.1-nickelmenu-v0.6.0`, and marks it as **latest**

If those two upstream versions have not changed, the workflow does not duplicate the release. When KOReader or NickelMenu ships, the next run publishes a new tag. [Releases](https://github.com/manwithacat/kobo-sideload/releases/latest) stay current without anyone rebuilding a zip by hand.

Each zip contains:

| Path | Role |
| --- | --- |
| `.adds/koreader/` | KOReader |
| `.adds/nm/koreader` | NickelMenu item that runs `koreader.sh` |
| `.kobo/KoboRoot.tgz` | NickelMenu plugin (applied on eject) |
| `KOReader/` | Sideload library (FB2 etc.). Nickel is told not to index it. Reinstalls do not wipe books already there. |
| `install.sh` / `install.ps1` | Copies the hidden folders onto the Kobo (`bash install.sh` on Mac/Linux — not a double-click). Merges `.adds/koreader/` so settings and dictionaries survive a reinstall. |
| `dictionaries.tsv` | Optional StarDict catalog (URLs only). Language PRs add a row here. |
| `READ ME FIRST.txt` | The same steps as above |

Dictionaries are **not** in the zip (size and licences). The installer creates `.adds/dictionaries/` and points KOReader at it with `defaults.custom.lua`. Reinstalls merge the app tree and leave that folder alone.

Do not drag `.adds` onto the reader in Finder or Explorer. That is how silent failures happen.

## Optional: run the pipeline yourself

Python 3.9+, no third-party packages:

```text
pipx install git+https://github.com/manwithacat/kobo-sideload
kobo-sideload install          # fetch current GitHub assets onto a mounted Kobo
kobo-sideload install --dicts en,ru   # same, and fetch English+Russian StarDict files
kobo-sideload dictionaries --lang en,ru
kobo-sideload build            # produce the same zip CI publishes
# zip installer, non-interactive: KOBO_SIDELOAD_DICTS=en,ru bash install.sh
```

Tests: `python3 -m unittest discover -s tests -v`

## Why this exists

The MobileRead OCP zip is a human-rebuilt merge of KFMon + NickelMenu + KOReader + Plato, hosted on an OVH bucket, installed by 2019 `install.command` / `.sh` / `.ps1` scripts. It lags GitHub (OCP was still KOReader v2026.03 when GitHub was on v2026.07.1) and ships the NickelMenu launch line commented out.

This repo treats GitHub as the source of truth and Actions as the packager. Details: [COMPONENTS.md](COMPONENTS.md). Libra Colour / Russian FB2 notes: [STRATEGY.md](STRATEGY.md). Upstream licenses: [NOTICE.md](NOTICE.md). Add a dictionary language: [CONTRIBUTING.md](CONTRIBUTING.md).
