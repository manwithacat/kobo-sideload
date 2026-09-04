import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from kobo_sideload.archive import payload_is_ready
from kobo_sideload.assemble import assemble, extract_payload_zip, package_payload
from tests.helpers import artifact, write_koreader_zip, write_nickelmenu_tgz


class PackageTests(unittest.TestCase):
    def test_zip_keeps_hidden_folders_and_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            zip_in = tmp_path / "koreader.zip"
            tgz = tmp_path / "KoboRoot.tgz"
            write_koreader_zip(zip_in)
            write_nickelmenu_tgz(tgz)
            payload = assemble(
                koreader_zip=zip_in,
                nickelmenu_tgz=tgz,
                payload_dir=tmp_path / "payload",
                koreader=artifact("koreader", "koreader.zip"),
                nickelmenu=artifact("nickelmenu", "KoboRoot.tgz"),
            )
            dist = package_payload(
                payload,
                tmp_path / "dist",
                artifact("koreader", "koreader.zip"),
                artifact("nickelmenu", "KoboRoot.tgz"),
            )
            self.assertTrue(dist.name.startswith("kobo-koreader-"))
            self.assertTrue(dist.with_name(dist.name + ".sha256").is_file())
            with zipfile.ZipFile(dist) as zf:
                names = zf.namelist()
            self.assertIn(".adds/koreader/koreader.sh", names)
            self.assertIn(".adds/nm/koreader", names)
            self.assertIn(".kobo/KoboRoot.tgz", names)
            self.assertIn("install.sh", names)
            self.assertIn("install.ps1", names)
            self.assertIn("READ ME FIRST.txt", names)
            self.assertNotIn("Install to Kobo.command", names)
            restored = extract_payload_zip(dist, tmp_path / "restored")
            self.assertTrue(payload_is_ready(restored))
            manifest = json.loads((restored / "MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["launcher"], "nickelmenu")


if __name__ == "__main__":
    unittest.main()
