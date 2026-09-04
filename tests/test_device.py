import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kobo_sideload.config import (
    BOOKS_FOLDER,
    EXCLUDE_SYNC_FOLDERS,
    EXCLUDE_SYNC_KEY,
    STARDICT_LUA_LINE,
    STARDICT_LUA_MARKER,
)
from kobo_sideload.device import (
    KoboVolume,
    eject_kobo,
    ensure_exclude_sync_folders,
    ensure_stardict_lua,
    install_payload,
    merge_copytree,
    verify_install,
)


def _fake_volume(root: Path) -> KoboVolume:
    root.mkdir(parents=True, exist_ok=True)
    kobo_dir = root / ".kobo"
    kobo_dir.mkdir()
    conf = kobo_dir / "Kobo" / "Kobo eReader.conf"
    conf.parent.mkdir(parents=True)
    conf.write_text("[ApplicationPreferences]\nCurrentLocale=en\n", encoding="utf-8")
    return KoboVolume(mountpoint=root, kobo_dir=kobo_dir, conf_path=conf)


def _payload(root: Path) -> Path:
    payload = root / "payload"
    (payload / ".adds" / "koreader").mkdir(parents=True)
    (payload / ".adds" / "koreader" / "koreader.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (payload / ".adds" / "nm").mkdir()
    (payload / ".adds" / "nm" / "koreader").write_text("menu_item:main:KOReader:cmd_spawn:quiet:exec x\n")
    (payload / ".kobo").mkdir()
    (payload / ".kobo" / "KoboRoot.tgz").write_bytes(b"tgz")
    (payload / "MANIFEST.json").write_text("{}\n", encoding="utf-8")
    (payload / BOOKS_FOLDER).mkdir()
    (payload / BOOKS_FOLDER / "README.txt").write_text("sideload library\n", encoding="utf-8")
    return payload


class DeviceTests(unittest.TestCase):
    def test_exclude_sync_folders_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conf = Path(tmp) / "Kobo eReader.conf"
            self.assertTrue(ensure_exclude_sync_folders(conf))
            self.assertFalse(ensure_exclude_sync_folders(conf))
            text = conf.read_text(encoding="utf-8")
            self.assertEqual(text.count(f"{EXCLUDE_SYNC_KEY}={EXCLUDE_SYNC_FOLDERS}"), 1)

    def test_install_and_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            volume = _fake_volume(tmp_path / "kobo")
            payload = _payload(tmp_path)
            install_payload(payload, volume)
            self.assertEqual(verify_install(volume), [])
            self.assertTrue((volume.mountpoint / ".adds" / "koreader" / "koreader.sh").is_file())
            self.assertTrue((volume.kobo_dir / "KoboRoot.tgz").is_file())
            self.assertTrue((volume.mountpoint / BOOKS_FOLDER / "README.txt").is_file())
            self.assertTrue((volume.mountpoint / ".adds" / "dictionaries" / "README.txt").is_file())
            lua = (volume.mountpoint / ".adds" / "koreader" / "defaults.custom.lua").read_text(
                encoding="utf-8"
            )
            self.assertIn(STARDICT_LUA_MARKER, lua)
            self.assertIn(STARDICT_LUA_LINE, lua)

    def test_books_folder_is_not_wiped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            volume = _fake_volume(tmp_path / "kobo")
            keep = volume.mountpoint / BOOKS_FOLDER / "keep.fb2"
            keep.parent.mkdir()
            keep.write_text("mine\n", encoding="utf-8")
            install_payload(_payload(tmp_path), volume)
            self.assertEqual(keep.read_text(encoding="utf-8"), "mine\n")
            self.assertTrue((volume.mountpoint / BOOKS_FOLDER / "README.txt").is_file())

    def test_exclude_sync_folders_upgrades_old_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conf = Path(tmp) / "Kobo eReader.conf"
            conf.write_text(
                "[FeatureSettings]\n"
                r"ExcludeSyncFolders=(\\.(?!kobo|adobe).+|([^.][^/]*/)+\\..+)"
                "\n",
                encoding="utf-8",
            )
            self.assertTrue(ensure_exclude_sync_folders(conf))
            text = conf.read_text(encoding="utf-8")
            self.assertIn(f"{EXCLUDE_SYNC_KEY}={EXCLUDE_SYNC_FOLDERS}", text)
            self.assertEqual(text.count(f"{EXCLUDE_SYNC_KEY}="), 1)

    def test_koreader_merge_preserves_settings_and_dicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            volume = _fake_volume(tmp_path / "kobo")
            payload = _payload(tmp_path)
            install_payload(payload, volume)
            settings = volume.mountpoint / ".adds" / "koreader" / "settings.reader.lua"
            settings.write_text("-- keep me\n", encoding="utf-8")
            old = (
                volume.mountpoint
                / ".adds"
                / "koreader"
                / "data"
                / "dict"
                / "olddict"
                / "old.ifo"
            )
            old.parent.mkdir(parents=True)
            old.write_text("ifo\n", encoding="utf-8")
            extra = volume.mountpoint / ".adds" / "dictionaries" / "custom" / "x.ifo"
            extra.parent.mkdir()
            extra.write_text("x\n", encoding="utf-8")
            (payload / ".adds" / "koreader" / "koreader.sh").write_text(
                "#!/bin/sh\necho new\n", encoding="utf-8"
            )
            install_payload(payload, volume)
            self.assertEqual(settings.read_text(encoding="utf-8"), "-- keep me\n")
            self.assertEqual(
                (volume.mountpoint / ".adds" / "koreader" / "koreader.sh").read_text(
                    encoding="utf-8"
                ),
                "#!/bin/sh\necho new\n",
            )
            self.assertTrue(old.is_file())
            migrated = volume.mountpoint / ".adds" / "dictionaries" / "olddict" / "old.ifo"
            self.assertTrue(migrated.is_file())
            self.assertEqual(extra.read_text(encoding="utf-8"), "x\n")
            lua = (volume.mountpoint / ".adds" / "koreader" / "defaults.custom.lua").read_text(
                encoding="utf-8"
            )
            self.assertEqual(lua.count(STARDICT_LUA_MARKER), 1)
            self.assertIn(STARDICT_LUA_LINE, lua)

    def test_stardict_lua_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            koreader = Path(tmp) / "koreader"
            koreader.mkdir()
            self.assertTrue(ensure_stardict_lua(koreader))
            self.assertFalse(ensure_stardict_lua(koreader))
            text = (koreader / "defaults.custom.lua").read_text(encoding="utf-8")
            self.assertEqual(text.count(STARDICT_LUA_MARKER), 1)
            self.assertIn(STARDICT_LUA_LINE, text)

    def test_merge_copytree_keeps_extra_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dest = Path(tmp) / "dest"
            (src / "sub").mkdir(parents=True)
            (src / "a.txt").write_text("new\n", encoding="utf-8")
            (src / "sub" / "b.txt").write_text("b\n", encoding="utf-8")
            dest.mkdir()
            (dest / "a.txt").write_text("old\n", encoding="utf-8")
            (dest / "keep.txt").write_text("keep\n", encoding="utf-8")
            merge_copytree(src, dest)
            self.assertEqual((dest / "a.txt").read_text(encoding="utf-8"), "new\n")
            self.assertEqual((dest / "keep.txt").read_text(encoding="utf-8"), "keep\n")
            self.assertEqual((dest / "sub" / "b.txt").read_text(encoding="utf-8"), "b\n")

    def test_eject_uses_diskutil_on_macos(self) -> None:
        volume = KoboVolume(
            mountpoint=Path("/Volumes/KOBOeReader"),
            kobo_dir=Path("/Volumes/KOBOeReader/.kobo"),
            conf_path=Path("/Volumes/KOBOeReader/.kobo/Kobo/Kobo eReader.conf"),
        )
        uname = mock.Mock(sysname="Darwin")
        with mock.patch("kobo_sideload.device.os.name", "posix"), mock.patch(
            "kobo_sideload.device.os.uname", return_value=uname, create=True
        ), mock.patch("kobo_sideload.device.subprocess.check_call") as call:
            eject_kobo(volume)
        call.assert_called_once_with(["diskutil", "eject", "/Volumes/KOBOeReader"])


if __name__ == "__main__":
    unittest.main()
