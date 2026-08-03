"""El formulario no puede desincronizarse del código (D-016, D-021).

Un documento de fórmulas se pudre en silencio: alguien ajusta una constante en el
código y la ficha sigue mostrando el valor viejo, con apariencia de rigor. Estos
tests atan las dos cosas — si cambia una constante, falla el test y hay que
actualizar la ficha a conciencia.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from garmin import formulas as F  # noqa: E402
from garmin import guides  # noqa: E402
from garmin.metrics import load, readiness, recovery, wellness  # noqa: E402
from garmin.metrics import external, zones  # noqa: E402
from garmin.transform import clean  # noqa: E402


def _params(clave: str) -> dict:
    return F.POR_CLAVE[clave]["parametros"]


def _numeros(texto: str) -> set[float]:
    """Números que aparecen en un texto, normalizando el menos tipográfico (−).

    Se comparan VALORES y no cadenas: la ficha escribe "≥ 3/10" o "−1.0" por
    legibilidad, y exigir coincidencia literal haría fallar el test por estética
    en vez de por una desincronización real con el código.
    """
    limpio = texto.replace("−", "-").replace("−", "-")
    return {float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", limpio)}


# Comandos LaTeX que KaTeX entiende y que este formulario usa. Cualquier otro es,
# casi siempre, dos cosas pegadas al concatenar cadenas: "\qquad" + "P" produce
# "\qquadP", que KaTeX pinta como texto crudo en vez de como fórmula. Ese error es
# invisible en el código y salta a la vista en pantalla, así que se comprueba aquí.
COMANDOS_VALIDOS = {
    "alpha", "begin", "cases", "cdot", "dfrac", "Delta", "e", "end", "frac", "ge",
    "iff", "in", "int", "le", "left", "ln", "mathcal", "mathrm", "max", "mediana",
    "min", "mu", "neg", "pm", "qquad", "quad", "right", "sigma", "sum", "text",
    "times", "varnothing", "vee", "wedge", "widetilde", "overline",
}


def test_ningun_comando_latex_quedo_pegado_al_concatenar():
    desconocidos = []
    for f in F.FORMULAS:
        for cmd in re.findall(r"\\([a-zA-Z]+)", f["latex"]):
            if cmd not in COMANDOS_VALIDOS:
                desconocidos.append((f["clave"], "\\" + cmd))
    assert not desconocidos, f"comandos LaTeX inválidos: {desconocidos}"


def test_las_llaves_del_latex_estan_balanceadas():
    for f in F.FORMULAS:
        sin_escapar = re.sub(r"\\[{}]", "", f["latex"])
        assert sin_escapar.count("{") == sin_escapar.count("}"), \
            f"{f['clave']} tiene llaves desbalanceadas"


# --- Integridad estructural --------------------------------------------------

def test_toda_ficha_tiene_los_campos_obligatorios():
    obligatorios = ("clave", "nombre", "categoria", "pregunta", "latex",
                    "implementacion", "referencias", "limitaciones")
    for f in F.FORMULAS:
        for campo in obligatorios:
            assert f.get(campo), f"{f.get('clave')} no tiene {campo}"
        assert f["referencias"], f"{f['clave']} sin referencia primaria (viola D-016)"


def test_claves_unicas_y_categorias_declaradas():
    claves = [f["clave"] for f in F.FORMULAS]
    assert len(claves) == len(set(claves))
    validas = {c for c, _, _ in F.CATEGORIAS}
    assert all(f["categoria"] in validas for f in F.FORMULAS)


def test_cada_ficha_apunta_a_una_guia_existente():
    """El botón ℹ️ enlaza guía y fórmula: una clave rota dejaría la ecuación huérfana."""
    for f in F.FORMULAS:
        assert f["guia"] in guides.GUIDES, f"{f['clave']} apunta a la guía inexistente {f['guia']}"


def test_el_archivo_citado_existe_y_la_funcion_tambien():
    raiz = Path(__file__).resolve().parents[1]
    for f in F.FORMULAS:
        ruta, _, funcs = f["implementacion"].partition("::")
        archivo = raiz / ruta.strip()
        assert archivo.exists(), f"{f['clave']} cita {ruta.strip()}, que no existe"
        fuente = archivo.read_text(encoding="utf-8")
        for fn in funcs.replace("()", "").split(","):
            fn = fn.strip()
            if fn:
                assert f"def {fn}" in fuente, f"{f['clave']} cita {fn}(), ausente en {ruta.strip()}"


# --- Las constantes de las fichas son las del código -------------------------

def test_coeficientes_de_banister():
    p = _params("trimp")
    assert float(p["a"]) == load._B_A
    assert float(p["b"]) == load._B_B


def test_spans_de_atl_y_ctl():
    p = _params("atl_ctl_tsb")
    assert "7" in p["ATL"] and "42" in p["CTL"]
    assert "False" in p["adjust"]      # rebuild_daily_load usa ewm(..., adjust=False)


def test_bandas_del_acwr_coinciden_con_classify_acwr():
    p = _params("acwr")["bandas"]
    for corte in ("0.8", "1.3", "1.5"):
        assert corte in p
    assert load.classify_acwr(1.0) == "optima"
    assert load.classify_acwr(1.4) == "precaucion"
    assert load.classify_acwr(1.6) == "alta"
    assert load.classify_acwr(0.5) == "baja"


def test_constante_swc_y_ventana():
    p = _params("swc")
    assert float(p["k"]) == recovery.SWC_K
    assert str(recovery.VENTANA_REF) in p["ventana"]
    assert str(recovery.MIN_DIAS_REF) in p["mínimo de días medidos"]


def test_necesidad_de_sueno_y_minimos_por_ventana():
    p = _params("deuda_sueno")
    assert str(recovery.NECESIDAD_H_DEFAULT) in p["h_nec"]
    for w, n in recovery.MIN_NOCHES.items():
        assert str(n) in p["mínimo de noches"], f"falta el mínimo de la ventana {w}"


def test_puerta_de_validez_del_hrv():
    p = _params("lnrmssd")["puerta de validez"]
    assert str(recovery.HRV_MIN_NOCHES_SEMANA) in p
    assert str(recovery.HRV_MIN_HISTORIA_D) in p


def test_ventana_y_umbrales_del_readiness():
    p = _params("readiness")
    assert readiness.VENTANA_Z in _numeros(p["ventana"])
    assert readiness.MIN_N_Z in _numeros(p["mínimo de observaciones"])
    umbrales = _numeros(p["umbrales"])
    assert readiness.UMBRAL_ALERTA in umbrales
    assert readiness.UMBRAL_ATENCION in umbrales


def test_cortes_de_zonas():
    p = _params("zonas")["Z1..Z5"]
    for pct in zones.ZONE_PCTS:
        assert str(int(pct * 100)) in p


def test_umbrales_de_limpieza_de_fc():
    p = _params("limpieza_fc")
    assert f"{clean.HR_MIN}-{clean.HR_MAX}" in p["rango plausible"]
    assert str(clean.SPIKE_BPM_PER_S) in p["salto máximo"]


def test_umbrales_de_limpieza_de_velocidad():
    p = _params("limpieza_velocidad")
    assert str(clean.SPEED_MAX_MS) in p["techo"]
    assert str(int(clean.ACCEL_MAX_MS2)) in p["aceleración máxima"]


def test_cortes_del_grado_gps():
    p = _params("gps_grade")
    assert str(external.DT_ALTA) in F.POR_CLAVE["gps_grade"]["latex"]
    assert str(external.DT_MEDIA) in F.POR_CLAVE["gps_grade"]["latex"]
    # Y el reparto declarado corresponde a los grados que la función puede devolver.
    assert external.grade_gps(1.0, True) == "alta"
    assert external.grade_gps(2.74, True) == "baja"


def test_ventana_de_la_base_hooper():
    p = _params("hooper")
    assert str(wellness._VENTANA_BASE_DIAS) in p["ventana"]
    assert str(wellness._MIN_OBS_BASE) in p["mínimo de observaciones"]


def test_puntuacion_ostrc_en_sus_bordes():
    """La escala de la ficha debe ser exactamente la que puntúa el código."""
    latex = F.POR_CLAVE["ostrc"]["latex"]
    for v in (8, 17, 25):
        assert str(v) in latex
    for v in (6, 13, 19):
        assert str(v) in latex
    assert wellness.ostrc_severity(25, 25, 25, 25) == 100
    assert wellness.ostrc_severity(0, 0, 0, 0) == 0
    assert wellness.ostrc_clasificacion(0, 13, 0, 0)["sustancial"] is True
    assert wellness.ostrc_clasificacion(8, 0, 0, 0)["sustancial"] is False


def test_umbral_de_zona_para_preguntar_ostrc():
    assert wellness.OSTRC_UMBRAL_ZONA in _numeros(_params("ostrc")["aplicación"])


def test_umbrales_de_alta_velocidad():
    p = _params("m_por_min")
    assert "Z2..Z5" in p["tiempo activo"]
    assert external.ZONAS_ACTIVAS == (2, 3, 4, 5)


# --- Búsqueda ----------------------------------------------------------------

def test_busqueda_ignora_tildes_y_mayusculas():
    assert F.buscar("SUEÑO") == F.buscar("sueno")
    assert any(f["clave"] == "deuda_sueno" for f in F.buscar("Sueño"))


def test_busqueda_vacia_devuelve_todo():
    assert len(F.buscar("")) == len(F.FORMULAS)


def test_busqueda_encuentra_por_autor_y_por_archivo():
    assert any(f["clave"] == "swc" for f in F.buscar("Hopkins"))
    assert any(f["clave"] == "limpieza_velocidad" for f in F.buscar("clean.py"))
