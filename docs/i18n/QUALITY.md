# HEM README translation quality

The canonical documentation is [README.md](../../README.md), in English. HEM supports 38 interface locales, but **interface language availability does not certify README translation quality**.

The previous automated translation run used the NLLB-200 machine-translation model. Its validation checked document structure, links, code blocks and image paths, but **did not test linguistic fluency or technical meaning**. A spot audit found malformed headings in all 36 non-Greek translated pages, as well as errors affecting safety-related descriptions, including ventilation, mold risk and shading.

## Current status

| Locale | Language | README quality status |
| --- | --- | --- |
| `ar` | العربية | Unreviewed machine translation - may contain incorrect or misleading text |
| `bg` | Български | Unreviewed machine translation - may contain incorrect or misleading text |
| `bn` | বাংলা | Unreviewed machine translation - may contain incorrect or misleading text |
| `cs` | Čeština | Unreviewed machine translation - may contain incorrect or misleading text |
| `da` | Dansk | Unreviewed machine translation - may contain incorrect or misleading text |
| `de` | Deutsch | Fully rewritten for natural wording; independent native-speaker review still requested |
| `el` | Ελληνικά | Fully rewritten for natural wording; independent native-speaker review still requested |
| `en` | English | Canonical English source |
| `es` | Español | Fully rewritten for natural wording; independent native-speaker review still requested |
| `fa` | فارسی | Unreviewed machine translation - may contain incorrect or misleading text |
| `fi` | Suomi | Unreviewed machine translation - may contain incorrect or misleading text |
| `fr` | Français | Fully rewritten for natural wording; independent native-speaker review still requested |
| `he` | עברית | Unreviewed machine translation - may contain incorrect or misleading text |
| `hi` | हिन्दी | Unreviewed machine translation - may contain incorrect or misleading text |
| `hr` | Hrvatski | Unreviewed machine translation - may contain incorrect or misleading text |
| `hu` | Magyar | Unreviewed machine translation - may contain incorrect or misleading text |
| `id` | Bahasa Indonesia | Unreviewed machine translation - may contain incorrect or misleading text |
| `it` | Italiano | Unreviewed machine translation - may contain incorrect or misleading text |
| `ja` | 日本語 | Unreviewed machine translation - may contain incorrect or misleading text |
| `ko` | 한국어 | Unreviewed machine translation - may contain incorrect or misleading text |
| `nb` | Norsk bokmål | Unreviewed machine translation - may contain incorrect or misleading text |
| `nl` | Nederlands | Unreviewed machine translation - may contain incorrect or misleading text |
| `pl` | Polski | Unreviewed machine translation - may contain incorrect or misleading text |
| `pt` | Português | Unreviewed machine translation - may contain incorrect or misleading text |
| `pt-BR` | Português (Brasil) | Unreviewed machine translation - may contain incorrect or misleading text |
| `ro` | Română | Unreviewed machine translation - may contain incorrect or misleading text |
| `ru` | Русский | Unreviewed machine translation - may contain incorrect or misleading text |
| `sk` | Slovenčina | Unreviewed machine translation - may contain incorrect or misleading text |
| `sr` | Српски | Unreviewed machine translation - may contain incorrect or misleading text |
| `sv` | Svenska | Unreviewed machine translation - may contain incorrect or misleading text |
| `ta` | தமிழ் | Unreviewed machine translation - may contain incorrect or misleading text |
| `th` | ไทย | Unreviewed machine translation - may contain incorrect or misleading text |
| `tr` | Türkçe | Unreviewed machine translation - may contain incorrect or misleading text |
| `uk` | Українська | Unreviewed machine translation - may contain incorrect or misleading text |
| `ur` | اردو | Unreviewed machine translation - may contain incorrect or misleading text |
| `vi` | Tiếng Việt | Unreviewed machine translation - may contain incorrect or misleading text |
| `zh-Hans` | 简体中文 | Unreviewed machine translation - may contain incorrect or misleading text |
| `zh-Hant` | 繁體中文 | Unreviewed machine translation - may contain incorrect or misleading text |

**The four rewritten languages are AI-assisted editorial revisions, not certified native-speaker translations.** They have been cross-checked against the English source for their sections, anchors, links, images, YAML examples and the key HEM safety statements. These structural and editorial checks cannot replace review by a proficient speaker.

**Unreviewed translations remain available only with a visible warning.** When following instructions about device control, electrical or operating protections, PID, or installation, consult the [English README](../../README.md).

## How to review and improve a language

1. Start from the current English [README.md](../../README.md) and edit `docs/i18n/README.<locale>.md` as fluent, natural writing in that language. Do not patch one malformed phrase while leaving a paragraph with incorrect meaning.
2. Preserve technical names, links, Markdown structure, anchored headings, images, YAML examples, repository URLs and the literal `environment_manager` integration domain.
3. Verify all important behavioral boundaries: HEM does not automatically control discovered devices; device operation requires explicit authorization and valid evidence; PID is available only where supported; estimated mold risk is not a mold detector; an airing recommendation does not automatically open a window; missing sensor data must not be interpreted as a safe measurement; and successful command dispatch does not prove physical actuation.
4. Have a proficient speaker read the whole translation in context, paying particular attention to smart-home terminology, formal/informal address and precise instructions. Check screenshots and user-facing Home Assistant navigation names.
5. Record the reviewer and review date in a pull request before changing the status to native-speaker reviewed. Run `python -I .github/tests/test_readme_localizations.py` and `python -I .github/tests/test_readme_translation_quality.py`.

### Examples discovered in the audit

- Greek: “Επικίνδυνο όταν είσαι σπίτι” incorrectly meant *comfortable when at home*; “αποχρωματισμού” incorrectly meant *shading*.
- German: “Klimabewältigung” mistranslated climate control, and several headings were grammatically broken.
- French: “indication de moule” incorrectly translated mold indication as a physical cast or mold.
- Spanish: “¿Qué puede HEM ¿Qué quieres decir?” is two mismatched questions, not *What can HEM do?*
- Japanese and Chinese: several questions and descriptions are incorrectly phrased, including the distinction between mold, molding and technical modes.

This file describes **documentation quality**, not the quality of HEM's interface locale JSON files. Those are a separate review task.

