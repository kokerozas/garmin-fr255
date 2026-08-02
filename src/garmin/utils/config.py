"""Configuración del proyecto: rutas y parámetros del atleta."""
from pathlib import Path
import yaml

# Raíz del proyecto: .../garmin-fr255 (este archivo vive en src/garmin/utils/)
PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULTS = {
    "paths": {
        "raw_fit": "data/raw/fit",
        "raw_tcx": "data/raw/tcx",
        "interim": "data/interim",
        "processed": "data/processed",
        "database": "data/db/garmin.duckdb",
    },
    "atleta": {"fc_maxima": None, "fc_reposo": None},
    "ingesta": {"extensiones": [".fit"]},
}


def load_settings() -> dict:
    """Lee config/settings.yaml (o el example como fallback) y mezcla con defaults."""
    cfg = {k: (v.copy() if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    for name in ("settings.yaml", "settings.example.yaml"):
        p = PROJECT_ROOT / "config" / name
        if p.exists():
            with open(p, encoding="utf-8") as f:
                user = yaml.safe_load(f) or {}
            for section, values in user.items():
                if isinstance(values, dict):
                    cfg.setdefault(section, {}).update(values)
                else:
                    cfg[section] = values
            break
    return cfg


def db_path(cfg: dict | None = None) -> Path:
    cfg = cfg or load_settings()
    p = PROJECT_ROOT / cfg["paths"]["database"]
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
