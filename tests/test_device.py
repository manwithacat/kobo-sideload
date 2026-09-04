import tempfile
import unittest
from pathlib import Path

from kobo_sideload.config import EXCLUDE_SYNC_FOLDERS, EXCLUDE_SYNC_KEY
from kobo_sideload.device import (
    KoboVolume,
    ensure_exclude_sync_folders,
    install_payload,
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


if __name__ == "__main__":
    unittest.main()
