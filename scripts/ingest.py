"""Ingesta end-to-end: data/raw/fit → DuckDB → métricas de carga.

Uso (desde la raíz del proyecto):
    python scripts/ingest.py

Idempotente: solo procesa archivos nuevos (D-004). Ejecutar tras cada sincronización.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from garmin.db.loader import load_directory          # noqa: E402
from garmin.metrics.load import refresh_all          # noqa: E402
from garmin.utils.config import db_path, load_settings  # noqa: E402


def main() -> None:
    cfg = load_settings()
    db = db_path(cfg)
    fit_dir = ROOT / cfg["paths"]["raw_fit"]

    print(f"Base de datos : {db}")
    print(f"Carpeta FIT   : {fit_dir}")

    rep = load_directory(db, fit_dir)
    print(
        f"Ingesta       : {rep['ok']} ok, {rep['errores']} con error, "
        f"{rep['nuevos']} nuevos, {rep['saltados']} ya cargados"
    )

    met = refresh_all(db)
    print(
        f"Métricas      : {met['trimp_calculados']} TRIMP calculados, "
        f"serie de {met['dias_serie']} días"
    )
    print(f"Estado hoy    : ACWR={met['acwr_hoy']}  riesgo={met['riesgo_hoy']}")


if __name__ == "__main__":
    main()
