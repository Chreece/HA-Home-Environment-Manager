"""Validate complete localized HEM README pages, navigation, assets and examples."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "README.md").read_text(encoding="utf-8")
LOCALES = {p.stem for p in
           (ROOT / "custom_components/environment_manager/translations").glob("*.json")}
PAGES = ROOT / "docs/i18n"
assert len(LOCALES) == 38 and "en" in LOCALES
assert SOURCE.count('src=".github/assets/hem-banner.svg"') == 1
assert SOURCE.count('src=".github/assets/ko-fi-banner.svg"') == 1
assert SOURCE.index('src=".github/assets/hem-banner.svg"') < SOURCE.index(
    'src=".github/assets/ko-fi-banner.svg"')
assert SOURCE.count('href="https://ko-fi.com/chreece"') == 1
assert SOURCE.count("<!-- HEM-LANGUAGE-SELECTOR-START -->") == 1
assert SOURCE.count("<!-- HEM-LANGUAGE-SELECTOR-END -->") == 1
for code in LOCALES - {"en"}:
    assert f'docs/i18n/README.{code}.md' in SOURCE, code

expected_files = {f"README.{code}.md" for code in LOCALES - {"en"}}
actual_files = {p.name for p in PAGES.glob("README.*.md")}
assert expected_files == actual_files, (expected_files - actual_files,
                                        actual_files - expected_files)

strip_nav = lambda data: re.sub(
    r"<!-- HEM-LANGUAGE-SELECTOR-START -->.*?"
    r"<!-- HEM-LANGUAGE-SELECTOR-END -->", "", data, flags=re.S)
english = strip_nav(SOURCE)
english_links = re.findall(r"\]\(([^)]+)\)", english)
yaml = re.findall(r"~~~yaml\n(.*?)\n~~~", english, flags=re.S)
headings = re.findall(r"^#{1,6} ", english, flags=re.M)
original_anchors = re.findall(r"\]\(#([^)]+)\)", english)

for path in sorted(PAGES.glob("README.*.md")):
    code = path.stem.split(".", 1)[1]
    page = path.read_text(encoding="utf-8")
    assert len(page) >= 0.32 * len(english), path
    assert page.count("<!-- HEM-LANGUAGE-SELECTOR-START -->") == 1, path
    assert page.count("<!-- HEM-LANGUAGE-SELECTOR-END -->") == 1, path
    assert '<a href="../../README.md">English</a>' in page, path
    for other in LOCALES - {code, "en"}:
        assert f'href="README.{other}.md"' in page, (path, other)
    assert page.index('src="../../.github/assets/hem-banner.svg"') < page.index(
        'src="../../.github/assets/ko-fi-banner.svg"'), path
    assert 'href="https://ko-fi.com/chreece"' in page, path
    assert yaml == re.findall(r"~~~yaml\n(.*?)\n~~~", page, flags=re.S), path
    assert len(re.findall(r"^#{1,6} ", page, flags=re.M)) == len(headings), path
    for anchor in original_anchors:
        assert f'<a id="{anchor}"></a>' in page, (path, anchor)
    localized_links = re.findall(r"\]\(([^)]+)\)", strip_nav(page))
    expected_links = [link if link.startswith(("#", "http:", "https:"))
                      else "../../" + link for link in english_links]
    assert localized_links == expected_links, (path, "changed Markdown link")
    for target in re.findall(r'(?:(?:src|href)=")([^"]+)', page) + localized_links:
        if target.startswith(("#", "http:", "https:", "mailto:", "data:")):
            continue
        assert (path.parent / target).exists(), (path, target)
    assert not re.search(r"HEMLITERAL|🟪[0-9]{4}🟪", page), path

print("PASS: English default, Ko-fi under HEM banner, complete 38-language links, "
      "37 localized READMEs, preserved examples, screenshots and local links")
