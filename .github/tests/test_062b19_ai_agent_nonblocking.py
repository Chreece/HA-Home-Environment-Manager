"""B19: AI-agent labels have no synchronous disk read on HA's event loop."""
from __future__ import annotations
import ast
import json
from pathlib import Path
from types import SimpleNamespace as N

SRC=Path(__file__).resolve().parents[2]/"custom_components/environment_manager"
source=(SRC/"ai_rewrite.py").read_text(encoding="utf-8")
tree=ast.parse(source)
constant=next(node for node in tree.body
              if isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name)
              and node.target.id=="AGENT_DEFAULT_LABELS")
funcs={node.name:node for node in tree.body if isinstance(node,ast.FunctionDef)}
assert "_agent_labels" in funcs and "conversation_agent_choices" in funcs
body=ast.get_source_segment(source,funcs["_agent_labels"])
assert "read_text" not in body and "open(" not in body and "Path(" not in body
assert "read_text" not in source and "from pathlib import Path" not in source
namespace={"Any":object,"DEFAULT_AGENT":"default",
           "resolve_language":lambda value:value if value in ("en","el","de","pt-BR") else "en"}
exec(compile(ast.Module(body=[constant,funcs["_agent_labels"],
                              funcs["conversation_agent_choices"]],type_ignores=[]),
             "ai_rewrite.py","exec"),namespace)
agent_labels=namespace["_agent_labels"]()
catalog=json.loads((SRC/"config_i18n_overrides.json").read_text(encoding="utf-8"))
expected={code:entry["agent"] for code,entry in catalog.items()}
assert agent_labels==expected and len(agent_labels)==38
for lang in ("en","el","de","pt-BR"):
    hass=N(config=N(language=lang),states=N(async_all=lambda domain:[]))
    options=namespace["conversation_agent_choices"](hass)
    assert options==[{"value":"default","label":expected[lang]}],(lang,options)
print("PASS: 38 identical agent labels, no filesystem I/O in HA configuration options, localized default choices")
