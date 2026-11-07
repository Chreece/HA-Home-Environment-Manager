"""Offline tests for exact-commit publication and preservation of release history."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from io import BytesIO
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch, Mock
from urllib.error import HTTPError
from urllib.parse import unquote
from urllib.request import Request
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("hem_publisher", ROOT / ".github/scripts/publish_release.py")
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)
VERSION = "0.6.1b1"


def release(version, *, identifier=1, draft=False, prerelease=True):
    return {"id": identifier, "tag_name": "v" + version, "draft": draft,
            "prerelease": prerelease, "published_at": None if draft else "2026-11-05T00:00:00Z"}


class FakeGitHub:
    """A release transport, with no credentials or network access."""
    def __init__(self, sha, *, initial=None, corrupt_digest=False, wrong_tag=False):
        self.sha = sha
        self.items = deepcopy(initial if initial is not None else [release("0.6.0b122")])
        self.tags = {item["tag_name"]: "1" * 40 for item in self.items if not item["draft"]}
        self.events = []
        self.data = b""
        self.corrupt_digest = corrupt_digest
        self.wrong_tag = wrong_tag
        self.published = False

    def releases(self):
        return deepcopy(self.items)

    def request(self, method, path, data=None, **kwargs):
        self.events.append((method, path))
        if method == "GET" and path == "/git/ref/heads/main":
            return {"object": {"type": "commit", "sha": self.sha}}
        if method == "GET" and path.startswith("/git/ref/tags/"):
            sha = self.tags.get(unquote(path.removeprefix("/git/ref/tags/")))
            return {"object": {"type": "commit", "sha": sha}} if sha else None
        if method == "POST" and path == "/releases":
            assert data.get("make_latest") == "legacy", data
            self.created = {**data, "id": 2, "assets": [], "published_at": None}
            self.items.append(self.created)
            return deepcopy(self.created)
        if method == "POST" and path.startswith("/releases/2/assets?"):
            self.data = data
            name = "environment_manager.zip"
            self.asset = {
                "id": 7, "name": name, "state": "uploaded", "size": len(data),
                "digest": "sha256:" + ("0" * 64 if self.corrupt_digest else hashlib.sha256(data).hexdigest()),
                "browser_download_url": f"https://github.com/{publisher.REPOSITORY}/releases/download/v{VERSION}/{name}",
            }
            self.created["assets"] = [self.asset]
            return deepcopy(self.asset)
        if method == "GET" and path == "/releases/2":
            return deepcopy(self.created)
        if method == "GET" and path == "/releases/assets/7":
            return deepcopy(self.asset)
        if method == "PATCH" and path == "/releases/2":
            assert data.get("make_latest") == "legacy", data
            self.created.update(data, published_at="2026-11-05T01:00:00Z")
            self.published = True
            self.tags[self.created["tag_name"]] = "0" * 40 if self.wrong_tag else self.sha
            return deepcopy(self.created)
        raise AssertionError(f"Unexpected offline API operation: {method} {path}")


class PublishReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.repo = Path(cls.directory.name)
        cls.files = {publisher.SOURCE + name: b"fixture\n" for name in publisher.REQUIRED}
        cls.files.update({
            publisher.SOURCE + "manifest.json": json.dumps({"domain": "environment_manager", "version": VERSION}).encode(),
            "manifest.json": b'{"domain":"wrong_root_decoy","version":"0.0.1"}',
            "README.md": b"integration documentation\n",
            ".github/releases/v" + VERSION + ".md": b"Beta fixture notes\n",
            ".github/tests/ignored.py": b"excluded\n", "tests/ignored.py": b"excluded\n",
            "dist/old.zip": b"excluded\n", "hacs.json": b"{}\n",
            "nested/__pycache__/ignored.py": b"excluded\n", "ignored.pyc": b"excluded\n",
        })
        for name, content in cls.files.items():
            path = cls.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        def git(*args):
            return subprocess.check_output(["git", "-C", str(cls.repo), *args], stderr=subprocess.PIPE)
        git("init", "-q", "-b", "main")
        git("add", "--all")
        git("-c", "user.name=Offline fixture", "-c", "user.email=fixture@example.invalid",
            "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-qm", "Fixture")
        cls.sha = git("rev-parse", "HEAD").decode().strip()

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_package_uses_deterministic_validated_blobs_and_exact_exclusions(self):
        first = publisher.package(self.repo, self.sha, VERSION)
        (self.repo / "README.md").write_text("unvalidated working-copy edit")
        (self.repo / "untracked.py").write_text("untracked input")
        second = publisher.package(self.repo, self.sha, VERSION)
        self.assertEqual(first, second)
        with ZipFile(BytesIO(first)) as archive:
            expected = {publisher.PREFIX + name for name in (*publisher.REQUIRED, "manifest.json")}
            self.assertEqual(set(archive.namelist()), expected)
            self.assertEqual(archive.read("manifest.json"), self.files[publisher.SOURCE + "manifest.json"])
            self.assertNotIn("README.md", archive.namelist())
            self.assertNotIn(publisher.SOURCE + "manifest.json", archive.namelist())
        with self.assertRaises(publisher.ReleaseError):
            publisher.inspect_zip(first, "0.6.1b2")

    def test_numeric_beta_order_and_stable_version_order(self):
        self.assertLess(publisher.version_key("0.6.0b9"), publisher.version_key("0.6.0b122"))
        self.assertLess(publisher.version_key("0.6.0b122"), publisher.version_key(VERSION))
        self.assertLess(publisher.version_key("0.6.0"), publisher.version_key(VERSION))
        self.assertLess(publisher.version_key(VERSION), publisher.version_key("0.6.1"))
        self.assertLess(publisher.version_key("0.6.0b999"), publisher.version_key("0.7.0b1"))
        self.assertIsNone(publisher.version_key("0.6.0rc1"))

    def test_release_history_still_rejects_newer_and_unknown_published_versions(self):
        items = [release("0.6.0b122"), release(VERSION, identifier=2),
                 release("0.6.0", identifier=3, prerelease=False),
                 release("0.6.0b121", identifier=4, draft=True),
                 release("work-in-progress", identifier=5, draft=True)]
        original = deepcopy(items)
        publisher.validate_release_history(items, VERSION)
        self.assertEqual(items, original)
        for unexpected in (release("0.6.1b2"), release("0.6.1", prerelease=False),
                           release("0.6.1b2", draft=True), release("unknown")):
            with self.subTest(tag=unexpected["tag_name"]), self.assertRaises(publisher.ReleaseError):
                publisher.validate_release_history([unexpected], VERSION)
        with self.assertRaises(publisher.ReleaseError):
            publisher.is_new_version([release(VERSION, draft=True)], VERSION)

    def test_existing_published_version_is_a_strict_no_write(self):
        api = FakeGitHub(self.sha, initial=[release(VERSION)])
        publisher.publish(api, self.repo, self.sha)
        self.assertFalse(any(method != "GET" for method, path in api.events))
        self.assertEqual(len(api.items), 1)

    def test_matching_successful_main_run_is_required(self):
        run = {"name": publisher.WORKFLOW, "workflow_id": 8, "event": "push",
               "head_branch": "main", "status": "completed", "conclusion": "success",
               "head_sha": self.sha, "repository": {"full_name": publisher.REPOSITORY},
               "head_repository": {"full_name": publisher.REPOSITORY}}
        publisher.validate_run(run, self.sha, 8)
        for change in ({"conclusion": "failure"}, {"event": "pull_request"},
                       {"head_branch": "dev"}, {"workflow_id": 9}, {"head_sha": "0" * 40},
                       {"head_repository": {"full_name": "fork/hem"}}):
            with self.subTest(change=change), self.assertRaises(publisher.ReleaseError):
                publisher.validate_run({**run, **change}, self.sha, 8)
        with self.assertRaises(publisher.ReleaseError):
            publisher.main_head(FakeGitHub("0" * 40), self.sha)

    def test_publication_preserves_all_older_releases_tags_and_assets(self):
        older = [release("0.6.0b121", identifier=11), release("0.6.0b122", identifier=12),
                 release("0.6.0", identifier=13, prerelease=False),
                 release("0.6.0b120", identifier=14, draft=True),
                 release("work-in-progress", identifier=15, draft=True)]
        for item in older:
            item.update(body="Existing release notes for " + item["tag_name"], assets=[{
                "id": 100 + item["id"], "name": item["tag_name"] + ".zip", "size": 123,
            }])
        api = FakeGitHub(self.sha, initial=older)
        api.tags["v0.5.0b1"] = "3" * 40  # A tag without a release also remains intact.
        original_tags = deepcopy(api.tags)
        def download(*args):
            api.events.append(("DOWNLOAD", "verified"))
            return api.data
        with patch.object(publisher, "download_asset", side_effect=download):
            publisher.publish(api, self.repo, self.sha)
        self.assertTrue(api.published)
        self.assertEqual(api.items[:-1], older)
        self.assertEqual(api.items[-1]["tag_name"], "v" + VERSION)
        self.assertEqual(api.tags, {**original_tags, "v" + VERSION: self.sha})
        self.assertIn(("DOWNLOAD", "verified"), api.events)
        self.assertFalse(any(method == "DELETE" for method, path in api.events))
        self.assertEqual([(method, path) for method, path in api.events
                          if method not in ("GET", "DOWNLOAD")], [
            ("POST", "/releases"),
            ("POST", "/releases/2/assets?name=environment_manager.zip"),
            ("PATCH", "/releases/2"),
        ])

    def test_newer_release_during_upload_still_stops_publication(self):
        api = FakeGitHub(self.sha)
        original = deepcopy(api.items)
        api.releases = lambda: deepcopy(api.items) + (
            [release("0.6.1b2", identifier=9)] if api.data else [])
        with patch.object(publisher, "download_asset") as download, self.assertRaises(publisher.ReleaseError):
            publisher.publish(api, self.repo, self.sha)
        download.assert_not_called()
        self.assertFalse(api.published)
        self.assertEqual(api.items[:-1], original)
        self.assertFalse(any(method in ("PATCH", "DELETE") for method, path in api.events))

    def test_verification_failures_preserve_old_release(self):
        for failure in ("server_digest", "tag", "download"):
            api = FakeGitHub(self.sha, corrupt_digest=failure == "server_digest", wrong_tag=failure == "tag")
            with self.subTest(failure=failure), patch.object(
                publisher, "download_asset", side_effect=lambda *args: b"bad" if failure == "download" else api.data
            ), self.assertRaises(publisher.ReleaseError):
                publisher.publish(api, self.repo, self.sha)
            self.assertTrue(any(item["tag_name"] == "v0.6.0b122" for item in api.items))
            self.assertFalse(any(method == "DELETE" for method, path in api.events))
            if failure == "server_digest":
                self.assertFalse(api.published)

    def test_authenticated_transport_rejects_release_asset_and_tag_deletion(self):
        with patch.object(publisher, "build_opener") as opener:
            api = publisher.GitHub("offline-test-token")
        for method in ("DELETE", "delete"):
            for path in ("/releases/1", "/releases/assets/7", "/git/refs/tags/v0.6.0b122"):
                with self.subTest(method=method, path=path), self.assertRaises(publisher.ReleaseError):
                    api.request(method, path)
        opener.return_value.open.assert_not_called()

    def test_asset_download_retries_without_authorization(self):
        name = "asset.zip"
        url = f"https://github.com/{publisher.REPOSITORY}/releases/download/v{VERSION}/{name}"
        opener = Mock()
        opener.open.side_effect = [HTTPError(url, 404, "Not ready", {}, None), BytesIO(b"zip")]
        with patch.object(publisher, "build_opener", return_value=opener), patch.object(publisher, "sleep") as sleep:
            self.assertEqual(publisher.download_asset({"browser_download_url": url}, "v" + VERSION, name, 3), b"zip")
        self.assertEqual(sleep.call_args.args, (2,))
        for call in opener.open.call_args_list:
            self.assertFalse(call.args[0].has_header("Authorization"))
        request = Request(url, headers={"User-Agent": "offline"})
        redirected = publisher.AssetRedirect().redirect_request(
            request, None, 302, "Found", {}, "https://release-assets.githubusercontent.com/asset")
        self.assertFalse(redirected.has_header("Authorization"))
        self.assertIsNone(publisher.NoRedirect().redirect_request(request, None, 302, "Found", {}, "https://example.com"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
