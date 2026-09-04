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

5. Eject the Kobo. It reboots as if applying an update — that is NickelMenu installing.
6. Open **NickelMenu** on the Home screen and tap **KOReader**.

Put FB2 (and other) books in any normal folder. Open them from KOReader, not from Kobo’s library.

Firmware **4.6–4.x** (Libra Colour 4.45 included). Firmware **5.x** is not supported yet (NickelMenu does not load).

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
| `install.sh` / `install.ps1` | Copies the hidden folders onto the Kobo (`bash install.sh` on Mac/Linux — not a double-click) |
| `READ ME FIRST.txt` | The same steps as above |

Do not drag `.adds` onto the reader in Finder or Explorer. That is how silent failures happen.

## Optional: run the pipeline yourself

Python 3.9+, no third-party packages:

```text
pipx install git+https://github.com/manwithacat/kobo-sideload
kobo-sideload install          # fetch current GitHub assets onto a mounted Kobo
kobo-sideload build            # produce the same zip CI publishes
```

Tests: `python3 -m unittest discover -s tests -v`

## Why this exists

The MobileRead OCP zip is a human-rebuilt merge of KFMon + NickelMenu + KOReader + Plato, hosted on an OVH bucket, installed by 2019 `install.command` / `.sh` / `.ps1` scripts. It lags GitHub (OCP was still KOReader v2026.03 when GitHub was on v2026.07.1) and ships the NickelMenu launch line commented out.

This repo treats GitHub as the source of truth and Actions as the packager. Details: [COMPONENTS.md](COMPONENTS.md). Libra Colour / Russian FB2 notes: [STRATEGY.md](STRATEGY.md). Upstream licenses: [NOTICE.md](NOTICE.md).
