import unittest

from kobo_sideload.catalog import discover, discover_koreader


def _release(tag: str, assets: list[dict]) -> dict:
    return {"tag_name": tag, "published_at": "2026-08-01T11:10:30Z", "assets": assets}


def _asset(name: str, digest: str, url: str) -> dict:
    return {
        "name": name,
        "browser_download_url": url,
        "digest": f"sha256:{digest}",
        "size": 12,
    }


KOREADER = _release(
    "v2026.07.1",
    [
        _asset(
            "koreader-kobo-v2026.07.1.zip",
            "aa" * 32,
            "https://example.test/koreader-kobo-v2026.07.1.zip",
        ),
        _asset(
            "koreader-kobov5-v2026.07.1.zip",
            "bb" * 32,
            "https://example.test/koreader-kobov5-v2026.07.1.zip",
        ),
    ],
)
NICKELMENU = _release(
    "v0.6.0",
    [_asset("KoboRoot.tgz", "cc" * 32, "https://example.test/KoboRoot.tgz")],
)


def getter(url: str) -> dict:
    if url.endswith("koreader/koreader/releases/latest"):
        return KOREADER
    if url.endswith("pgaskin/NickelMenu/releases/latest"):
        return NICKELMENU
    raise AssertionError(url)


class DiscoverTests(unittest.TestCase):
    def test_firmware_4_picks_kobo_zip_not_v5(self) -> None:
        art = discover_koreader("4", getter)
        self.assertEqual(art.filename, "koreader-kobo-v2026.07.1.zip")
        self.assertEqual(art.tag, "v2026.07.1")
        self.assertEqual(art.sha256, "aa" * 32)

    def test_firmware_5_picks_kobov5_zip(self) -> None:
        art = discover_koreader("5", getter)
        self.assertEqual(art.filename, "koreader-kobov5-v2026.07.1.zip")

    def test_discover_returns_koreader_and_nickelmenu_only(self) -> None:
        arts = discover("4", getter)
        self.assertEqual(set(arts), {"koreader", "nickelmenu"})
        self.assertEqual(arts["nickelmenu"].filename, "KoboRoot.tgz")
        self.assertNotIn("kfmon", arts)
        self.assertNotIn("plato", arts)

    def test_missing_asset_is_explicit(self) -> None:
        def empty(_url: str) -> dict:
            return _release("v1", [])

        with self.assertRaisesRegex(RuntimeError, "no asset"):
            discover_koreader("4", empty)


if __name__ == "__main__":
    unittest.main()
