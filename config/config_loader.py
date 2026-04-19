import yaml
from pathlib import Path
from types import SimpleNamespace


def _dict_to_namespace(d: dict) -> SimpleNamespace:
    ns = SimpleNamespace()
    for key, value in d.items():
        if isinstance(value, dict):
            setattr(ns, key, _dict_to_namespace(value))
        else:
            setattr(ns, key, value)
    return ns


def load_config(path: str = None) -> SimpleNamespace:
    if path is None:
        path = Path(__file__).parent / "config.yaml"
    with open(path, "r") as f:
        raw = yaml.safe_load(f)
    return _dict_to_namespace(raw)


CFG = load_config()
