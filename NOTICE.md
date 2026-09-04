# Upstream software this tool installs

`kobo-sideload` is MIT-licensed glue. The files it copies onto a Kobo are
**not** ours. A payload zip and a device install contain:

| Project | License | Source |
| --- | --- | --- |
| [KOReader](https://github.com/koreader/koreader) | AGPL-3.0-or-later | `koreader-kobo-*.zip` GitHub release asset |
| [NickelMenu](https://github.com/pgaskin/NickelMenu) | MIT | `KoboRoot.tgz` GitHub release asset |

Redistributing a CI-built payload zip redistributes KOReader and NickelMenu.
Keep their licenses with the zip (they already ship inside the KOReader tree
and the NickelMenu tarball). Do not strip `.adds/koreader/COPYING`.
