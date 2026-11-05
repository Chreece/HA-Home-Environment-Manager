"""Remove only the 130 explicitly reviewed tags older than beta113.

Every deletion is limited by both a fixed name allowlist and its observed Git
object SHA. Beta113, newer tags, every release and every branch are preserved.
Missing reviewed tags permit resuming a partial run. Changed refs, release
references, permission errors and transport errors stop all further deletion.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote
from urllib.request import HTTPRedirectHandler, Request, build_opener


REPOSITORY = "Chreece/HA-Home-Environment-Manager"
API_ROOT = "https://api.github.com"
KEEP_TAG = "v0.6.0b113"
KEEP_COMMIT = "5e71435d849643addc93a4f76c2760d80e861da0"
KEEP_RELEASE_ID = 435121994
KEEP_ASSET_ID = 713187912
KEEP_ASSET_DIGEST = "sha256:d105e2dff9745cd0a5aea4de0579709589648c83a90c5c15f7ca0da5c9b0283a"
EARLIER_STABLE_TAGS = (
    "v0.1.8", "v0.2.0", "v0.2.1", "v0.2.2", "v0.2.4", "v0.2.5",
    "v0.2.6", "v0.2.7", "v0.2.8", "v0.2.9", "v0.2.10", "v0.2.11",
    "v0.2.12", "v0.2.13", "v0.2.14", "v0.3.0", "v0.5.0", "v0.5.1",
)
AUTHORIZED_TAGS = frozenset(EARLIER_STABLE_TAGS) | frozenset(
    f"v0.6.0b{number}" for number in range(1, 113)
)
SHA = re.compile(r"[0-9a-f]{40}\Z")
RELEASE_FIELDS = ("id", "tag_name", "target_commitish", "draft", "prerelease")
ASSET_FIELDS = ("id", "name", "size", "digest", "state")


class CleanupError(RuntimeError):
    """A guard failed; do not attempt further deletions."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CleanupError(message)


def is_older_tag(name: str) -> bool:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?", name)
    if not match:
        return False
    version = tuple(int(match[index]) for index in (1, 2, 3))
    if version != (0, 6, 0):
        return version < (0, 6, 0)
    return match[4] == "a" or (match[4] == "b" and int(match[5]) < 113)


def ref_signature(value: Any) -> dict:
    require(isinstance(value, dict) and isinstance(value.get("object"), dict),
            "Malformed Git reference")
    return {"ref": value.get("ref"), "type": value["object"].get("type"),
            "sha": value["object"].get("sha")}


def release_signature(value: Any) -> dict:
    require(isinstance(value, dict) and isinstance(value.get("assets"), list),
            "Malformed retained release")
    require(all(isinstance(asset, dict) for asset in value["assets"]),
            "Malformed retained release assets")
    result = {field: value.get(field) for field in RELEASE_FIELDS}
    result["assets"] = sorted(
        ({field: asset.get(field) for field in ASSET_FIELDS} for asset in value["assets"]),
        key=lambda item: str(item["id"]),
    )
    return result


