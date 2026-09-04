import io
import tarfile
import zipfile
from pathlib import Path

from kobo_sideload.catalog import Artifact


def artifact(name: str, filename: str) -> Artifact:
    return Artifact(
        name=name,
        project="test/test",
        tag="vtest",
        filename=filename,
        url="https://example.test/" + filename,
        sha256=None,
        size=1,
        published_at=None,
    )


def write_koreader_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("koreader/koreader.sh", "#!/bin/sh\necho ok\n")
        zf.writestr("koreader.png", "not-an-icon")


def write_nickelmenu_tgz(path: Path) -> None:
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode="w:gz") as tar:
        info = tarfile.TarInfo(name="./usr/local/Kobo/imageformats/libnm.so")
        data = b"fake-plugin"
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    path.write_bytes(payload.getvalue())
