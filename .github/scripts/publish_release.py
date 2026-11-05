"""Publish only a newly versioned, validated main beta; retain tags on cleanup.

Authenticated requests never follow redirects. Asset downloads are separate,
unauthenticated HTTPS requests. Any failure before full publication verification
leaves older releases intact; an interrupted draft requires explicit review.
"""
from __future__ import annotations

import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from time import sleep
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


REPOSITORY = "Chreece/HA-Home-Environment-Manager"
WORKFLOW = "Validate Home Environment Manager"
PREFIX = "custom_components/environment_manager/"
VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:b(0|[1-9]\d*))?")
REQUIRED = (
    "__init__.py", "device_faults.py", "equipment_resume.py", "pid_review.py",
    "equipment_power_switch.py", "pid_passive.py", "pid_calibration.py",
    "equipment_runtime.py", "equipment_setpoint_sequence.py", "equipment_pid_safety.py",
    "advanced_comfort.py", "shade_cooling.py", "switch.py", "button.py", "climate.py",
    "equipment_name_catalog.py", "equipment_labels.json", "equipment_window.py",
    "climate_arbitration.py", "pid_phase.py", "pid_restart.py", "equipment_status.py",
    "equipment_battery.py", "room_ventilation.py", "messages.py", "select.py",
    "number.py", "device_controls.py", "translations/el.json",
    "frontend/air-quality-advisor-card.js",
)


class ReleaseError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise ReleaseError(message)


def version_key(value):
    match = VERSION.fullmatch(value.removeprefix("v")) if isinstance(value, str) else None
    if match is None:
        return None
    major, minor, patch, beta = match.groups()
    return (int(major), int(minor), int(patch), 1 if beta is None else 0,
            int(beta) if beta is not None else 0)


def cleanup_candidates(releases, version):
    """Never delete drafts, stable releases, unknown tags, or a newer beta."""
    target = version_key(version)
    require(target is not None and target[3] == 0, "A canonical beta version is required")
    candidates = []
    for release in releases:
        key = version_key(release.get("tag_name"))
        if key is None:
            require(release.get("draft") is True,
                    "An unrecognized published version requires manual review")
            continue
        require(key <= target, "A newer release exists; refusing publication or cleanup")
        if (key < target and key[3] == 0 and release.get("draft") is False
                and release.get("prerelease") is True and release.get("published_at")):
            candidates.append(release)
    return sorted(candidates, key=lambda item: version_key(item["tag_name"]))


def is_new_version(releases, version):
    matching = [release for release in releases if release.get("tag_name") == "v" + version]
    if any(release.get("draft") is False for release in matching):
        return False  # Published versions are immutable to this publisher.
    require(not matching, "A draft for this version already exists; review it before retrying")
    cleanup_candidates(releases, version)
    return True


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


def included(name):
    # Keep this selection identical to the canonical validation package.
    return not (name.startswith((".github/", "tests/", "dist/")) or name == "hacs.json"
                or "__pycache__" in name or name.endswith((".pyc", ".pyo")))


def inspect_zip(data, version):
    with ZipFile(BytesIO(data)) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), "Duplicate archive paths")
        require(all(name.startswith(PREFIX) and included(name[len(PREFIX):])
                    and ".." not in PurePosixPath(name).parts for name in names),
                "Unexpected archive layout")
        require(archive.testzip() is None, "ZIP integrity check failed")
        manifest = json.loads(archive.read(PREFIX + "manifest.json"))
        require(manifest.get("domain") == "environment_manager"
                and manifest.get("version") == version, "ZIP manifest mismatch")
        require(all(PREFIX + name in names for name in REQUIRED), "Required integration files missing")
    return names


