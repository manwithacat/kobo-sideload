import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from kobo_sideload.assemble import assemble
from kobo_sideload.config import NICKELMENU_CONFIG
from tests.helpers import artifact, write_koreader_zip, write_nickelmenu_tgz


class AssembleTests(unittest.TestCase):
    def test_payload_layout_drops_trigger_png_and_writes_nm_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            zip_path = tmp_path / "koreader.zip"
            tgz_path = tmp_path / "KoboRoot.tgz"
            write_koreader_zip(zip_path)
            write_nickelmenu_tgz(tgz_path)
            payload = assemble(
                koreader_zip=zip_path,
                nickelmenu_tgz=tgz_path,
                payload_dir=tmp_path / "payload",
                koreader=artifact("koreader", "koreader.zip"),
                nickelmenu=artifact("nickelmenu", "KoboRoot.tgz"),
            )
            self.assertTrue((payload / ".adds" / "koreader" / "koreader.sh").is_file())
            self.assertFalse((payload / "koreader.png").exists())
            self.assertFalse((payload / ".adds" / "koreader.png").exists())
            nm = (payload / ".adds" / "nm" / "koreader").read_text(encoding="utf-8")
            self.assertEqual(nm, NICKELMENU_CONFIG)
            self.assertIn("cmd_spawn", nm)
            self.assertNotIn("#menu_item", nm)
            manifest = json.loads((payload / "MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["launcher"], "nickelmenu")
            self.assertEqual(manifest["omitted"], ["kfmon", "plato"])
            self.assertIn("koreader", manifest["upstream_licenses"])
            self.assertTrue((payload / "KOReader" / "README.txt").is_file())

    def test_rejects_tarball_without_libnm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            zip_path = tmp_path / "koreader.zip"
            tgz_path = tmp_path / "KoboRoot.tgz"
            write_koreader_zip(zip_path)
            payload = io.BytesIO()
            with tarfile.open(fileobj=payload, mode="w:gz") as tar:
                info = tarfile.TarInfo(name="./readme.txt")
                data = b"nope"
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            tgz_path.write_bytes(payload.getvalue())
            with self.assertRaisesRegex(RuntimeError, "libnm.so"):
                assemble(
                    koreader_zip=zip_path,
                    nickelmenu_tgz=tgz_path,
                    payload_dir=tmp_path / "payload",
                    koreader=artifact("koreader", "koreader.zip"),
                    nickelmenu=artifact("nickelmenu", "KoboRoot.tgz"),
                )


if __name__ == "__main__":
    unittest.main()
