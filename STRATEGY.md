# Kobo Libra Colour: one path to KOReader for Russian FB2

Device in scope: **Kobo Libra Colour (N428)**, firmware **4.45.23697**.
Goal: read **FB2** (especially Russian / windows-1251) without mixing decade-old launcher recipes.

This is a single recommended path, not a catalog of every method that has ever worked.

## The mental model (what the forums mix up)

Nickel is Kobo’s stock UI. You keep it. KOReader is a second reader that lives in a hidden folder. Nickel cannot start KOReader by itself, so you also need a **launcher**.

| Piece | What it is | Need it? |
| --- | --- | --- |
| **Nickel** | Stock Kobo UI and bookstore | Yes. Leave it. |
| **KOReader** | The reader that actually handles FB2 + Cyrillic well | Yes. This is the goal. |
| **NickelMenu** | Injects a “NickelMenu” item into Nickel. Can run `koreader.sh` directly. Survives official firmware updates. | **Yes — primary launcher.** |
| **KFMon** | Daemon that treats `koreader.png` as a fake book and launches KOReader when you open it. Official firmware updates disable it. | Optional extra. OCP bundles it. |
| **Plato** | A *different* third-party reader | **No** for FB2/Russian. |
| **fmon** | Older File Monitor KFMon replaced | **No.** Mutually exclusive with KFMon. |
| **KSM** (Kobo Start Menu) | Deprecated boot menu. Always wins over KFMon/NickelMenu. | **No** on Clara-or-newer / FW 4.25+. |

“nm” is just NickelMenu’s config folder: `.adds/nm/`.

## Why KOReader (not stock Kobo) for Russian FB2

Kobo’s official format list is EPUB/PDF/MOBI/TXT/HTML/RTF/CBZ/CBR — not FB2. Firmware has historically contained an unofficial Nickel FB2 XSLT path; it is slow, crash-prone, and poorly styled compared with EPUB.

KOReader treats `.fb2`, `.fb2.zip`, and `.fb3` as first-class CREngine formats. It decodes the encodings Russian FB2 files actually use (UTF-8, windows-1251/cp1251, koi8-r, cp866), ships Russian hyphenation patterns, and uses Noto as the default CRE faces. Charis is the usual extra recommendation for Latin+Cyrillic.

There is no Russia-specific or FB2-specific installer. Install KOReader once; open the FB2 from KOReader’s file browser.

## Recommended path for this device

**Install KOReader v2026.03 via NiLuJe’s One-Click Package, then make NickelMenu the launcher you actually use.**

Do **not** also install Plato. Do **not** follow KSM, fmon, “Ghost”, or YouTube mixed-installer videos.

Current official OCP zip (as of 2026-06-07):

