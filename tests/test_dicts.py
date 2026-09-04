import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from kobo_sideload.__main__ import build_parser
from kobo_sideload.assemble import bundled_dir
from kobo_sideload.dicts import (
    CATALOG,
    available_langs,
    catalog_path,
    format_lang_prompt,
    lang_choice_hint,
    load_catalog,
    parse_langs,
    specs_for_langs,
    unpack_stardict_archive,
)


def _stardict_tarball(path: Path, stem: str, *, with_res: bool = False) -> None:
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode="w:gz") as tar:
        files = {
            f"stardict-{stem}/": None,
            f"stardict-{stem}/{stem}.ifo": f"StarDict's dict ifo file\nwordcount=1\nbookname={stem}\n",
            f"stardict-{stem}/{stem}.idx": b"\x00\x00",
            f"stardict-{stem}/{stem}.dict": f"{stem} definition\n",
        }
        if with_res:
            files[f"stardict-{stem}/res/"] = None
            files[f"stardict-{stem}/res/note.txt"] = "resource\n"
        for name, content in files.items():
            info = tarfile.TarInfo(name=name)
            if content is None:
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)
                continue
            data = content if isinstance(content, bytes) else content.encode("utf-8")
            info.size = len(data)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    path.write_bytes(payload.getvalue())


