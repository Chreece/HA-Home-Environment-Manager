"""Exercise destructive-operation guards without network access or credentials."""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import unittest
from urllib.parse import unquote


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("hem_tag_cleanup", HERE / "cleanup.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PLAN = json.loads((HERE / "inventory.json").read_text(encoding="utf-8"))
CONTEXT = {
    "GITHUB_REPOSITORY": MODULE.REPOSITORY,
    "GITHUB_REF": "refs/heads/dev",
    "GITHUB_EVENT_NAME": "push",
    "GITHUB_SERVER_URL": "https://github.com",
    "GITHUB_API_URL": MODULE.API_ROOT,
    "GITHUB_SHA": "a" * 40,
}


def git_ref(name, sha, kind="commit"):
    return {"ref": "refs/tags/" + name, "object": {"type": kind, "sha": sha}}


class FakeAPI:
    def __init__(self):
        self.refs = {item["name"]: git_ref(item["name"], item["sha"], item["type"])
                     for item in PLAN["delete_tags"]}
        self.refs[MODULE.KEEP_TAG] = git_ref(MODULE.KEEP_TAG, MODULE.KEEP_COMMIT)
        self.release_items = [deepcopy(PLAN["retained_release"])]
        self.deleted = []
        self.get_calls = []
        self.before_get = None
        self.before_delete = None

    def get(self, suffix, *, missing_ok=False):
        self.get_calls.append(suffix)
        if self.before_get:
            self.before_get(suffix)
        if suffix == "":
            return {"full_name": MODULE.REPOSITORY, "default_branch": "main",
                    "archived": False, "disabled": False}
        if suffix.startswith("/releases?per_page=100&page="):
            page = int(suffix.rsplit("=", 1)[1])
            return deepcopy(self.release_items[(page - 1) * 100:page * 100])
        if suffix == "/git/matching-refs/tags/":
            return deepcopy(list(self.refs.values()))
        if suffix.startswith("/git/ref/tags/"):
            name = unquote(suffix.removeprefix("/git/ref/tags/"))
            if name not in self.refs:
                if missing_ok:
                    return None
                raise MODULE.CleanupError("Missing retained tag")
            return deepcopy(self.refs[name])
        raise AssertionError("Unexpected GET " + suffix)

    def delete(self, suffix):
        MODULE.API.check_operation("DELETE", suffix)
        if self.before_delete:
            self.before_delete(suffix)
        name = unquote(suffix.removeprefix("/git/refs/tags/"))
        if name not in self.refs:
            return False
        self.deleted.append(name)
        del self.refs[name]
        return True


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeAPI()
        self.plan = deepcopy(PLAN)
        self.context = deepcopy(CONTEXT)

    def cleanup(self):
        return MODULE.Cleanup(self.api, self.plan, self.context)

    def run_cleanup(self):
        with redirect_stdout(io.StringIO()):
            return self.cleanup().run()

    def assert_preflight_rejects(self):
        with self.assertRaises(MODULE.CleanupError):
            self.run_cleanup()
        self.assertEqual(self.api.deleted, [])

    def test_deletes_all_130_exact_candidates_and_retains_beta113(self):
        releases = deepcopy(self.api.release_items)
        result = self.run_cleanup()
        self.assertEqual(result["deleted_tags"], 130)
        self.assertEqual(set(self.api.deleted), MODULE.AUTHORIZED_TAGS)
        self.assertEqual(set(self.api.refs), {MODULE.KEEP_TAG})
        self.assertEqual(self.api.release_items, releases)
        self.assertEqual(result["remaining_tags"], [MODULE.KEEP_TAG])
        self.assertTrue(all(not path.startswith("/branches") for path in self.api.get_calls))

    def test_rerun_after_partial_or_completed_cleanup(self):
        first = sorted(MODULE.AUTHORIZED_TAGS)[:70]
        for name in first:
            del self.api.refs[name]
        result = self.run_cleanup()
        self.assertEqual(result["deleted_tags"], 60)
        self.assertEqual(result["already_absent_tags"], 70)
        result = self.run_cleanup()
        self.assertEqual(result["deleted_tags"], 0)
        self.assertEqual(result["already_absent_tags"], 130)

    def test_preserves_newer_beta_stable_and_other_tags_with_releases(self):
        for name in ("v0.6.0b114", "v0.6.0b200", "v0.6.0rc1", "v0.6.0", "v1.0.0", "demo-preview"):
            self.api.refs[name] = git_ref(name, "b" * 40)
            self.api.release_items.append({"id": len(self.api.release_items), "tag_name": name})
        original_newer = set(self.api.refs) - MODULE.AUTHORIZED_TAGS
        self.run_cleanup()
        self.assertEqual(set(self.api.refs), original_newer)

    def test_changed_candidate_in_bulk_inventory_rejects_before_writes(self):
        self.api.refs["v0.6.0b100"]["object"]["sha"] = "b" * 40
        self.assert_preflight_rejects()

    def test_changed_candidate_immediately_before_delete_rejects(self):
        first = sorted(MODULE.AUTHORIZED_TAGS)[0]
        def change(suffix):
            if suffix == "/git/ref/tags/" + first:
                self.api.refs[first]["object"]["sha"] = "c" * 40
        self.api.before_get = change
        self.assert_preflight_rejects()

    def test_candidate_type_changed_rejects(self):
        self.api.refs["v0.6.0b112"]["object"]["type"] = "tag"
        self.assert_preflight_rejects()

    def test_release_referencing_candidate_rejects_before_writes(self):
        self.api.release_items.append({"id": 9999, "tag_name": "v0.6.0b112", "draft": True})
        self.assert_preflight_rejects()

    def test_new_release_reference_during_run_stops_next_deletion(self):
        def appear(suffix):
            if suffix.startswith("/releases?") and self.api.deleted:
                name = sorted(MODULE.AUTHORIZED_TAGS)[1]
                self.api.release_items.append({"id": 9999, "tag_name": name})
                self.api.before_get = None
        self.api.before_get = appear
        with self.assertRaises(MODULE.CleanupError):
            self.run_cleanup()
        self.assertEqual(len(self.api.deleted), 1)

    def test_retained_tag_missing_moved_or_changed_type_rejects(self):
        for mode in ("missing", "moved", "changed_type"):
            with self.subTest(mode=mode):
                self.api = FakeAPI()
                if mode == "missing":
                    del self.api.refs[MODULE.KEEP_TAG]
                elif mode == "moved":
                    self.api.refs[MODULE.KEEP_TAG]["object"]["sha"] = "c" * 40
                else:
                    self.api.refs[MODULE.KEEP_TAG]["object"]["type"] = "tag"
                self.assert_preflight_rejects()

    def test_retained_release_or_asset_changed_rejects(self):
        for mode in ("missing", "commit", "digest"):
            with self.subTest(mode=mode):
                self.api = FakeAPI()
                if mode == "missing":
                    self.api.release_items.clear()
                elif mode == "commit":
                    self.api.release_items[0]["target_commitish"] = "c" * 40
                else:
                    self.api.release_items[0]["assets"][0]["digest"] = "sha256:" + "0" * 64
                self.assert_preflight_rejects()

    def test_extra_unreviewed_older_tag_aborts_without_deleting_it(self):
        self.api.refs["v0.2.3"] = git_ref("v0.2.3", "c" * 40)
        self.assert_preflight_rejects()
        self.assertIn("v0.2.3", self.api.refs)

    def test_modified_inventory_cannot_add_retained_newer_or_branch_targets(self):
        for invalid in ("v0.6.0b113", "v0.6.0b114", "main", "../heads/main"):
            with self.subTest(invalid=invalid):
                self.plan = deepcopy(PLAN)
                self.plan["delete_tags"][0]["name"] = invalid
                self.plan["delete_tags"][0]["ref"] = "refs/tags/" + invalid
                self.assert_preflight_rejects()

    def test_incomplete_duplicate_and_invalid_sha_inventory_reject(self):
        for mode in ("missing", "duplicate", "invalid_sha"):
            with self.subTest(mode=mode):
                self.plan = deepcopy(PLAN)
                if mode == "missing":
                    self.plan["delete_tags"].pop()
                elif mode == "duplicate":
                    self.plan["delete_tags"][0] = deepcopy(self.plan["delete_tags"][1])
                else:
                    self.plan["delete_tags"][0]["sha"] = "invalid"
                self.assert_preflight_rejects()

    def test_wrong_execution_context_rejects(self):
        mutations = {
            "GITHUB_REPOSITORY": "somewhere/else", "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "pull_request", "GITHUB_SERVER_URL": "https://example.com",
            "GITHUB_API_URL": "https://example.com", "GITHUB_SHA": "invalid",
        }
        for key, value in mutations.items():
            with self.subTest(key=key):
                self.context = deepcopy(CONTEXT)
                self.context[key] = value
                self.assert_preflight_rejects()

    def test_permissions_failure_stops_without_retry_or_later_delete(self):
        attempts = []
        def reject(suffix):
            attempts.append(suffix)
            raise MODULE.CleanupError("GitHub returned HTTP 403")
        self.api.before_delete = reject
        self.assert_preflight_rejects()
        self.assertEqual(len(attempts), 1)

    def test_api_will_not_delete_branches_releases_or_surviving_tags(self):
        invalid = (
            "/git/refs/heads/main", "/git/refs/heads/dev", "/releases/435121994",
            "/git/refs/tags/v0.6.0b113", "/git/refs/tags/v0.6.0b114",
            "/git/refs/tags/v0.6.0b1?unexpected=yes", "/git/refs/tags/../heads/main",
            "/git/refs/tags/%2e%2e%2fheads%2fmain",
        )
        for suffix in invalid:
            with self.subTest(suffix=suffix), self.assertRaises(MODULE.CleanupError):
                MODULE.API.check_operation("DELETE", suffix)
        for name in MODULE.AUTHORIZED_TAGS:
            MODULE.API.check_operation("DELETE", "/git/refs/tags/" + name)

    def test_releases_are_checked_across_pagination(self):
        self.api.release_items.extend({"id": number, "tag_name": "v1.0.0"} for number in range(1, 101))
        self.api.release_items.append({"id": 1001, "tag_name": "v0.6.0b112"})
        self.assert_preflight_rejects()
        self.assertIn("/releases?per_page=100&page=2", self.api.get_calls)


if __name__ == "__main__":
    unittest.main(verbosity=2)
