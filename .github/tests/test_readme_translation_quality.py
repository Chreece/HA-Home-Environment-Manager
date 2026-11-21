"""README translation-quality disclosures and safeguards.

Structural parity cannot prove native fluency. These checks only prevent
unreviewed machine translations from being presented as verified documentation.
"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "README.md").read_text(encoding="utf-8")
DIRECTORY = ROOT / "docs/i18n"
LOCALES = {p.stem for p in (ROOT / "custom_components/environment_manager/translations").glob("*.json")}
REWRITTEN = {"el", "de", "fr", "es"}
UNREVIEWED = LOCALES - REWRITTEN - {"en"}
UPDATES = json.loads((ROOT / '.github/localization/readme_updates.json').read_text())['translations']

assert len(LOCALES) == 38
assert len(UNREVIEWED) == 33
assert "Translation quality: English is the reference" in SOURCE
assert 'href="docs/i18n/QUALITY.md"' in SOURCE
assert (DIRECTORY / "QUALITY.md").is_file()

for code in UNREVIEWED:
    path = DIRECTORY / f"README.{code}.md"
    data = path.read_text(encoding="utf-8")
    assert data.count("<!-- HEM-TRANSLATION-UNREVIEWED-START -->") == 1, code
    assert data.count("<!-- HEM-TRANSLATION-UNREVIEWED-END -->") == 1, code
    assert UPDATES[code]['warning'] in data, code
    assert UPDATES[code]['warning'] != UPDATES['en']['warning'], code
    assert 'href="../../README.md"' in data, code
    assert data.index("<!-- HEM-TRANSLATION-UNREVIEWED-START -->") < data.index("## "), code

for code in REWRITTEN:
    data = (DIRECTORY / f"README.{code}.md").read_text(encoding="utf-8")
    assert "HEM-TRANSLATION-UNREVIEWED" not in data, code
    assert data.count("type: custom:home-environment-manager-card") == 2, code
    assert data.count('src="../../docs/images/') == 5, code
    assert data.count('<a id="') >= 25, code
    assert "**https://github.com/Chreece/HA-Home-Environment-Manager**" in data, code
    assert "**custom_components/environment_manager**" in data, code
    assert "**environment_manager**" in data, code

samples = {
    "el": {
        "required": ("Άνεση όταν είστε σπίτι", "σκίαση", "δεν ανοίγει από μόνο του",
                     "εκτίμηση, όχι", "ντετερμινιστικές"),
        "forbidden": ("Επικίνδυνο όταν είσαι σπίτι", "αποχρωματισμού",
                      "Γουίλ . HEM", "Εμπορικό κατάστημα της Κοινότητας"),
    },
    "de": {
        "required": ("Komfort bei Anwesenheit", "Beschattung",
                     "kein Sensor für Schimmel", "HEM öffnet Fenster nicht selbstständig"),
        "forbidden": ("Klimabewältigung", "Das tun wir?", "Was kann HEM -"),
    },
    "fr": {
        "required": ("Du confort à la maison", "protections solaires",
                     "pas d'un détecteur de moisissures", "HEM n'ouvre pas les fenêtres"),
        "forbidden": ("indication de moule", "Je ne sais pas.", "Qu'est-ce qui peut HEM"),
    },
    "es": {
        "required": ("Confort cuando estás en casa", "sombreado",
                     "no un detector de moho", "HEM no abre una ventana por sí mismo"),
        "forbidden": ("¿Qué quieres decir?", "¿Cómo lo hizo?", "¿Qué puede HEM ¿"),
    },
}
for code, rules in samples.items():
    data = (DIRECTORY / f"README.{code}.md").read_text(encoding="utf-8")
    for phrase in rules["required"]:
        assert phrase.casefold() in data.casefold(), (code, "missing key behavioral phrase", phrase)
    for phrase in rules["forbidden"]:
        assert phrase not in data, (code, "known wrong translation resurfaced", phrase)

print("PASS: 33 machine translations explicitly identified; four editorial rewrites "
      "retain key safety claims, without claiming native-speaker certification")
