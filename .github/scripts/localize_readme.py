#!/usr/bin/env python3
"""Generate the full localized HEM README for every supported UI language.

English stays at README.md. Protect inline code, URLs, images, HTML and YAML
from machine translation. All outputs must validate before files are written.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCALE_DIR = ROOT / "custom_components/environment_manager/translations"
OUTPUT_DIR = ROOT / "docs/i18n"
LANGUAGES = {
    "ar": "العربية", "bg": "Български", "bn": "বাংলা",
    "cs": "Čeština", "da": "Dansk", "de": "Deutsch",
    "el": "Ελληνικά", "en": "English", "es": "Español",
    "fa": "فارسی", "fi": "Suomi", "fr": "Français",
    "he": "עברית", "hi": "हिन्दी", "hr": "Hrvatski",
    "hu": "Magyar", "id": "Bahasa Indonesia",
    "it": "Italiano", "ja": "日本語", "ko": "한국어",
    "nb": "Norsk bokmål", "nl": "Nederlands",
    "pl": "Polski", "pt": "Português",
    "pt-BR": "Português (Brasil)", "ro": "Română",
    "ru": "Русский", "sk": "Slovenčina",
    "sr": "Српски", "sv": "Svenska", "ta": "தமிழ்",
    "th": "ไทย", "tr": "Türkçe", "uk": "Українська",
    "ur": "اردو", "vi": "Tiếng Việt",
    "zh-Hans": "简体中文", "zh-Hant": "繁體中文",
}
GOOGLE_CODES = {"nb": "no", "pt": "pt-PT", "pt-BR": "pt",
                "zh-Hans": "zh-CN", "zh-Hant": "zh-TW"}
NAV_PATTERN = re.compile(
    r"<!-- HEM-LANGUAGE-SELECTOR-START -->.*?"
    r"<!-- HEM-LANGUAGE-SELECTOR-END -->", re.S
)
LITERAL_PATTERN = re.compile(r"!\[[^\]]*\]\([^)]+\)|\]\([^)]+\)|\x60[^\x60]+\x60")
TABLE_DIVIDER = re.compile(r"^:?-{3,}:?$")
LIST_PREFIX = re.compile(r"^(\s*(?:(?:#{1,6}|[-*]|\d+\.)\s+))(.*)$")
BATCH_MARKER = re.compile(r"__HEMSEG([0-9]{4})__")
SESSION_LAST = 0.0


def navigation(selected: str) -> str:
    values = []
    for code, name in LANGUAGES.items():
        if code == selected:
            values.append(f"<strong>{name} (default)</strong>" if code == "en"
                          else f"<strong>{name}</strong>")
        else:
            link = ("../../README.md" if code == "en" else
                    f"README.{code}.md" if selected != "en" else
                    f"docs/i18n/README.{code}.md")
            values.append(f'<a href="{link}">{name}</a>')
    return ("<!-- HEM-LANGUAGE-SELECTOR-START -->\n"
            '<p align="center">\n  ' + " · ".join(values) + "\n</p>\n"
            "<!-- HEM-LANGUAGE-SELECTOR-END -->")


def request_translation(phrase: str, target: str) -> str:
    global SESSION_LAST
    if not phrase.strip():
        return phrase
    params = urllib.parse.urlencode({
        "client": "gtx", "sl": "en",
        "tl": GOOGLE_CODES.get(target, target), "dt": "t",
        "q": phrase,
    })
    url = "https://translate.googleapis.com/translate_a/single?" + params
    if len(url) > 12000:
        raise ValueError(f"Translation URL too long: {len(url)}")
    for attempt in range(8):
        try:
            wait = max(0, 0.85 - (time.monotonic() - SESSION_LAST))
            if wait:
                time.sleep(wait)
            request = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(request, timeout=35) as response:
                raw = response.read(1_000_000).decode("utf-8")
            SESSION_LAST = time.monotonic()
            payload = json.loads(raw)
            result = "".join(p[0] or "" for p in payload[0] if p)
            if not result.strip():
                raise ValueError(f"Empty translation for {target}")
            return result
        except (OSError, ValueError, IndexError, KeyError, TypeError) as exc:
            if attempt == 7:
                raise RuntimeError(f"Translation failed for {target}: {exc}") from exc
            pause = min(45, 2 ** attempt)
            print(f"Retry {target}: {type(exc).__name__} ({pause}s)", flush=True)
            time.sleep(pause)
    raise AssertionError("Unreachable")


def mask_literals(value: str) -> tuple[str, dict[str, str]]:
    kept: dict[str, str] = {}

    def protect(match: re.Match[str]) -> str:
        key = f"HEMLITERAL{len(kept):04d}QXZ"
        kept[key] = match.group(0)
        return key

    return LITERAL_PATTERN.sub(protect, value), kept


def recover_literals(result: str, kept: dict[str, str]) -> str:
    for marker, original in kept.items():
        pattern = r"\s*".join(re.escape(x) for x in marker)
        result, count = re.subn(pattern, lambda _: original, result)
        if count != 1:
            raise ValueError(f"Unrecoverable literal {marker}: {result[:140]}")
    if "HEMLITERAL" in result:
        raise ValueError("Inline literal left in translated text")
    return result


def build_units(source: str):
    rendered = []
    units = []
    fenced = False
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith(("~~~", "\x60\x60\x60")):
            fenced = not fenced
            rendered.append(("literal", line))
            continue
        if not fenced and stripped.startswith("<"):
            strong = re.fullmatch(r'(<p[^>]*><strong>)([^<]+)(</strong></p>)', stripped)
            alt = re.match(r'^(.*\balt=")([^"]+)(".*)$', line)
            if strong or alt:
                groups = strong.groups() if strong else alt.groups()
                masked, held = mask_literals(groups[1])
                index = len(units)
                units.append((index, masked, held))
                rendered.append(("unit", index, groups[0], groups[2]))
                continue
        if (fenced or not stripped or stripped.startswith("<") or
                stripped in ("---", "***")):
            rendered.append(("literal", line))
            continue
        if line.startswith("|") and line.endswith("|"):
            ids = []
            for part in line.split("|"):
                if not part.strip() or TABLE_DIVIDER.fullmatch(part.strip()):
                    ids.append(("literal", part))
                    continue
                head = part[:len(part) - len(part.lstrip())]
                tail = part[len(part.rstrip()):]
                masked, held = mask_literals(part.strip())
                index = len(units)
                units.append((index, masked, held))
                ids.append(("unit", index, head, tail))
            rendered.append(("table", ids))
            continue
        m = LIST_PREFIX.match(line)
        prefix = m.group(1) if m else ""
        body = m.group(2) if m else line
        if not body.strip():
            rendered.append(("literal", line))
            continue
        head = body[:len(body) - len(body.lstrip())]
        tail = body[len(body.rstrip()):]
        masked, held = mask_literals(body.strip())
        index = len(units)
        units.append((index, masked, held))
        rendered.append(("unit", index, prefix + head, tail))
    if fenced:
        raise ValueError("Unclosed Markdown code fence")
    return rendered, units


def translate_batch(batch, target: str) -> dict[int, str]:
    if len(batch) == 1:
        index, value, _ = batch[0]
        return {index: request_translation(value, target).strip()}
    query = "\n".join(f"__HEMSEG{index:04d}__ {value}"
                      for index, value, _ in batch)
    translated = request_translation(query, target)
    markers = list(BATCH_MARKER.finditer(translated))
    ids = [item[0] for item in batch]
    if len(markers) == len(batch) and [int(m.group(1)) for m in markers] == ids:
        values = {}
        for offset, match in enumerate(markers):
            end = (markers[offset + 1].start() if offset + 1 < len(markers)
                   else len(translated))
            item = translated[match.end():end].strip()
            if not item:
                break
            values[ids[offset]] = item
        if len(values) == len(batch):
            return values
    midpoint = len(batch) // 2
    return {**translate_batch(batch[:midpoint], target),
            **translate_batch(batch[midpoint:], target)}



# Local CPU translation avoids third-party API quotas and remains deterministic.
NLLB_CODES = {
    "ar": "arb_Arab", "bg": "bul_Cyrl", "bn": "ben_Beng",
    "cs": "ces_Latn", "da": "dan_Latn", "de": "deu_Latn",
    "el": "ell_Grek", "es": "spa_Latn", "fa": "pes_Arab",
    "fi": "fin_Latn", "fr": "fra_Latn", "he": "heb_Hebr",
    "hi": "hin_Deva", "hr": "hrv_Latn", "hu": "hun_Latn",
    "id": "ind_Latn", "it": "ita_Latn", "ja": "jpn_Jpan",
    "ko": "kor_Hang", "nb": "nob_Latn", "nl": "nld_Latn",
    "pl": "pol_Latn", "pt": "por_Latn", "pt-BR": "por_Latn",
    "ro": "ron_Latn", "ru": "rus_Cyrl", "sk": "slk_Latn",
    "sr": "srp_Cyrl", "sv": "swe_Latn", "ta": "tam_Taml",
    "th": "tha_Thai", "tr": "tur_Latn", "uk": "ukr_Cyrl",
    "ur": "urd_Arab", "vi": "vie_Latn",
    "zh-Hans": "zho_Hans", "zh-Hant": "zho_Hant",
}
INLINE_PROTECTED = re.compile(
    r"(HEMLITERAL[0-9]{4}QXZ|\*\*|\[|\]|Home Assistant|"
    r"(?<!\w)HEM(?!\w)|(?<!\w)HACS(?!\w)|"
    r"(?<!\w)PID(?!\w)|(?<!\w)Ko-fi(?!\w)|(?<!\w)GitHub(?!\w))"
)
NLLB_REPO = "luigi000/nllb-200-distilled-600M-ct2-int8"


def offline_translate_units(units, target: str) -> dict[int, str]:
    """Translate prose only; never feed Markdown, URLs, YAML or code to NLLB."""
    import ctranslate2
    import sentencepiece as spm
    from huggingface_hub import snapshot_download

    if set(NLLB_CODES) != set(LANGUAGES) - {"en"}:
        raise ValueError("Offline translation locale map is incomplete")
    root = Path(snapshot_download(
        repo_id=NLLB_REPO,
        allow_patterns=("model.bin", "config.json", "shared_vocabulary.json",
                        "sentencepiece.bpe.model")
    ))
    sp = spm.SentencePieceProcessor(model_file=str(root / "sentencepiece.bpe.model"))
    translator = ctranslate2.Translator(
        str(root), device="cpu", compute_type="int8",
        inter_threads=1, intra_threads=2
    )
    locale = NLLB_CODES[target]
    translated_parts = {}
    pending: dict[str, None] = {}
    ordered_parts = {}

    # Split syntax from human text *before* machine translation.
    for index, original, protected in units:
        parts = INLINE_PROTECTED.split(original)
        ordered_parts[index] = parts
        for part in parts:
            if (not part.strip() or INLINE_PROTECTED.fullmatch(part) or
                    not re.search(r"[\w\u0080-\uffff]", part)):
                continue
            pending[part] = None

    original_text = list(pending)
    print(f"Offline NLLB {target}: {len(original_text)} distinct prose segments", flush=True)

    # CTranslate2 batches reduce CPU time. Feed complete natural-language
    # segments; keep the original syntax outside all model requests.
    for offset in range(0, len(original_text), 24):
        texts = original_text[offset:offset + 24]
        source_tokens = []
        for part in texts:
            token_list = ["eng_Latn"] + sp.encode(part.strip(), out_type=str) + ["</s>"]
            if len(token_list) > 480:
                raise ValueError(f"Translation segment > NLLB context: {target}")
            source_tokens.append(token_list)
        outcomes = translator.translate_batch(
            source_tokens, target_prefix=[[locale]] * len(texts),
            beam_size=2, max_decoding_length=450, batch_type="tokens",
            max_batch_size=24
        )
        if len(outcomes) != len(texts):
            raise RuntimeError(f"Incomplete offline translation: {target}")
        for original, output in zip(texts, outcomes):
            words = [token for token in output.hypotheses[0]
                     if token not in (locale, "</s>")]
            phrase = sp.decode(words).strip()
            if not phrase:
                raise ValueError(f"Empty offline translation: {target}: {original[:70]}")
            left = original[:len(original) - len(original.lstrip())]
            right = original[len(original.rstrip()):]
            translated_parts[original] = left + phrase + right
        print(f"  {target}: {min(offset + len(texts), len(original_text))}/{len(original_text)}", flush=True)

    output = {}
    for index, original, protected in units:
        parts = ordered_parts[index]
        result = "".join(translated_parts.get(part, part) for part in parts)
        result = recover_literals(result, protected)
        if not result.strip():
            raise ValueError(f"Empty localized README unit: {target} #{index}")
        output[index] = result
    return output

def translate_units(units, target: str) -> dict[int, str]:
    return offline_translate_units(units, target)
    results = {}
    batch = []
    length = 0

    def flush():
        nonlocal batch, length
        if batch:
            results.update(translate_batch(batch, target))
        batch, length = [], 0

    for unit in units:
        estimated = len(unit[1]) + 16
        if batch and length + estimated > 2900:
            flush()
        batch.append(unit)
        length += estimated
    flush()
    for index, original, protected in units:
        try:
            results[index] = recover_literals(results[index], protected)
        except ValueError:
            results[index] = recover_literals(
                request_translation(original, target).strip(), protected
            )
        if not results[index].strip():
            raise ValueError(f"Missing translated content: {target} #{index}")
    return results


def rebase_relative_urls(document: str) -> str:
    def rebase(path: str) -> str:
        if (not path or path.startswith(("#", "/", "http:", "https:",
                                         "mailto:", "data:"))):
            return path
        return "../../" + path
    document = re.sub(
        r"(?<=\]\()([^)]+)(?=\))",
        lambda m: rebase(m.group(1)), document,
    )
    document = re.sub(
        r'(?<=\bsrc=")([^"]+)(?=")',
        lambda m: rebase(m.group(1)), document,
    )
    document = re.sub(
        r'(?<=\bhref=")([^"]+)(?=")',
        lambda m: rebase(m.group(1)), document,
    )
    return document


def render(source: str, target: str) -> str:
    raw = NAV_PATTERN.sub("", source)
    template, units = build_units(raw)
    translated = translate_units(units, target)
    lines = []
    for part in template:
        if part[0] == "literal":
            lines.append(part[1])
        elif part[0] == "unit":
            lines.append(part[2] + translated[part[1]] + part[3])
        else:
            components = []
            for item in part[1]:
                if item[0] == "literal":
                    components.append(item[1])
                else:
                    components.append(item[2] + translated[item[1]] + item[3])
            lines.append("|".join(components))
    page = rebase_relative_urls("\n".join(lines).strip() + "\n")
    # Translated headings have translated slugs. Preserve the canonical
    # English IDs so the original table-of-contents links keep working.
    canonical_headings = [line for line in raw.splitlines()
                          if re.match(r"^#{1,6} ", line)]
    translated_lines = []
    heading_index = 0
    for line in page.splitlines():
        if re.match(r"^#{1,6} ", line):
            heading = re.sub(r"^#{1,6} ", "", canonical_headings[heading_index])
            slug = re.sub(r"[^\w -]", "", heading.lower()).strip().replace(" ", "-")
            if slug:
                translated_lines.append(f'<a id="{slug}"></a>')
            heading_index += 1
        translated_lines.append(line)
    if heading_index != len(canonical_headings):
        raise ValueError(f"Heading structure changed in {target}")
    page = "\n".join(translated_lines) + "\n"
    first_header = re.search(r"^# ", page, flags=re.M)
    if not first_header:
        raise ValueError(f"No H1 found in {target}")
    page = (page[:first_header.start()] + navigation(target) + "\n\n" +
            page[first_header.start():])
    return page


def validate(source: str, page: str, target: str) -> None:
    if "HEMLITERAL" in page or "__HEMSEG" in page:
        raise ValueError(f"Unresolved translation marker: {target}")
    if page.count("## ") != source.count("## "):
        raise ValueError(f"Section count changed: {target}")
    if page.count('src="../../docs/images/') != source.count('src="docs/images/'):
        raise ValueError(f"Image count changed: {target}")
    if 'src="../../.github/assets/ko-fi-banner.svg"' not in page:
        raise ValueError(f"Ko-fi image missing: {target}")
    if 'href="https://ko-fi.com/chreece"' not in page:
        raise ValueError(f"Ko-fi link missing: {target}")
    if page.count("<!-- HEM-LANGUAGE-SELECTOR-START -->") != 1:
        raise ValueError(f"Language selector missing: {target}")
    if page.count("type: custom:home-environment-manager-card") != 2:
        raise ValueError(f"YAML card definition modified: {target}")
    if len(page) < len(source) * 0.32:
        raise ValueError(f"Suspiciously short translation: {target}")


def main() -> int:
    actual = {p.stem for p in LOCALE_DIR.glob("*.json")}
    if actual != set(LANGUAGES):
        raise ValueError(f"Locale inventory differs: {actual ^ set(LANGUAGES)}")
    source = (ROOT / "README.md").read_text(encoding="utf-8")
    if source.count('src=".github/assets/hem-banner.svg"') != 1:
        raise ValueError("Canonical HEM banner missing")
    if source.count('src=".github/assets/ko-fi-banner.svg"') != 1:
        raise ValueError("Canonical Ko-fi banner missing")
    if NAV_PATTERN.search(source) is None:
        raise ValueError("English language selector missing")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", choices=[code for code in LANGUAGES if code != "en"],
                        help="Translate just one UI locale (for CI matrix jobs)")
    args = parser.parse_args()
    requested = [args.lang] if args.lang else [code for code in LANGUAGES if code != "en"]
    results = {}
    for code in requested:
        print(f"Translating README: {code}", flush=True)
        page = render(source, code)
        validate(source, page, code)
        results[code] = page
        print(f"Validated {code}: {len(page)} characters", flush=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for code, page in results.items():
        (OUTPUT_DIR / f"README.{code}.md").write_text(page, encoding="utf-8")
    print(f"PASS: {len(results)} localized README(s); English remains default", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