class NoRedirect(HTTPRedirectHandler):
    """Never forward the workflow token to a redirected host or repository."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class API:
    """Fixed repository client; DELETE can only address authorized tag names."""

    def __init__(self, token: str):
        require(bool(token), "The workflow token is missing")
        self._token = token
        self._opener = build_opener(NoRedirect())
        self._last_delete: float | None = None

    @staticmethod
    def check_operation(method: str, suffix: str) -> None:
        require(method in ("GET", "DELETE"), "Unsupported API operation")
        require(((method == "GET" and suffix == "") or suffix.startswith("/"))
                and not suffix.startswith("//"), "Invalid repository API path")
        if method == "DELETE":
            prefix = "/git/refs/tags/"
            require(suffix.startswith(prefix), "Only reviewed tag refs can be deleted")
            name = unquote(suffix.removeprefix(prefix))
            require(name in AUTHORIZED_TAGS and suffix == prefix + quote(name, safe=""),
                    "Tag deletion is outside the reviewed allowlist")

    def request(self, method: str, suffix: str, *, missing_ok: bool = False) -> Any:
        self.check_operation(method, suffix)
        if method == "DELETE":
            now = time.monotonic()
            if self._last_delete is not None:
                delay = 1.05 - (now - self._last_delete)
                if delay > 0:
                    time.sleep(delay)
            self._last_delete = time.monotonic()
        request = Request(API_ROOT + "/repos/" + REPOSITORY + suffix, method=method, headers={
            "Authorization": "Bearer " + self._token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "HEM-reviewed-tags-before-beta113",
        })
        try:
            with self._opener.open(request, timeout=30) as response:
                if method == "DELETE":
                    require(response.status == 204, "Unexpected GitHub deletion status")
                    return True
                data = response.read()
        except HTTPError as error:
            if missing_ok and error.code == 404:
                return False if method == "DELETE" else None
            raise CleanupError(f"GitHub returned HTTP {error.code} for {method} {suffix}") from None
        except (URLError, TimeoutError, OSError):
            raise CleanupError(f"GitHub transport failed for {method} {suffix}") from None
        try:
            return json.loads(data)
        except (ValueError, UnicodeDecodeError):
            raise CleanupError(f"Invalid GitHub JSON for {method} {suffix}") from None

    def get(self, suffix: str, *, missing_ok: bool = False) -> Any:
        return self.request("GET", suffix, missing_ok=missing_ok)

    def delete(self, suffix: str) -> bool:
        return self.request("DELETE", suffix, missing_ok=True)


class Cleanup:
    def __init__(self, api: Any, plan: dict, context: dict[str, str]):
        self.api = api
        require(isinstance(plan, dict) and plan.get("schema_version") == 1,
                "Unknown cleanup inventory schema")
        require(plan.get("repository") == REPOSITORY and plan.get("cutoff") == KEEP_TAG,
                "Wrong repository or cutoff in inventory")
        require(context.get("GITHUB_REPOSITORY") == REPOSITORY,
                "Wrong workflow repository")
        require(context.get("GITHUB_REF") == "refs/heads/dev"
                and context.get("GITHUB_EVENT_NAME") == "push",
                "Cleanup requires the reviewed dev push")
        require(context.get("GITHUB_SERVER_URL") == "https://github.com"
                and context.get("GITHUB_API_URL") == API_ROOT,
                "Wrong GitHub host")
        require(bool(SHA.fullmatch(context.get("GITHUB_SHA", ""))),
                "Malformed workflow commit")
        kept = plan.get("retained_tag", {})
        require(kept == {"name": KEEP_TAG, "ref": "refs/tags/" + KEEP_TAG,
                         "type": "commit", "sha": KEEP_COMMIT, "commit": KEEP_COMMIT},
                "Retained beta113 identity changed")
        self.keep_ref = {key: kept[key] for key in ("ref", "type", "sha")}
        self.keep_release = plan.get("retained_release")
        require(self.keep_release == {
            "id": KEEP_RELEASE_ID, "tag_name": KEEP_TAG, "target_commitish": KEEP_COMMIT,
            "draft": False, "prerelease": True,
            "assets": [{"id": KEEP_ASSET_ID, "name": "HA-Home-Environment-Manager-v0.6.0b113.zip",
                        "size": 2689459, "digest": KEEP_ASSET_DIGEST, "state": "uploaded"}],
        }, "Retained beta113 release or asset inventory changed")
        targets = plan.get("delete_tags")
        require(isinstance(targets, list) and len(targets) == len(AUTHORIZED_TAGS),
                "The reviewed inventory must contain exactly 130 tags")
        self.targets = {}
        for item in targets:
            require(isinstance(item, dict), "Malformed deletion inventory entry")
            name = item.get("name")
            require(name in AUTHORIZED_TAGS and name not in self.targets,
                    "Unreviewed or duplicate tag entered the deletion inventory")
            require(item.get("ref") == "refs/tags/" + name
                    and item.get("type") in ("commit", "tag")
                    and bool(SHA.fullmatch(item.get("sha", ""))),
                    "Malformed tag reference in deletion inventory")
            self.targets[name] = {key: item[key] for key in ("ref", "type", "sha")}
        require(set(self.targets) == AUTHORIZED_TAGS, "The reviewed tag inventory is incomplete")
        self.deleted = self.already_absent = 0

    def releases(self) -> list[dict]:
        values, seen = [], set()
        for page in range(1, 101):
            batch = self.api.get(f"/releases?per_page=100&page={page}")
            require(isinstance(batch, list), "Malformed releases response")
            for item in batch:
                require(isinstance(item, dict) and type(item.get("id")) is int
                        and item["id"] not in seen and isinstance(item.get("tag_name"), str),
                        "Malformed or duplicate release")
                values.append(item)
                seen.add(item["id"])
            if len(batch) < 100:
                return values
        raise CleanupError("Release pagination exceeded the review bound")

    def verify_releases(self) -> None:
        releases = self.releases()
        kept = [item for item in releases if item["id"] == KEEP_RELEASE_ID]
        require(len(kept) == 1 and release_signature(kept[0]) == self.keep_release,
                "Retained beta113 release or installation asset changed")
        referenced = sorted({item["tag_name"] for item in releases} & set(self.targets))
        require(not referenced, "A reviewed tag is referenced by a release: " + ", ".join(referenced))

    def peeled_commit(self, ref: dict) -> str:
        obj, seen = ref.get("object"), set()
        for _ in range(16):
            require(isinstance(obj, dict) and bool(SHA.fullmatch(obj.get("sha", ""))),
                    "Malformed retained tag object")
            if obj.get("type") == "commit":
                return obj["sha"]
            require(obj.get("type") == "tag" and obj["sha"] not in seen,
                    "Invalid or cyclic retained tag object")
            seen.add(obj["sha"])
            annotated = self.api.get("/git/tags/" + obj["sha"])
            require(isinstance(annotated, dict) and annotated.get("sha") == obj["sha"],
                    "Retained annotated tag changed")
            obj = annotated.get("object")
        raise CleanupError("Retained tag nesting exceeded the review bound")

    def verify_keep(self) -> None:
        kept = self.api.get("/git/ref/tags/" + KEEP_TAG)
        require(ref_signature(kept) == self.keep_ref and self.peeled_commit(kept) == KEEP_COMMIT,
                "Retained beta113 tag moved or changed")

    def verify_inventory(self) -> set[str]:
        refs = self.api.get("/git/matching-refs/tags/")
        require(isinstance(refs, list), "Malformed tag inventory response")
        names = set()
        for item in refs:
            signature = ref_signature(item)
            ref = signature["ref"]
            require(isinstance(ref, str) and ref.startswith("refs/tags/"),
                    "Non-tag reference in tag inventory")
            name = ref.removeprefix("refs/tags/")
            require(name and name not in names, "Duplicate tag inventory entry")
            names.add(name)
            if name in self.targets:
                require(signature == self.targets[name], "Reviewed tag changed: " + name)
            else:
                require(not is_older_tag(name), "Unreviewed older tag appeared: " + name)
        require(KEEP_TAG in names, "Retained beta113 tag is missing")
        return names

    def delete_tag(self, name: str) -> None:
        require(name in self.targets and name in AUTHORIZED_TAGS,
                "Tag is not authorized for deletion")
        self.verify_releases()
        encoded = quote(name, safe="")
        live = self.api.get("/git/ref/tags/" + encoded, missing_ok=True)
        if live is None:
            self.already_absent += 1
            return
        require(ref_signature(live) == self.targets[name],
                "Reviewed tag changed immediately before deletion: " + name)
        if self.api.delete("/git/refs/tags/" + encoded):
            self.deleted += 1
            print("DELETED_TAG " + name + " " + self.targets[name]["sha"], flush=True)
        else:
            self.already_absent += 1

    def run(self) -> dict:
        repository = self.api.get("")
        require(isinstance(repository, dict) and repository.get("full_name") == REPOSITORY
                and repository.get("default_branch") == "main"
                and repository.get("archived") is False and repository.get("disabled") is False,
                "Repository identity or availability changed")
        self.verify_keep()
        self.verify_releases()
        self.verify_inventory()
        # No write is allowed before all preflight checks pass.
        for index, name in enumerate(sorted(self.targets)):
            if index % 20 == 0:
                self.verify_keep()
                print(json.dumps({"status": "progress", "deleted_tags": self.deleted,
                                  "already_absent_tags": self.already_absent}), flush=True)
            self.delete_tag(name)
        self.verify_keep()
        self.verify_releases()
        remaining = self.verify_inventory()
        require(not remaining.intersection(self.targets), "Reviewed tags remain after cleanup")
        result = {"status": "complete", "deleted_tags": self.deleted,
                  "already_absent_tags": self.already_absent,
                  "remaining_tags": sorted(remaining), "retained_release": KEEP_TAG,
                  "branches": "unchanged", "releases": "unchanged"}
        print(json.dumps(result), flush=True)
        return result


def main() -> int:
    try:
        plan = json.loads(Path(__file__).with_name("inventory.json").read_text(encoding="utf-8"))
        Cleanup(API(os.environ.get("GH_TOKEN", "")), plan, dict(os.environ)).run()
    except (CleanupError, ValueError, OSError) as error:
        print("TAG_CLEANUP_ABORTED: " + str(error), file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
