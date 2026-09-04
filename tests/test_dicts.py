import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from kobo_sideload.__main__ import build_parser
from kobo_sideload.assemble import bundled_dir
from kobo_sideload.dicts import (
    CATALOG,
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
        self.assertEqual(parse_langs("en"), ["en"])
        self.assertEqual(parse_langs("ru"), ["ru"])
        self.assertEqual(parse_langs("en,ru"), ["en", "ru"])
        self.assertEqual(parse_langs("en, ru"), ["en", "ru"])
        self.assertEqual(parse_langs("both"), ["en", "ru"])
        with self.assertRaises(ValueError):
            parse_langs("fr")

    def test_specs_for_langs(self) -> None:
        en = specs_for_langs(["en"])
        self.assertEqual([spec.key for spec in en], ["gcide"])
        ru = specs_for_langs(["ru"])
        self.assertEqual([spec.key for spec in ru], ["rus-eng-short", "ushakov"])
        both = specs_for_langs(["en", "ru"])
        self.assertEqual([spec.key for spec in both], [spec.key for spec in CATALOG])
        self.assertEqual(specs_for_langs([]), [])

    def test_catalog_uses_koreader_targz(self) -> None:
        for spec in CATALOG:
            self.assertTrue(spec.url.startswith("http"))
            self.assertTrue(spec.filename.endswith(".tar.gz"))
            self.assertTrue(spec.langs)
            self.assertTrue(spec.license)

    def test_bundled_installers_keep_catalog_urls(self) -> None:
        sh = (bundled_dir() / "install.sh").read_text(encoding="utf-8")
        ps1 = (bundled_dir() / "install.ps1").read_text(encoding="utf-8")
        for spec in CATALOG:
            self.assertIn(spec.url, sh)
            self.assertIn(spec.url, ps1)
            self.assertIn(spec.filename, sh)
            self.assertIn(spec.filename, ps1)
        self.assertIn("STARDICT_DATA_DIR", sh)
        self.assertIn("STARDICT_DATA_DIR", ps1)
        self.assertNotIn("Remove-Item $destKo", ps1)

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
