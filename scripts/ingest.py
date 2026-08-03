"""Ingesta end-to-end: data/raw/fit → DuckDB → métricas de carga.

Uso (desde la raíz del proyecto):
    python scripts/ingest.py

Idempotente: solo procesa archivos nuevos (D-004). Ejecutar tras cada sincronización.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from garmin.db.export_loader import load_export          # noqa: E402
from garmin.db.loader import load_directory              # noqa: E402
from garmin.db.monitoring_loader import load_monitoring  # noqa: E402
from garmin.db.schema import connect                     # noqa: E402
from garmin.metrics.load import refresh_all              # noqa: E402
from garmin.metrics.readiness import refresh_readiness   # noqa: E402
from garmin.metrics.recovery import refresh_recovery     # noqa: E402
from garmin.metrics.zones import compute_zone_times      # noqa: E402
from garmin.utils.config import db_path, load_settings   # noqa: E402


def main() -> None:
    cfg = load_settings()
    db = db_path(cfg)
    fit_dir = ROOT / cfg["paths"]["raw_fit"]

    print(f"Base de datos : {db}")
    print(f"Carpeta FIT   : {fit_dir}")

    rep = load_directory(db, fit_dir)
    print(
        f"Actividades   : {rep['ok']} ok, {rep['errores']} con error, "
        f"{rep['nuevos']} nuevos, {rep['saltados']} ya cargados"
    )

    mon = load_monitoring(db, ROOT / "data/raw/monitoring")
    resumen = " · ".join(
        f"{k}: {v['ok']} ok" + (f", {v['errores']} err" if v["errores"] else "")
        for k, v in mon.items()
    )
    print(f"Monitoreo     : {resumen}")

    exp = load_export(db, ROOT / "data/raw/export")
    if exp:
        acts = exp.get("actividades") or {}
        print(
            f"Export Garmin : {exp.get('dias_rellenados', 0)} días rellenados"
            + (f" · actividades históricas: +{acts.get('insertadas', 0)} "
               f"({acts.get('duplicadas_omitidas', 0)} ya existían)" if acts else "")
        )

    met = refresh_all(db)
    con = connect(db)
    try:
        n_zonas = compute_zone_times(con)
    finally:
        con.close()
    print(
        f"Métricas      : {met['trimp_calculados']} TRIMP calculados, "
        f"{n_zonas} actividades con zonas nuevas, serie de {met['dias_serie']} días"
    )

    # Series derivadas (D-018). Van después de refresh_all porque leen daily_load.
    rec = refresh_recovery(db)
    rdy = refresh_readiness(db)
    print(
        f"Recuperación  : {rec['dias_con_banda']} días con banda personal · "
        f"FC reposo {rec['rhr_estado']} ({rec['rhr_estado_fecha']}) · "
        f"deuda de sueño 7d: {rec['deuda_7d_h']} h ({rec['deuda_7d_fecha']}) · "
        f"HRV: {rec['hrv_motivo']}"
    )
    print(
        f"Disposición   : {rdy['dias_serie']} días · índice hoy {rdy['indice']} "
        f"({rdy['n_dominios']} dominios, {rdy['dominios_alerta']} en alerta)"
    )
    print(f"Estado hoy    : ACWR={met['acwr_hoy']}  riesgo={met['riesgo_hoy']}")


if __name__ == "__main__":
    main()
