"""Protect public-only reporting, complete pagination, and last-good output."""

import pathlib
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import update_profile_stats as stats


def repository(name, **overrides):
    data = {
        "name": name, "private": False, "visibility": "public", "fork": False,
        "owner": {"login": stats.USERNAME}, "stargazers_count": 3,
    }
    data.update(overrides)
    return data


class ProfileStatsTests(unittest.TestCase):
    def test_pagination_privacy_forks_and_language_totals(self):
        called = []

        def fetch(endpoint, *, paginate=False):
            called.append(endpoint)
            if endpoint == f"users/{stats.USERNAME}":
                return {"followers": 12}
            if endpoint.startswith("users/"):
                self.assertTrue(paginate)
                return [
                    [repository("one"), repository("private", private=True), repository("fork", fork=True)],
                    [repository("two"), repository("internal", visibility="internal"), repository("foreign", owner={"login": "someone-else"})],
                ]
            return {"Python": 10, "Shell": 20} if "/one/" in endpoint else {"Python": 30}

        snapshot = stats.collect_snapshot(fetch, "2026-09-16")
        self.assertEqual(snapshot["public_repositories"], 3)
        self.assertEqual(snapshot["original_repositories"], 2)
        self.assertEqual(snapshot["stars"], 6)
        self.assertEqual(snapshot["languages"], {"Python": 40, "Shell": 20})
        self.assertEqual(len([path for path in called if path.startswith("repos/")]), 2)
        self.assertFalse(any(f"/{name}/" in path for name in ("private", "internal", "foreign", "fork") for path in called))

    def test_missing_visibility_is_not_public(self):
        repo = repository("unknown")
        del repo["private"]
        self.assertEqual(stats.public_owned([repo]), [])

    def test_empty_languages_and_xml_escaping(self):
        empty = {"languages": {}, "date": "2026-09-16"}
        root = ET.fromstring(stats.render_languages(empty))
        self.assertIn("No public language data", "".join(root.itertext()))
        escaped = stats.render_languages({**empty, "languages": {"A&B <script>": 10}})
        root = ET.fromstring(escaped)
        self.assertIn("A&B <script>", "".join(root.itertext()))
        self.assertNotIn("<script>", escaped)

    def test_remaining_languages_are_included_in_other(self):
        snapshot = {"date": "2026-09-16", "languages": {f"Language {i}": 10 for i in range(8)}}
        rendered = stats.render_languages(snapshot)
        ET.fromstring(rendered)
        self.assertIn("Other: 37.5%", rendered)

    def test_failed_read_preserves_existing_cards(self):
        def failing(endpoint, **kwargs):
            raise RuntimeError("API unavailable")

        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory)
            for name in ("github-stats.svg", "top-languages.svg"):
                (output / name).write_text("last good card")
            with self.assertRaisesRegex(RuntimeError, "API unavailable"):
                stats.refresh(output, failing)
            self.assertEqual([path.read_text() for path in output.iterdir()], ["last good card"] * 2)

    def test_failed_language_read_preserves_both_cards(self):
        def fetch(endpoint, **kwargs):
            if endpoint == f"users/{stats.USERNAME}":
                return {"followers": 1}
            if endpoint.startswith("users/"):
                return [[repository("one")]]
            raise RuntimeError("Language API unavailable")

        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory)
            for name in ("github-stats.svg", "top-languages.svg"):
                (output / name).write_text("last good card")
            with self.assertRaisesRegex(RuntimeError, "Language API unavailable"):
                stats.refresh(output, fetch)
            self.assertEqual([path.read_text() for path in output.iterdir()], ["last good card"] * 2)


if __name__ == "__main__":
    unittest.main()