- [OCP-KOReader-v2026.03.zip](https://storage.gra.cloud.ovh.net/v1/AUTH_2ac4bfee353948ec8ea7fd1710574097/kfmon-pub/OCP-KOReader-v2026.03.zip)
- Sticky: <https://www.mobileread.com/forums/showthread.php?t=314220>
- Wiki: <https://github.com/koreader/koreader/wiki/Installation-on-Kobo-devices>

That zip unpacks four things at the USB root:

1. `.adds/koreader/` — the app
2. `.kobo/KoboRoot.tgz` — KFMon + NickelMenu (applied on next reboot)
3. `koreader.png` and `kfmon.png` — KFMon’s fake-book icons
4. `.adds/nm/` — NickelMenu config (KOReader launch lines are **commented out**; KFMon’s generator is supposed to fill them in)

Then immediately uncomment NickelMenu’s direct launch line so KOReader still starts after the next Kobo firmware update.

### Install steps (macOS)

Safari will auto-unzip downloads. That is the #1 failure on Mac. Keep the original `.zip`.

1. Reboot the Libra Colour fully. Connect USB from the **Home** screen. Do not open a book first.
2. Put these in the **same folder** (this repo is fine):
   - `OCP-KOReader-v2026.03.zip` (the zip, not an extracted folder)
   - `install.command` (already here)
3. Run `install.command` (Right-click → Open → Open). Pick the KOReader zip. The script:
   - finds the volume labeled `KOBOeReader`
   - writes `ExcludeSyncFolders` so Nickel ignores `.adds`
   - unzips to the device root
   - checks that `.kobo/KoboRoot.tgz` and `kfmon.png` landed
4. Eject safely. The device should “process a book”, then reboot as if installing an update. If it does **not** reboot, `KoboRoot.tgz` did not land in `.kobo/`.
5. After reboot, plug in again and edit `.adds/nm/koreader` so this line is **uncommented**:

   ```
   menu_item : main : KOReader : cmd_spawn : quiet : exec /mnt/onboard/.adds/koreader/koreader.sh
   ```

6. Eject. Open **NickelMenu** from the Home screen (bottom-right tabs on current firmware) and tap **KOReader**.

That NickelMenu line is the path that survives firmware updates. The `koreader.png` icon is a convenience, not the thing to depend on.

### After KOReader is running

Copy FB2 files anywhere except `.adds` / `.kobo` (a folder such as `books/ru/` is fine). Open them from KOReader’s file manager, not from Nickel’s library.

In a Russian FB2:

- Font: Noto Serif is the default; add Charis or a C-Cyrillic face under `fonts/` if a book’s CSS names something Nickel-ish.
- Hyphenation: KOReader already ships `Russian.pattern`. Set the document language to Russian if a book’s metadata is wrong.
- Encoding: leave auto. windows-1251 FB2 should just work.

## Firmware 4.45.x notes (Libra Colour)

- KOReader has a Libra Colour profile (`Kobo_monza`) since 2024.07. v2026.03 is current in the official OCP zip.
- KFMon is device-agnostic on Nickel ≥ 2.9. A MobileRead post from July 2026 shows KFMon **running** on Libra Colour **4.45.23697** (the same build you have). The complaint was a shutdown toast, not a failed launch.
- NickelMenu’s own docs only claim full testing through 4.31.19086, say it is safe to try on newer 4.x (failsafe uninstalls it), document a Libra Colour on 4.41.23145, and **do not support firmware 5.x**.
- One unanswered GitHub issue ([pgaskin/NickelMenu#229](https://github.com/pgaskin/NickelMenu/issues/229), May 2026) reports NickelMenu not appearing on Libra Colour **4.45.23684** after copying only `KoboRoot.tgz`. That is a real risk. Mitigation: install via OCP (KFMon + NickelMenu together), then enable the `cmd_spawn` line. If NickelMenu is missing after reboot, the `koreader.png` icon is the fallback — if that PNG is actually on the device.
- Kobo’s current sideload for N428 is **4.46.23836** (August 2026). Stay on 4.45 until KOReader launches once. Then you may update; after any official update, KFMon is dead until you reinstall `OCP-KFMon-*.zip`. NickelMenu + `cmd_spawn` should keep working.

Do not install firmware 5.x if you want these tools.

## Why the packages in this folder did not get you there

This directory already contains extracted OCP trees, not the zips `install.command` looks for (`OCP-KOReader-v*.zip`).

| Folder | What it is | Problem |
| --- | --- | --- |
| `OCP-KOReader-v2026/` | KOReader v2026.03 + KFMon + NickelMenu | **Missing `koreader.png` and `kfmon.png` at the zip root.** KFMon watches those files. Without them the icon path cannot start. |
| `OCP-Plato-0-2/` | Combined KOReader + Plato | Has the PNGs, but Plato is extra surface area you do not need. |
| `OCP-Plato-0/` | Plato only | Not the FB2 reader you want. |
| `KFMon-v1/` | KFMon-only | Incomplete (7 files). Use the official `OCP-KFMon-*.zip` after a firmware update, not this. |
| `install.command` | Correct macOS installer | It will print “No supported packages found” until the **.zip** is sitting next to it. |

Typical Mac failure chain:

1. Safari auto-extracts the zip and you copy folders by hand.
2. Finder hides `.adds` / `.kobo`, or you miss the root PNGs.
3. Nickel never sees `KoboRoot.tgz`, so it never reboots into an “update”.
4. NickelMenu’s KOReader lines stay commented, and KFMon’s generator never runs → nothing in the menu, nothing in the library.

Do not drag extracted folders onto the device. Re-download the zip and let `install.command` unpack it.

## What to skip (dead ends)

- **KSM** — mutually exclusive, deprecated for this hardware/firmware.
- **fmon / Sergey / Baskerville launcher recipes** — last one installed wins against KFMon.
- **Chinese KOReader wiki (last edited 2022)** — still tells people to drop `koreader` into `.kobo` and use KSM/fmon.
- **YouTube “Ghost” 2025 mixed installers** — comments report tap-does-nothing on 4.45.x; not the wiki/OCP path.
- **Installing Plato “because the OCP thread mentions it”** — it is a second reader, not a KOReader dependency.
- **NickelMenu-only `KoboRoot.tgz` as the first attempt on 4.45** — possible, but issue #229 is unresolved. Prefer OCP (both launchers) then `cmd_spawn`.

## Recovery

**Uninstall KOReader (leave Nickel):** delete `.adds/koreader`, `koreader.png`. NickelMenu uninstall: create `.adds/nm/uninstall` and reboot. KFMon uninstall: official `KFMon-Uninstaller.zip`.

**Firmware update broke launch:** KOReader files are usually still in `.adds/koreader`. Reinstall `OCP-KFMon-*.zip` *or* just restore the NickelMenu `cmd_spawn` line. Do not re-copy the whole KOReader tree unless it is gone.

**Device did not reboot after eject:** `KoboRoot.tgz` is not in `.kobo/`. Hidden-folder copy failed. Use the zip + script.

**Nickel is indexing garbage / “processing” forever:** `ExcludeSyncFolders` was not written. `install.command` does this; a hand copy often does not.

## Implementation in this repo

The consumer installer is `python3 -m kobo_sideload` (stdlib only, macOS/Linux/Windows). It downloads **KOReader v2026.07.1** (or whatever GitHub latest is) and **NickelMenu v0.6.0** directly, writes the `cmd_spawn` line uncommented, and never touches KFMon or Plato.

That exists because the official OCP zip is a human-rebuilt merge that currently ships KOReader **v2026.03** — four months behind GitHub — and because `install.command` / `install.sh` / `install.ps1` only unzip a file you already downloaded, on one OS each.

See [README.md](README.md) and [COMPONENTS.md](COMPONENTS.md).

## Community version of this guide

The 94-page OCP thread is the canonical package source, not a tutorial. A better public page is:

1. Mental model table (Nickel / KOReader / NickelMenu / KFMon / Plato).
2. One beginner path: OCP-KOReader zip + OS script + uncomment `cmd_spawn`.
3. One recovery path: after a Kobo firmware update, reinstall KFMon *or* use NickelMenu.
4. Explicit “do not” list: KSM, fmon, Ghost, Plato-as-dependency, firmware 5.x.
5. macOS Safari zip warning as step 0.
6. FB2/Russian as a KOReader setting, not a second installer.

Natural homes: a short KOReader wiki page “Libra Colour / firmware 4.45+” and a first-post summary on MobileRead that links the zip rather than burying the `cmd_spawn` line in a commented sample.

## Sources

- KOReader wiki, Installation on Kobo devices: https://github.com/koreader/koreader/wiki/Installation-on-Kobo-devices
- NiLuJe OCP sticky (packages + install script): https://www.mobileread.com/forums/showthread.php?t=314220
- KFMon README: https://github.com/NiLuJe/kfmon
- NickelMenu: https://pgaskin.net/NickelMenu/ and https://github.com/pgaskin/NickelMenu/blob/master/res/doc
- NickelMenu 4.45 report: https://github.com/pgaskin/NickelMenu/issues/229
- Kobo official formats: https://help.kobo.com/hc/en-us/articles/360017763713
- Kobo N428 firmware sideload: https://help.kobo.com/hc/en-us/articles/35059171032727-Manually-Updating-your-Kobo-eReader-device-Firmware
- Firmware 4.45.23697 thread: https://www.mobileread.com/forums/showthread.php?t=373709
- KFMon on Libra Colour 4.45.23697: https://www.mobileread.com/forums/showthread.php?t=314220&page=94
- Cited research dump: session `deep-research` report under this project’s workflow scratch