def package(repo, sha, version):
    """Use validated Git blobs, ignoring untracked files and working-copy edits."""
    entries = git(repo, "ls-tree", "-r", "-z", "--full-tree", sha).split(b"\0")
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=8) as archive:
        for entry in sorted(filter(None, entries), key=lambda row: row.split(b"\t", 1)[1]):
            metadata, raw_name = entry.split(b"\t", 1)
            mode, kind, oid = metadata.decode("ascii").split()
            name = raw_name.decode("utf-8")
            if not included(name):
                continue
            require(kind == "blob" and mode in ("100644", "100755"),
                    "Non-regular tracked file cannot enter the integration ZIP")
            info = ZipInfo(PREFIX + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = int(mode, 8) << 16
            archive.writestr(info, git(repo, "cat-file", "blob", oid),
                             compress_type=ZIP_DEFLATED, compresslevel=8)
    data = output.getvalue()
    inspect_zip(data, version)
    return data


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class AssetRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url = urlsplit(newurl)
        require(url.scheme == "https" and (url.hostname == "github.com"
                or (url.hostname or "").endswith(".githubusercontent.com")),
                "Unexpected release download redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class GitHub:
    def __init__(self, token):
        require(bool(token), "GitHub Actions token is missing")
        self._token = token
        self._opener = build_opener(NoRedirect())

    def request(self, method, path, data=None, *, upload=False, missing=False):
        require(path.startswith("/") and not path.startswith("//"), "Invalid GitHub API path")
        host = "uploads.github.com" if upload else "api.github.com"
        payload = data if upload else json.dumps(data).encode() if data is not None else None
        request = Request("https://" + host + "/repos/" + REPOSITORY + path,
                          data=payload, method=method, headers={
            "Authorization": "Bearer " + self._token,
            "Accept": "application/vnd.github+json", "User-Agent": "hem-beta-publisher",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/zip" if upload else "application/json",
        })
        try:
            with self._opener.open(request, timeout=30) as response:
                content = response.read()
                return json.loads(content) if content else None
        except HTTPError as error:
            if missing and error.code == 404:
                return None
            raise ReleaseError(f"GitHub {method} {path.split('?')[0]} returned HTTP {error.code}") from None

    def releases(self):
        result = []
        for page in range(1, 101):
            batch = self.request("GET", f"/releases?per_page=100&page={page}")
            require(isinstance(batch, list), "Unexpected releases response")
            result.extend(batch)
            if len(batch) < 100:
                return result
        raise ReleaseError("Release pagination limit reached")


def validate_run(run, sha, workflow_id):
    require(run.get("name") == WORKFLOW and run.get("workflow_id") == workflow_id
            and run.get("event") == "push" and run.get("head_branch") == "main"
            and run.get("status") == "completed" and run.get("conclusion") == "success"
            and run.get("head_sha") == sha
            and run.get("repository", {}).get("full_name") == REPOSITORY
            and run.get("head_repository", {}).get("full_name") == REPOSITORY,
            "Only the successful canonical main validation run may publish")


def main_head(api, sha):
    ref = api.request("GET", "/git/ref/heads/main")
    require(ref.get("object", {}).get("type") == "commit"
            and ref["object"].get("sha") == sha,
            "Main has moved; this validation commit is no longer publishable")


def tag_commit(api, tag):
    ref = api.request("GET", "/git/ref/tags/" + quote(tag, safe=""), missing=True)
    if ref is None:
        return None
    obj = ref.get("object", {})
    for _ in range(6):
        if obj.get("type") == "commit":
            return obj.get("sha")
        require(obj.get("type") == "tag", "Unexpected tag object")
        obj = api.request("GET", "/git/tags/" + obj["sha"]).get("object", {})
    raise ReleaseError("Tag nesting limit reached")


def verified_asset(api, release_id, tag, sha, name, digest, size, *, published):
    release = api.request("GET", f"/releases/{release_id}")
    require(release.get("tag_name") == tag and release.get("draft") is (not published)
            and release.get("prerelease") is True
            and release.get("target_commitish") == sha, "Release identity or publication state changed")
    require(not published or bool(release.get("published_at")), "Release is not published")
    assets = release.get("assets", [])
    require(len(assets) == 1 and assets[0].get("name") == name, "Unexpected release assets")
    asset = api.request("GET", f"/releases/assets/{assets[0]['id']}")
    require(asset.get("name") == name and asset.get("state") == "uploaded"
            and asset.get("size") == size and asset.get("digest") == "sha256:" + digest,
            "Uploaded asset size or server SHA256 does not match")
    if published:
        require(tag_commit(api, tag) == sha, "Published tag does not match validated commit")
    return asset


def download_asset(asset, tag, name, size):
    expected = f"https://github.com/{REPOSITORY}/releases/download/{tag}/{name}"
    require(asset.get("browser_download_url") == expected, "Unexpected published download URL")
    # No Authorization header or authenticated opener is used for any hop.
    request = Request(expected, headers={"User-Agent": "hem-beta-verifier"})
    for attempt in range(5):
        try:
            with build_opener(AssetRedirect()).open(request, timeout=30) as response:
                data = response.read(size + 1)
            break
        except HTTPError as error:
            if attempt == 4 or error.code not in (404, 429, 500, 502, 503, 504):
                raise ReleaseError(f"Published asset download returned HTTP {error.code}") from None
            sleep(2 * (attempt + 1))
    require(len(data) == size, "Downloaded asset size mismatch")
    return data


def publish(api, repo, sha):
    manifest = json.loads(git(repo, "show", sha + ":manifest.json"))
    version = manifest.get("version")
    key = version_key(version)
    require(manifest.get("domain") == "environment_manager", "Unexpected integration domain")
    if key is None or key[3] != 0 or version.startswith("v"):
        print("No canonical beta version to publish")
        return
    releases = api.releases()
    if not is_new_version(releases, version):
        print("Already published; no changes:", "v" + version)
        return
    tag = "v" + version
    notes = git(repo, "show", sha + f":.github/releases/{tag}.md").decode("utf-8")
    require(bool(notes.strip()), "Matching release notes are empty")
    require(tag_commit(api, tag) in (None, sha), "Existing tag points to a different commit")
    data = package(repo, sha, version)
    digest = hashlib.sha256(data).hexdigest()
    name = "HA-Home-Environment-Manager-" + tag + ".zip"
    main_head(api, sha)
    draft = api.request("POST", "/releases", {
        "tag_name": tag, "target_commitish": sha, "name": tag, "body": notes,
        "draft": True, "prerelease": True, "make_latest": "false",
    })
    release_id = draft["id"]
    api.request("POST", f"/releases/{release_id}/assets?name=" + quote(name, safe=""),
                data, upload=True)
    verified_asset(api, release_id, tag, sha, name, digest, len(data), published=False)
    main_head(api, sha)
    cleanup_candidates(api.releases(), version)
    api.request("PATCH", f"/releases/{release_id}",
                {"draft": False, "prerelease": True, "make_latest": "false"})
    asset = verified_asset(api, release_id, tag, sha, name, digest, len(data), published=True)
    downloaded = download_asset(asset, tag, name, len(data))
    require(hashlib.sha256(downloaded).hexdigest() == digest, "Published download SHA256 mismatch")
    inspect_zip(downloaded, version)
    print("Verified published beta:", tag, sha, "SHA256", digest)
    # Every deletion is scoped to a freshly checked older, published beta.
    # The tag endpoint is read-only throughout this script.
    for old in cleanup_candidates(api.releases(), version):
        main_head(api, sha)
        verified_asset(api, release_id, tag, sha, name, digest, len(data), published=True)
        current = cleanup_candidates(api.releases(), version)
        require(any(item["id"] == old["id"] and item["tag_name"] == old["tag_name"]
                    for item in current), "Older release changed before cleanup")
        api.request("DELETE", f"/releases/{old['id']}")
        print("Retired older beta release; tag retained:", old["tag_name"])


def main():
    require(os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("GITHUB_REPOSITORY") == REPOSITORY
            and os.environ.get("GITHUB_EVENT_NAME") == "workflow_run",
            "Publisher runs only for the canonical GitHub Actions workflow_run event")
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    require(event.get("repository", {}).get("full_name") == REPOSITORY
            and event.get("action") == "completed", "Unexpected workflow event")
    trigger = event["workflow_run"]
    sha, run_id = trigger.get("head_sha"), trigger.get("id")
    require(isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha)
            and type(run_id) is int, "Invalid validation run identity")
    api = GitHub(os.environ.get("GITHUB_TOKEN"))
    workflow = api.request("GET", "/actions/workflows/validate.yml")
    require(workflow.get("name") == WORKFLOW and workflow.get("path") == ".github/workflows/validate.yml",
            "Unexpected validation workflow")
    validate_run(trigger, sha, workflow["id"])
    validate_run(api.request("GET", f"/actions/runs/{run_id}"), sha, workflow["id"])
    repo = Path(__file__).resolve().parents[2]
    require(git(repo, "rev-parse", "HEAD").decode().strip() == sha, "Checkout differs from validated commit")
    require(not git(repo, "status", "--porcelain", "--untracked-files=no"), "Tracked checkout has modifications")
    main_head(api, sha)
    publish(api, repo, sha)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Do not print urllib exceptions, response bodies, headers or tokens.
        message = str(error) if isinstance(error, ReleaseError) else type(error).__name__
        print("::error::Beta publication stopped: " + message, file=sys.stderr)
        sys.exit(1)