class DictTests(unittest.TestCase):
    def test_parse_langs(self) -> None:
        self.assertEqual(parse_langs("skip"), [])
        self.assertEqual(parse_langs(""), [])
        self.assertEqual(parse_langs("s"), [])
        self.assertEqual(parse_langs("en"), ["en"])
        self.assertEqual(parse_langs("ru"), ["ru"])
        self.assertEqual(parse_langs("1"), ["ru"])
        self.assertEqual(parse_langs("2"), ["en"])
        self.assertEqual(parse_langs("1,2"), ["ru", "en"])
        self.assertEqual(parse_langs("en,ru"), ["en", "ru"])
        self.assertEqual(parse_langs("en, ru"), ["en", "ru"])
        self.assertEqual(parse_langs("both"), available_langs())
        self.assertEqual(parse_langs("all"), available_langs())
        self.assertEqual(parse_langs("a"), available_langs())
        with self.assertRaises(ValueError):
            parse_langs("fr")
        with self.assertRaises(ValueError):
            parse_langs("9")

    def test_specs_for_langs(self) -> None:
        en = specs_for_langs(["en"])
        self.assertEqual([spec.key for spec in en], ["gcide"])
        ru = specs_for_langs(["ru"])
        self.assertEqual([spec.key for spec in ru], ["rus-eng-short", "ushakov"])
        both = specs_for_langs(["en", "ru"])
        self.assertEqual([spec.key for spec in both], [spec.key for spec in CATALOG])
        self.assertEqual(specs_for_langs([]), [])

    def test_catalog_file_is_the_source_of_truth(self) -> None:
        self.assertEqual(load_catalog(), CATALOG)
        self.assertEqual(catalog_path(), bundled_dir() / "dictionaries.tsv")
        self.assertEqual(available_langs(), ["ru", "en"])
        prompt = "\n".join(format_lang_prompt())
        self.assertIn("  1) Russian", prompt)
        self.assertIn("  2) English", prompt)
        self.assertIn("Russian-English short dictionary", prompt)
        self.assertIn("Ushakov explanatory dictionary (Russian)", prompt)
        self.assertIn("GNU Collaborative International Dictionary of English", prompt)
        self.assertIn("  A) all of the above", prompt)
        self.assertIn("  S) skip", prompt)
        self.assertEqual(lang_choice_hint(), "1-2, A, or S")
        for spec in CATALOG:
            self.assertTrue(spec.url.startswith("http"))
            self.assertTrue(spec.filename.endswith(".tar.gz"))
            self.assertTrue(spec.langs)
            self.assertTrue(spec.license)
            self.assertTrue(spec.label)

    def test_notice_lists_every_catalog_entry(self) -> None:
        notice = (Path(__file__).resolve().parents[1] / "NOTICE.md").read_text(encoding="utf-8")
        for spec in CATALOG:
            self.assertIn(spec.name, notice)
            self.assertIn(spec.license, notice)

    def test_bundled_installers_read_the_tsv(self) -> None:
        tsv = (bundled_dir() / "dictionaries.tsv").read_text(encoding="utf-8")
        sh = (bundled_dir() / "install.sh").read_text(encoding="utf-8")
        ps1 = (bundled_dir() / "install.ps1").read_text(encoding="utf-8")
        for spec in CATALOG:
            self.assertIn(spec.url, tsv)
            self.assertIn(spec.filename, tsv)
            self.assertNotIn(spec.url, sh)
            self.assertNotIn(spec.url, ps1)
        self.assertIn("dictionaries.tsv", sh)
        self.assertIn("dictionaries.tsv", ps1)
        self.assertIn("STARDICT_DATA_DIR", sh)
        self.assertIn("STARDICT_DATA_DIR", ps1)
        self.assertNotIn("Remove-Item $destKo", ps1)

    def test_extra_language_row_is_selectable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dictionaries.tsv"
            path.write_text(
                "gcide\ten\tEnglish\tGCIDE\tGPLv3+\tgcide.tar.gz\thttp://example.test/gcide.tar.gz\n"
                "foo\tfr\tFrench\tFrench dict\tGPL\tfr.tar.gz\thttps://example.test/fr.tar.gz\n",
                encoding="utf-8",
            )
            catalog = load_catalog(path)
            self.assertEqual(available_langs(catalog), ["en", "fr"])
            self.assertEqual(parse_langs("fr", catalog), ["fr"])
            self.assertEqual(parse_langs("2", catalog), ["fr"])
            self.assertEqual(parse_langs("all", catalog), ["en", "fr"])
            self.assertEqual([spec.key for spec in specs_for_langs(["fr"], catalog)], ["foo"])
            prompt = "\n".join(format_lang_prompt(catalog))
            self.assertIn("  1) English", prompt)
            self.assertIn("  2) French", prompt)
            self.assertIn("French dict", prompt)

    def test_load_catalog_rejects_zst_and_bad_lang(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dictionaries.tsv"
            path.write_text(
                "bad\tfr\tFrench\tNope\tGPL\tfr.tar.zst\thttps://example.test/fr.tar.zst\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, r"\.tar\.gz"):
                load_catalog(path)
            path.write_text(
                "bad\tfrench\tFrench\tNope\tGPL\tfr.tar.gz\thttps://example.test/fr.tar.gz\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "invalid language"):
                load_catalog(path)

    def test_unpack_stardict_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archive = tmp_path / "gcide.tar.gz"
            dest = tmp_path / "dictionaries"
            _stardict_tarball(archive, "gcide", with_res=True)
            installed = unpack_stardict_archive(archive, dest)
            self.assertEqual([path.name for path in installed], ["gcide"])
            self.assertTrue((dest / "gcide" / "gcide.ifo").is_file())
            self.assertTrue((dest / "gcide" / "gcide.dict").is_file())
            self.assertTrue((dest / "gcide" / "res" / "note.txt").is_file())
            self.assertFalse((dest / ".unpack").exists())

    def test_unpack_stardict_with_unreadable_tar_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archive = tmp_path / "gcide.tar.gz"
            dest = tmp_path / "dictionaries"
            payload = io.BytesIO()
            with tarfile.open(fileobj=payload, mode="w:gz") as tar:
                directory = tarfile.TarInfo("stardict-gcide/")
                directory.type = tarfile.DIRTYPE
                directory.mode = 0o644
                tar.addfile(directory)
                info = tarfile.TarInfo("stardict-gcide/gcide.ifo")
                data = b"StarDict's dict ifo file\n"
                info.size = len(data)
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(data))
            archive.write_bytes(payload.getvalue())
            unpack_stardict_archive(archive, dest)
            self.assertTrue((dest / "gcide" / "gcide.ifo").is_file())

    def test_unpack_rejects_archive_without_ifo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archive = tmp_path / "empty.tar.gz"
            payload = io.BytesIO()
            with tarfile.open(fileobj=payload, mode="w:gz") as tar:
                info = tarfile.TarInfo(name="readme.txt")
                data = b"no dict"
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            archive.write_bytes(payload.getvalue())
            with self.assertRaisesRegex(RuntimeError, "no StarDict"):
                unpack_stardict_archive(archive, tmp_path / "dest")

    def test_cli_install_dicts_flag_and_dictionaries_command(self) -> None:
        parser = build_parser()
        install = parser.parse_args(["install", "--yes", "--dicts", "en,ru"])
        self.assertEqual(install.dicts, "en,ru")
        self.assertTrue(install.yes)
        dictionaries = parser.parse_args(["dictionaries", "--lang", "ru", "--yes"])
        self.assertEqual(dictionaries.lang, "ru")
        self.assertTrue(dictionaries.yes)


if __name__ == "__main__":
    unittest.main()
