"""Beta44 HACS domain-switch and flat-tag payload contract."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "custom_components" / "environment_manager"
CURRENT_VERSION = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))["version"]


def _builder():
    builder_version = ("beta52" if CURRENT_VERSION == "0.6.0b52" else
                       "beta51" if CURRENT_VERSION == "0.6.0b51" else
                       "beta50" if CURRENT_VERSION == "0.6.0b50" else
                       "beta49" if CURRENT_VERSION == "0.6.0b49" else
                       "beta48" if CURRENT_VERSION == "0.6.0b48" else
                       "beta47" if CURRENT_VERSION == "0.6.0b47" else
                       "beta46" if CURRENT_VERSION == "0.6.0b46" else
                       "beta45" if CURRENT_VERSION == "0.6.0b45" else "beta44")
    path = ROOT / "tools" / f"build_{builder_version}_payload.py"
    spec = importlib.util.spec_from_file_location(f"{builder_version}_payload_builder", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_hacs_root_discovery_is_canonical():
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    root_manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    canonical = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))

    assert hacs["content_in_root"] is True
    assert hacs.get("zip_release") is not True
    assert "filename" not in hacs
    assert hacs["hide_default_branch"] is True
    assert root_manifest == canonical
    assert canonical["domain"] == "environment_manager"
    assert canonical["version"] == CURRENT_VERSION


def test_flat_payload_contains_only_integration_root_plus_hacs_metadata():
    module = _builder()
    with tempfile.TemporaryDirectory() as tmp:
        payload = Path(tmp) / "payload"
        module.build_payload(payload)
        assert (payload / "__init__.py").is_file()
        assert (payload / "manifest.json").is_file()
        assert (payload / "services.yaml").is_file()
        assert (payload / "translations").is_dir()
        assert (payload / "frontend").is_dir()
        assert (payload / "brand" / "icon.png").is_file()
        assert (payload / "hacs.json").is_file()
        assert not (payload / "custom_components").exists()
        assert not (payload / "tests").exists()
        assert not (payload / ".github").exists()


def test_normal_hacs_tag_archive_extraction_lands_in_canonical_directory():
    """Mirror HACS download_repository_zip with content.path.remote == ''."""
    module = _builder()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        payload = root / "payload"
        module.build_payload(payload)

        archive = root / "tag.zip"
        outer = "Chreece-HA-Home-Environment-Manager-deadbeef"
        with zipfile.ZipFile(archive, "w") as zf:
            for path in payload.rglob("*"):
                if path.is_file():
                    zf.write(path, f"{outer}/{path.relative_to(payload).as_posix()}")

        destination = root / "config" / "custom_components" / "environment_manager"
        destination.mkdir(parents=True)
        remote = ""
        with zipfile.ZipFile(archive) as zf:
            extractable = []
            for info in zf.filelist:
                filename = "/".join(info.filename.split("/")[1:])
                if filename.startswith(remote) and filename != remote:
                    info.filename = filename.replace(remote, "", 1)
                    if info.filename == "/":
                        continue
                    extractable.append(info)
            assert extractable
            zf.extractall(destination, extractable)

        manifest = json.loads(
            (destination / "manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["domain"] == "environment_manager"
        assert manifest["version"] == CURRENT_VERSION
        assert (destination / "__init__.py").is_file()
        assert not (destination / "custom_components").exists()


def test_beta44_publisher_creates_flat_branch_and_no_zip_release():
    workflow = (
        ROOT / ".github" / "workflows" / "beta44-weather-owned-shades.yml"
    ).read_text(encoding="utf-8")
    assert "python tools/build_beta44_payload.py" in workflow
    assert "git checkout --orphan beta44-payload" in workflow
    assert "git push origin HEAD:refs/heads/beta/v0.6.0b44" in workflow
    assert "gh release create v0.6.0b44" in workflow
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    assert hacs.get("zip_release") is not True
    assert "filename" not in hacs


def test_beta45_publisher_keeps_flat_payload_and_reuses_all_safety_gates():
    if CURRENT_VERSION != "0.6.0b45":
        return
    workflow = (ROOT / ".github/workflows/beta45-generic-roller-release.yml").read_text(
        encoding="utf-8"
    )
    assert "python tools/build_beta45_payload.py" in workflow
    assert "python tools/verify_beta45_generic_shade_ha.py" in workflow
    assert "git checkout --orphan beta45-payload" in workflow
    assert "git push origin HEAD:refs/heads/beta/v0.6.0b45" in workflow
    assert "gh release create v0.6.0b45" in workflow
    assert "needs: [test, hassfest, hacs, home_assistant]" in workflow


def test_beta46_publisher_requires_no_em_or_en_dashes_after_regeneration():
    if CURRENT_VERSION != "0.6.0b46":
        return
    workflow = (ROOT / ".github/workflows/beta46-plain-hyphens-release.yml").read_text(
        encoding="utf-8"
    )
    assert "python tools/build_beta46_payload.py" in workflow
    assert "git checkout --orphan beta46-payload" in workflow
    assert "git push origin HEAD:refs/heads/beta/v0.6.0b46" in workflow
    assert "gh release create v0.6.0b46" in workflow
    assert "needs: [test, hassfest, hacs, home_assistant]" in workflow
    assert "no_typographic_dashes" in workflow


def test_beta47_publisher_validates_sensor_average_regressions_before_release():
    if CURRENT_VERSION != "0.6.0b47":
        return
    workflow = (ROOT / ".github/workflows/beta47-valid-sensor-averages.yml").read_text(
        encoding="utf-8"
    )
    assert "python tools/build_beta47_payload.py" in workflow
    assert "git checkout --orphan beta47-payload" in workflow
    assert "git push origin HEAD:refs/heads/beta/v0.6.0b47" in workflow
    assert "gh release create v0.6.0b47" in workflow
    assert "needs: [test, hassfest, hacs, home_assistant]" in workflow
    assert "github.event_name == 'push'" in workflow
    assert "Generate catalogs and run full regression suite" in workflow
    assert "no_typographic_dashes" in workflow

 
def test_beta48_open_window_alert_publisher_is_flat_and_gated():
    if CURRENT_VERSION != "0.6.0b48":
        return
    workflow = (ROOT/".github/workflows/beta48-away-window-alert.yml").read_text(encoding="utf-8")
    assert "python tools/build_beta48_payload.py" in workflow
    assert "git checkout --orphan beta48-payload" in workflow
    assert "git push origin HEAD:refs/heads/beta/v0.6.0b48" in workflow
    assert "gh release create v0.6.0b48" in workflow
    assert "needs: [test, hassfest, hacs, home_assistant]" in workflow
    assert "python -m pytest -q tests" in workflow
    assert "tests/test_beta48_away_window_alert.py" in workflow


def test_beta49_publisher_requires_all_ha_hacs_and_sensor_regressions():
    if CURRENT_VERSION != "0.6.0b49":
        return
    workflow = (ROOT / ".github/workflows/beta49-presence-dry-fix.yml").read_text(encoding="utf-8")
    assert "python tools/build_beta49_payload.py" in workflow
    assert "tests/test_beta49_numeric_presence_dry_mode.py" in workflow
    assert "git checkout --orphan beta49-payload" in workflow
    assert "git push origin HEAD:refs/heads/beta/v0.6.0b49" in workflow
    assert "gh release create v0.6.0b49" in workflow
    assert "needs: [test, hassfest, hacs, home_assistant]" in workflow
    assert "github.ref == 'refs/heads/feat/beta44-shade-weather-owned-open-announcements-20261025'" in workflow


def test_beta50_publisher_validates_all_climate_presets_before_release():
    if CURRENT_VERSION != "0.6.0b50":
        return
    workflow = (ROOT / ".github/workflows/beta50-effective-climate-presets.yml").read_text(encoding="utf-8")
    assert "python tools/build_beta50_payload.py" in workflow
    assert "tests/test_beta50_active_climate_presets.py" in workflow
    assert "git checkout --orphan beta50-payload" in workflow
    assert "git push origin HEAD:refs/heads/beta/v0.6.0b50" in workflow
    assert "gh release create v0.6.0b50" in workflow
    assert "needs: [test, hassfest, hacs, home_assistant]" in workflow
    assert "refs/heads/feat/beta44-shade-weather-owned-open-announcements-20261025" in workflow


def test_beta51_reboot_away_publisher_is_version_gated_and_flat():
    if CURRENT_VERSION != "0.6.0b51":
        return
    workflow = (ROOT / ".github/workflows/beta51-reboot-away-continuity.yml").read_text(encoding="utf-8")
    assert "python tools/build_beta51_payload.py" in workflow
    assert "tests/test_beta51_presence_reboot_away.py" in workflow
    assert "git checkout --orphan beta51-payload" in workflow
    assert "git push origin HEAD:refs/heads/beta/v0.6.0b51" in workflow
    assert "gh release create v0.6.0b51" in workflow
    assert "needs: [test, hassfest, hacs, home_assistant]" in workflow
    assert "github.ref == 'refs/heads/feat/beta44-shade-weather-owned-open-announcements-20261025'" in workflow


def test_beta52_sleep_source_heating_publisher_is_gated():
    if CURRENT_VERSION != "0.6.0b52":
        return
    workflow = (ROOT / ".github/workflows/beta52-sleep-source-heating.yml").read_text(encoding="utf-8")
    assert "python tools/build_beta52_payload.py" in workflow
    assert "tests/test_beta52_sleep_source_heating.py" in workflow
    assert "git checkout --orphan beta52-payload" in workflow
    assert "git push origin HEAD:refs/heads/beta/v0.6.0b52" in workflow
    assert "gh release create v0.6.0b52" in workflow
    assert "needs: [test, hassfest, hacs, home_assistant]" in workflow
    assert "github.ref == 'refs/heads/feat/beta44-shade-weather-owned-open-announcements-20261025'" in workflow
