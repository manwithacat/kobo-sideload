import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kobo_sideload.paths import default_home, work_dirs


class PathsTests(unittest.TestCase):
    def test_env_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"KOBO_SIDELOAD_HOME": tmp}):
                self.assertEqual(default_home(), Path(tmp))

    def test_work_dirs_shape(self) -> None:
        dirs = work_dirs(Path("/tmp/sideload"))
        self.assertEqual(dirs["payload"], Path("/tmp/sideload/payload"))
        self.assertEqual(dirs["dist"], Path("/tmp/sideload/dist"))
        self.assertEqual(dirs["catalog"], Path("/tmp/sideload/catalog.json"))
