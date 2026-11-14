"""Checks for the public-facing, practical HEM README and linked illustrations.

This is a documentation check only. It must not import or operate Home Assistant.
"""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
readme = (root / "README.md").read_text(encoding="utf-8")
guide = (root / "docs/advanced-configuration.md").read_text(encoding="utf-8")

required = (
    "## What can HEM do?",
    "## Explore the features",
    "### A complete home dashboard",
    "### Different settings for the home, each room and each device",
    "### Climate control and PID, device by device",
    "### Comfortable when you're home, economical when you're away",
    "### Prepare your environment before you arrive",
    "### Ventilation advice, windows, doors and shading",
    "### Humidity, mold indication and air quality",
    "### Announcements, diagnostics and protection",
    "## See HEM in action",
    "## Getting started",
    "## Installation",
    "## Common questions",
)
for heading in required:
    assert heading in readme, f"Missing practical README section: {heading}"

# Keep the overview timeless. Historical publication details live in Git,
# not in the user-oriented overview.
for pattern in (r"\bversion(?:s|ing)?\b", r"\brelease(?:s)?\b",
                r"\bbeta\b", r"\bpre-release\b", r"\bv\d+\.\d+"):
    assert not re.search(pattern, readme, flags=re.I), pattern

# Prefer ordinary hyphens over typographic long dashes in user-facing prose
# and the visible labels of the shipped README graphics.
text_assets = [
    root / "README.md",
    root / "docs/advanced-configuration.md",
    root / "docs/door-context.md",
    root / "docs/settings-audit.md",
    root / "CONTRIBUTING.md",
    root / ".github/assets/hem-banner.svg",
    root / ".github/assets/hem-logo.svg",
]
image_paths = [
    "docs/images/hem-dashboard-overview.svg",
    "docs/images/hem-room-expanded.svg",
    "docs/images/hem-home-settings.svg",
    "docs/images/hem-room-settings.svg",
    "docs/images/hem-device-settings.svg",
]
assert readme.count('src="docs/images/') == len(image_paths)
for path in image_paths:
    assert f'src="{path}"' in readme, path
    assert (root / path).is_file(), path
    text_assets.append(root / path)
assert (root / "docs/advanced-configuration.md").is_file()
assert (root / "CONTRIBUTING.md").is_file()
for file in text_assets:
    contents = file.read_text(encoding="utf-8")
    assert not any(mark in contents for mark in ("\u2013", "\u2014")), file

# The short guide should link to a separate, preserved deep technical guide.
assert "[detailed configuration guide](docs/advanced-configuration.md)" in readme
for section in ("## Enable device control", "### Independent operating modes",
                "### Prepare for arrival", "## Presence and sleep",
                "## Optional solar shading", "## Mold indication measurement",
                "## Announcements", "## Troubleshooting"):
    assert section in guide, section

print("PASS: HEM user-friendly README, all features, screenshot links, plain hyphens")
