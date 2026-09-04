# Upstream software this tool installs

`kobo-sideload` is MIT-licensed glue. The files it copies onto a Kobo are
**not** ours. A payload zip and a device install contain:

| Project | License | Source |
| --- | --- | --- |
| [KOReader](https://github.com/koreader/koreader) | AGPL-3.0-or-later | `koreader-kobo-*.zip` GitHub release asset |
| [NickelMenu](https://github.com/pgaskin/NickelMenu) | MIT | `KoboRoot.tgz` GitHub release asset |

Optional dictionaries (not in the GitHub app zip; fetched only if you ask
the installer or `kobo-sideload dictionaries`) come from the same tar.gz
files KOReader lists in `frontend/ui/data/dictionaries.lua`:

| Dictionary | License | Source |
| --- | --- | --- |
| GNU Collaborative International Dictionary of English (gcide) | GPLv3+ | `http://build.koreader.rocks/download/dict/gcide.tar.gz` |
| Russian-English short dictionary | GPL | GitLab `avsej/dicts-stardict-form-xdxf` |
| Ushakov explanatory dictionary (Russian) | see upstream `.ifo` | GitLab `avsej/dicts-stardict-form-xdxf` |

Redistributing a CI-built payload zip redistributes KOReader and NickelMenu.
Keep their licenses with the zip (they already ship inside the KOReader tree
and the NickelMenu tarball). Do not strip `.adds/koreader/COPYING`.
Do not add dictionary archives to that zip.
