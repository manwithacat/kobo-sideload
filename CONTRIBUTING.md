# Contributing

PRs welcome. This repo is MIT glue that assembles current KOReader + NickelMenu
onto a Kobo. It does not vendor KFMon, Plato, or dictionary archives.

## Dictionary languages

The installer can fetch StarDict files for extra languages. The GitHub zip
**never** contains those archives (size and licences). Users opt in at install
time, or later in KOReader over Wi-Fi.

The catalog is one file:

```text
kobo_sideload/bundled/dictionaries.tsv
```

Python, `install.sh`, and `install.ps1` all read it. Adding a language is a
row in that file plus a NOTICE line — not a copy-paste through three installers.

### Add a language (or another dictionary for an existing language)

1. Add one **tab-separated** row to `kobo_sideload/bundled/dictionaries.tsv`.
2. Add the dictionary to the table in `NOTICE.md`.
3. Run `python3 -m unittest discover -s tests -v`.
4. Open a pull request.

Do not commit `.tar.gz` files. CI rebuilds the user zip on merge to `main`;
the new row ships as catalog text only.

### Row format

```text
key	langs	label	name	license	filename	url
```

| Field | Meaning |
| --- | --- |
| `key` | Stable id: `a-z`, digits, `.`, `_`, `-`. Unique in the file. |
| `langs` | Comma-separated ISO 639 codes (`en`, `ru`, `fr`, `de`, …). A bilingual dict can list both: `ja,en`. |
| `label` | Short name in the install prompt. The first row for a code wins (`ru` + `ru` → one “Russian” line). |
| `name` | Full dictionary title (shown when downloading). |
| `license` | SPDX-style or a short phrase. Must be redistributable. |
| `filename` | Cache name. Must end in `.tar.gz`. |
| `url` | Public `http://` or `https://` download. No login. |

No tabs inside values. Lines starting with `#` are comments.

Optional 8th field: SHA-256 of the archive. Leave it off if HEAD/checksums
are unreliable; the installer checks that the tarball contains `.ifo` files.

### What we will merge

- StarDict layout: `.ifo` + `.idx` + `.dict` or `.dict.dz` (and optional `res/`).
- **`.tar.gz` only.** Not `.tar.zst` — the zip installer uses stock macOS/Windows `tar`.
- Prefer the same files KOReader already lists in
  [`frontend/ui/data/dictionaries.lua`](https://github.com/koreader/koreader/blob/master/frontend/ui/data/dictionaries.lua)
  (`build.koreader.rocks` or the GitLab `dicts-stardict-form-xdxf` pins).
- A licence the user can actually accept (GPL, CC-BY-SA, public domain, …).
  No proprietary “reader.dict” dumps.
- A modest download. Prefer the short/abridged dict when Wiktionary is 100+ MB.
- A URL that returns 200 without cookies.

### What we will not merge

- Archives checked into this repo or attached to GitHub Releases.
- Changes that wipe `.adds/koreader/` or `.adds/dictionaries` on reinstall.
- KFMon / Plato as defaults.

### Prompt the user will see

Languages are numbered in **file order** (first distinct `langs` code is `1)`).
Each menu entry lists the dictionary titles for that code. The user types a
number (`1`), comma-separated numbers (`1,2`), `A` for all, or `S` to skip.

Scripts can still use codes: `KOBO_SIDELOAD_DICTS=ru` and
`kobo-sideload install --dicts ru`. Put the language you want first in the
TSV if it should be option `1`.

## Tests and local install

Python 3.9+, stdlib only:

```text
python3 -m unittest discover -s tests -v
python3 -m kobo_sideload --help
```

Do not put secrets in the catalog. Do not bump the sideload version in a
language PR unless the maintainer asks — merging to `main` is enough for the
next weekly/push build to pick up the TSV.
