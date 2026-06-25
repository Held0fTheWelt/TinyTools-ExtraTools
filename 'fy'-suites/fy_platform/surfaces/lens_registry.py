"""Registry of suite adapters with optional import tolerance."""
from __future__ import annotations

from importlib import import_module
from typing import Any


_DEFNS = {
    "contractify": ("contractify.adapter.service", "ContractifyAdapter"),
    "testify": ("testify.adapter.service", "TestifyAdapter"),
    "documentify": ("documentify.adapter.service", "DocumentifyAdapter"),
    "docify": ("docify.adapter.service", "DocifyAdapter"),
    "despaghettify": ("despaghettify.adapter.service", "DespaghettifyAdapter"),
    "dockerify": ("dockerify.adapter.service", "DockerifyAdapter"),
    "postmanify": ("postmanify.adapter.service", "PostmanifyAdapter"),
    "templatify": ("templatify.adapter.service", "TemplatifyAdapter"),
    "usabilify": ("usabilify.adapter.service", "UsabilifyAdapter"),
    "securify": ("securify.adapter.service", "SecurifyAdapter"),
    "observifyfy": ("observifyfy.adapter.service", "ObservifyfyAdapter"),
    "mvpify": ("mvpify.adapter.service", "MVPifyAdapter"),
    "metrify": ("metrify.adapter.service", "MetrifyAdapter"),
    "diagnosta": ("diagnosta.adapter.service", "DiagnostaAdapter"),
    "coda": ("coda.adapter.service", "CodaAdapter"),
}


def _load_adapter(module_name: str, attr_name: str) -> Any | None:
    try:
        module = import_module(module_name)
    except ModuleNotFoundError:
        return None
    return getattr(module, attr_name, None)


ADAPTERS: dict[str, Any] = {}
for _name, (_module_name, _attr_name) in _DEFNS.items():
    _adapter = _load_adapter(_module_name, _attr_name)
    if _adapter is not None:
        ADAPTERS[_name] = _adapter
