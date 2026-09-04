# What each Kobo sideload piece actually does

This is an independent reverse-engineering of the KOReader-on-Kobo stack, not a restatement of the MobileRead sticky. The old “one-click” zip is a *bundler*. It is not a runtime.

## Two kinds of write

A Kobo in USB storage mode exposes one FAT volume labeled `KOBOeReader`. Two very different things get copied onto it:

| Kind | Where it lives | When it runs | Survives a Kobo firmware update? |
| --- | --- | --- | --- |
| **User-storage payload** | `.adds/…` on the USB volume | When something launches it | Yes |
| **Rootfs payload** | `.kobo/KoboRoot.tgz` | On eject: Nickel treats the tarball as an official update, extracts it onto the Linux root filesystem, deletes the tarball, reboots | **No.** A firmware update restores vanilla startup files |

If the device does not reboot after eject, `KoboRoot.tgz` never landed in `.kobo/`. That is the most common Mac failure (Safari auto-unzip + Finder hiding dot folders).

## Components

### Nickel

Kobo’s stock UI. You keep it. It cannot start KOReader. Official format list is EPUB/PDF/MOBI/TXT/HTML/RTF/CBZ/CBR — not FB2.

Firmware 4.17+ will index hidden folders (`.adds`) unless this key is set in `.kobo/Kobo/Kobo eReader.conf`:

```
[FeatureSettings]
ExcludeSyncFolders=(\\.(?!kobo|adobe).+|([^.][^/]*/)+\\..+)
```

That is the *only* Nickel config the install needs. The 2019 `install.command` always appends it; a second run duplicates the block. QSettings last-wins, but a modern installer should be idempotent.

### KOReader

The reader. Lives entirely in `.adds/koreader/`. Entry point: `koreader.sh`.

Canonical download, not the OCP zip:

- Firmware 4.x (Libra Colour 4.45): `koreader-kobo-{tag}.zip` from [koreader/koreader releases](https://github.com/koreader/koreader/releases)
- Firmware 5.x: `koreader-kobov5-{tag}.zip`

The zip contains a `koreader/` folder plus a leftover `koreader.png` (old fmon trigger). The PNG is not needed if you launch from NickelMenu.

KOReader v2026.07.1 (1 Aug 2026) is current. NiLuJe’s OCP zip is still **v2026.03**. The one-click channel lags GitHub because a human rebuilds it.

FB2 (including windows-1251 / koi8-r / cp866) and Russian hyphenation are inside KOReader. There is no Russia-specific package.

### NickelMenu

A Qt image-format plugin (`libnm.so`) dropped into `/usr/local/Kobo/imageformats/`. Nickel loads image plugins at startup, so the plugin can inject menu items.

Canonical download: `KoboRoot.tgz` from [pgaskin/NickelMenu releases](https://github.com/pgaskin/NickelMenu/releases) (currently v0.6.0). That tarball *is* the rootfs payload. Current latest: 7 Dec 2025.

Config is plain text files in `.adds/nm/` (no extension). The line that starts KOReader, which OCP ships **commented out**, is:

```
menu_item:main:KOReader:cmd_spawn:quiet:exec /mnt/onboard/.adds/koreader/koreader.sh
```

That is the whole launcher. NickelMenu is documented as persisting across firmware 4.x updates. It does not support firmware 5.x yet.

### KFMon (optional, not used by this repo’s default path)

A daemon that watches a PNG in the library (`koreader.png`) via inotify and runs a script when Nickel “opens” that fake book. It starts because it **replaces** `/etc/init.d/on-animator.sh` (the boot progress-bar script). Firmware updates restore the vanilla script, so KFMon dies until you drop another `KoboRoot.tgz`.

KFMon has **no GitHub Releases**. Tags exist (`v1.4.6`); the zip people actually install is `KFMon-v1.4.6-191-gca31869`, published on NiLuJe’s OVH bucket. That is why OCP exists: it is NiLuJe’s private merge of KFMon + NickelMenu + KOReader + Plato.

You do not need KFMon to run KOReader on firmware 4.6+.

### Plato (optional, not used)

A *different* document reader (`baskerville/plato`). OCP bundles it because KFMon can launch more than one app. It is not a KOReader dependency and does nothing for FB2 that KOReader does not already do.

### fmon / KSM

Older launchers. fmon and KFMon patch the same startup script; last installed wins. Kobo Start Menu always takes precedence and is deprecated on Clara-or-newer / firmware 4.25+. Do not install either.

## What `one-click.py` actually does

NiLuJe’s builder ([kfmon/tools/one-click.py](https://github.com/NiLuJe/kfmon/blob/master/tools/one-click.py)):

1. Takes a **local** `KFMon-v*.zip` (he built it).
2. Downloads latest NickelMenu `KoboRoot.tgz` from GitHub.
3. Downloads latest `koreader-kobo-*.zip` and `plato-*.zip` from GitHub.
4. Merges the two KoboRoot tarballs (KFMon’s patched `on-animator.sh` + NickelMenu’s `libnm.so`).
5. Stages three combo zips and an `OCP-KFMon` repair zip.
6. Ships NickelMenu configs with the `cmd_spawn` lines **commented**, relying on KFMon’s IPC generator to fill the menu.

The macOS/Linux/Windows install scripts then: find volume label `KOBOeReader`, append `ExcludeSyncFolders`, unzip the combo zip to the volume root, check that `KoboRoot.tgz` and `kfmon.png` exist, `sync`. They never download anything. They never uncomment the NickelMenu launch line. They require the zip to sit next to the script — Safari auto-extract is called out as a known footgun and left as a FAQ.

That is the “enthusiast, not consumer” shape: a human-maintained mega-zip, three OS-specific unzip wrappers, and a launcher config that does not work unless a second daemon is alive.

## What this repo does instead

`python3 -m kobo_sideload` talks to GitHub only:

1. **discover** — latest `koreader-kobo-*.zip` + NickelMenu `KoboRoot.tgz`
2. **fetch** — download + SHA-256 (GitHub asset digest)
3. **assemble** — device-shaped tree with the `cmd_spawn` line **enabled**
4. **install** — copy onto the mounted Kobo, write `ExcludeSyncFolders` once, verify

No KFMon, no Plato, no OVH, no `install.command`. One Python 3 stdlib program on macOS, Linux, and Windows.
