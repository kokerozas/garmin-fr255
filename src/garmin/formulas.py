"""Formulario del proyecto: cada métrica con su fórmula, su código y su cita.

Cumple la regla suprema D-016 de forma verificable: aquí no se escribe una fórmula
"bonita" sino la que el código ejecuta de verdad, con la ruta al archivo y la función
donde vive, para que cualquiera pueda contrastarlas línea a línea. Si alguna vez el
código y esta ficha se contradicen, es un bug — y el test `tests/test_formulas.py`
comprueba que las constantes citadas aquí sigan siendo las del código.

Estructura de cada ficha:
    clave          identificador estable (se usa para enlazar desde las guías ℹ️)
    nombre         cómo se llama en el dashboard
    categoria      para agrupar en la vista
    pregunta       qué responde, en una línea y en criollo
    latex          la fórmula tal como está implementada
    variables      símbolo → significado
    parametros     valores concretos que usa ESTE proyecto
    implementacion archivo::función donde vive
    referencias    citas primarias completas
    limitaciones   qué NO se puede concluir con esto
"""
from __future__ import annotations

CATEGORIAS = [
    ("carga", "Carga de entrenamiento", "Cuánto trabajo hizo el cuerpo y cómo se acumula."),
    ("recuperacion", "Recuperación", "Si el cuerpo está absorbiendo esa carga o no."),
    ("externa", "Carga externa y fatiga", "Trabajo mecánico: lo que sufrió el músculo."),
    ("subjetiva", "Registro subjetivo", "Lo que solo el atleta puede reportar."),
    ("calidad", "Calidad del dato", "Reglas que deciden en qué números se puede confiar."),
]

FORMULAS: list[dict] = [
    # ------------------------------------------------------------------ CARGA
    {
        "clave": "trimp",
        "nombre": "TRIMP de Banister",
        "categoria": "carga",
        "pregunta": "¿Cuánta carga interna tuvo esta sesión?",
        "latex": r"\mathrm{TRIMP}=\sum_{i}\frac{\Delta t_i}{60}\;\cdot\;"
                 r"\mathrm{HR}_{r,i}\;\cdot\;a\;\cdot\;e^{\,b\,\mathrm{HR}_{r,i}}"
                 r"\qquad\text{con}\qquad "
                 r"\mathrm{HR}_r=\frac{\mathrm{FC}-\mathrm{FC}_{rep}}"
                 r"{\mathrm{FC}_{max}-\mathrm{FC}_{rep}}\in[0,1]",
        "variables": {
            r"\Delta t_i": "segundos entre muestras consecutivas (acotado a 10 s)",
            r"\mathrm{HR}_r": "fracción de reserva cardíaca de la muestra",
            "a, b": "coeficientes exponenciales (perfil masculino)",
        },
        "parametros": {"a": "0.64", "b": "1.92",
                       r"\mathrm{FC}_{max}": "182 ppm", r"\mathrm{FC}_{rep}": "71 ppm"},
        "implementacion": "src/garmin/metrics/load.py :: trimp_from_hr()",
        "referencias": [
            "Banister, E.W. (1991). Modeling elite athletic performance. En: "
            "Physiological Testing of the High-Performance Athlete, Human Kinetics.",
            "Morton, R.H., Fitz-Clarke, J.R. & Banister, E.W. (1990). Modeling human "
            "performance in running. Journal of Applied Physiology 69(3):1171-1177.",
        ],
        "limitaciones": "Integra solo frecuencia cardíaca: es ciego a la carga mecánica "
                        "(aceleraciones, frenadas, saltos), que es justamente la que rompe "
                        "isquiotibiales. La FC de muñeca en fútbol tiene artefactos, por eso "
                        "se integra únicamente sobre muestras marcadas como válidas (D-008).",
        "guia": "carga_diaria",
    },
    {
        "clave": "trimp_avg",
        "nombre": "TRIMP por FC media (respaldo)",
        "categoria": "carga",
        "pregunta": "¿Y cuando no hay serie segundo a segundo?",
        "latex": r"\mathrm{TRIMP}_{avg}=\frac{T}{60}\cdot \overline{\mathrm{HR}_r}\cdot a"
                 r"\cdot e^{\,b\,\overline{\mathrm{HR}_r}}",
        "variables": {"T": "duración total de la sesión en segundos",
                      r"\overline{\mathrm{HR}_r}": "reserva cardíaca de la FC media"},
        "parametros": {"uso": "las 50 actividades del backfill histórico (anteriores a may-2024)"},
        "implementacion": "src/garmin/metrics/load.py :: trimp_session_avg()",
        "referencias": ["Misma base que el TRIMP integrado (Banister 1991)."],
        "limitaciones": "Subestima las sesiones intermitentes: promediar la FC de un partido "
                        "con picos y pausas aplana el término exponencial. Queda marcado en "
                        "`activities.trimp_method = 'session_avg'` para poder excluirlo.",
        "guia": "carga_diaria",
    },
    {
        "clave": "atl_ctl_tsb",
        "nombre": "ATL · CTL · TSB (fitness–fatiga)",
        "categoria": "carga",
        "pregunta": "¿Estoy en forma, fatigado o fresco?",
        "latex": r"y_t=\alpha\,x_t+(1-\alpha)\,y_{t-1},\qquad \alpha=\frac{2}{N+1}"
                 r"\\[6pt]"
                 r"\mathrm{ATL}=y_t^{(N=7)},\qquad \mathrm{CTL}=y_t^{(N=42)},"
                 r"\qquad \mathrm{TSB}=\mathrm{CTL}-\mathrm{ATL}",
        "variables": {"x_t": "TRIMP del día t (0 si no hubo actividad)",
                      "N": "span de la media móvil exponencial"},
        "parametros": {"ATL": "span 7 días", "CTL": "span 42 días",
                       "adjust": "False (recursión estándar, sin corrección de sesgo inicial)"},
        "implementacion": "src/garmin/metrics/load.py :: rebuild_daily_load()",
        "referencias": [
            "Banister, E.W. (1991), modelo fitness-fatiga.",
            "Allen, H. & Coggan, A. Training and Racing with a Power Meter "
            "(operacionalización tipo Performance Management Chart).",
            "Williams, S. et al. (2017). Better way to determine the acute:chronic "
            "workload ratio? British Journal of Sports Medicine 51(3):209-210.",
        ],
        "limitaciones": "Los spans 7/42 son convención, no están calibrados para este atleta. "
                        "Con `adjust=False` los primeros ~42 días de la serie arrastran el "
                        "arranque en cero y subestiman la CTL real.",
        "guia": "kpis_carga",
    },
    {
        "clave": "carga_absoluta",
        "nombre": "Carga absoluta y percentil personal",
        "categoria": "carga",
        "pregunta": "¿Cuánto cargué esta semana, comparado con mis propias semanas?",
        # Ojo al concatenar: sin el espacio final, "\qquad" + "P" se pega en
        # "\qquadP" y KaTeX lo lee como un comando inexistente.
        "latex": r"L_{7}(t)=\sum_{i=t-6}^{t}\mathrm{TRIMP}_i"
                 r"\qquad\qquad "
                 r"P_{7}(t)=\frac{\#\{s\in V_{365}: L_7(s)\le L_7(t)\}}{|V_{365}|}",
        "variables": {"L_7": "suma móvil de 7 días (también 14, 21 y 28)",
                      "V_{365}": "ventana de los 365 días previos",
                      "P_7": "percentil de la semana actual dentro de esa ventana"},
        "parametros": {"min_periods de L": "la ventana completa",
                       "min_periods del percentil": "120 días"},
        "implementacion": "src/garmin/metrics/load.py :: percentil_movil()",
        "referencias": [
            "Impellizzeri, F.M. et al. (2021). What Role Do Chronic Workloads Play in the "
            "Acute to Chronic Workload Ratio? Time to Dismiss ACWR and Its Underlying "
            "Theory. Sports Medicine 51(3):581-592.",
            "Lolli, L. et al. (2019). Mathematical coupling causes spurious correlation "
            "within the conventional acute-to-chronic workload ratio calculations. "
            "British Journal of Sports Medicine 53(15):921-922.",
        ],
        "limitaciones": "El percentil asume que la historia previa sigue siendo un buen "
                        "referente: se rompe tras lesiones largas o cambios de temporada. "
                        "Las unidades TRIMP no son comparables con umbrales publicados, que "
                        "están en AU de sRPE o metros de GPS.",
        "guia": "carga_absoluta",
    },
    {
        "clave": "acwr",
        "nombre": "ACWR (señal secundaria)",
        "categoria": "carga",
        "pregunta": "¿Cuánto se despegó esta semana de lo que venía haciendo?",
        "latex": r"\mathrm{ACWR}(t)=\frac{\frac{1}{7}\sum_{i=t-6}^{t}\mathrm{TRIMP}_i}"
                 r"{\frac{1}{28}\sum_{i=t-27}^{t}\mathrm{TRIMP}_i}",
        "variables": {"numerador": "carga media de los últimos 7 días",
                      "denominador": "carga media de los últimos 28 días"},
        "parametros": {"bandas": "<0.8 subcarga · 0.8-1.3 óptima · 1.3-1.5 precaución · >1.5 alta"},
        "implementacion": "src/garmin/metrics/load.py :: rebuild_daily_load(), classify_acwr()",
        "referencias": [
            "Hulin, B.T. et al. (2016). British Journal of Sports Medicine 50(4):231-236.",
            "Gabbett, T.J. (2016). The training-injury prevention paradox. "
            "British Journal of Sports Medicine 50(5):273-280.",
            "EN CONTRA — Impellizzeri, F.M. et al. (2021). Sports Medicine 51(3):581-592: "
            "sustituyeron la carga crónica por valores ALEATORIOS y el ACWR siguió "
            "asociándose con lesión igual de bien.",
            "EN CONTRA — Dalen-Lorentsen, T. et al. (2021). British Journal of Sports "
            "Medicine: único ECA (482 futbolistas juveniles, 10 meses), sin diferencia.",
        ],
        "limitaciones": "DEGRADADO A SEÑAL SECUNDARIA en D-018. Sufre acoplamiento matemático "
                        "(numerador y denominador comparten datos), su evidencia es asociativa "
                        "y el único ensayo controlado no encontró beneficio al planificar con "
                        "él. Se conserva como descriptor del contraste, no como oráculo.",
        "guia": "acwr",
    },
    {
        "clave": "wow",
        "nombre": "Cambio semana a semana",
        "categoria": "carga",
        "pregunta": "¿Di un salto de carga más grande de lo que suelo dar?",
        "latex": r"\Delta_{sem}(t)=\frac{L_7(t)}{L_7(t-7)}-1"
                 r"\\[6pt]"
                 r"\text{bandera}=\begin{cases}"
                 r"\text{rojo} & |\Delta_{sem}|>2\,\sigma_{\Delta}\\"
                 r"\text{ámbar} & |\Delta_{sem}|>1.5\,\sigma_{\Delta}\\"
                 r"\text{—} & \text{en otro caso}\end{cases}",
        "variables": {r"\sigma_{\Delta}": "desviación de los propios cambios semanales (365 d)"},
        "parametros": {"guarda": "si L₇(t−7) ≤ 50 TRIMP el resultado es nulo",
                       "por qué": "dividir por una semana casi vacía produce porcentajes absurdos"},
        "implementacion": "src/garmin/metrics/load.py :: cambio_semanal(), clasificar_cambio()",
        "referencias": [
            "Rogalski, B. et al. (2013). Training and game loads and injury risk in elite "
            "Australian footballers. Journal of Science and Medicine in Sport 16(6):499-503.",
            "Cross, M.J. et al. (2016). The Influence of In-Season Training Loads on Injury "
            "Risk in Professional Rugby Union. IJSPP 11(3):350-355. — un aumento de 2 DE en "
            "el cambio semanal elevaba las odds de lesión.",
        ],
        "limitaciones": "El umbral está individualizado con la variabilidad propia, NO con los "
                        "AU de rugby del paper: no son transferibles. Y sigue siendo "
                        "asociación, no predicción.",
        "guia": "wow_change",
    },
    {
        "clave": "monotonia",
        "nombre": "Monotonía y strain de Foster",
        "categoria": "carga",
        "pregunta": "¿Mis días son todos iguales? (eso también desgasta)",
        "latex": r"M(t)=\frac{\overline{x}_{7}}{s_{7}}\qquad\qquad"
                 r"\mathrm{Strain}(t)=L_7(t)\cdot M(t)",
        "variables": {r"\overline{x}_7": "media del TRIMP diario de 7 días",
                      "s_7": "desviación estándar de esos 7 días"},
        "parametros": {"umbral de atención": "M > 2.0",
                       "caso borde": "s₇ = 0 (semana plana o de ceros) → nulo, no infinito"},
        "implementacion": "src/garmin/metrics/load.py :: monotonia_strain()",
        "referencias": [
            "Foster, C. (1998). Monitoring training in athletes with reference to "
            "overtraining syndrome. Medicine & Science in Sports & Exercise 30(7):1164-1168.",
        ],
        "limitaciones": "Con semanas irregulares y muchos días en cero —el patrón de un "
                        "amateur— la desviación es inestable y la monotonía salta.",
        "guia": "carga_diaria",
    },
    {
        "clave": "zonas",
        "nombre": "Zonas de frecuencia cardíaca",
        "categoria": "carga",
        "pregunta": "¿Cuánto tiempo estuve en cada intensidad?",
        "latex": r"Z(\mathrm{FC})=\max\{\,i:\ \mathrm{FC}\ge p_i\cdot \mathrm{FC}_{max}\,\}"
                 r"\qquad p=(0.5,\;0.6,\;0.7,\;0.8,\;0.9)",
        "variables": {"p_i": "borde inferior de cada zona como fracción de FCmax"},
        "parametros": {r"\mathrm{FC}_{max}": "182 ppm (override en config/settings.yaml)",
                       "Z1..Z5": "50-60 · 60-70 · 70-80 · 80-90 · 90-100 %FCmax"},
        "implementacion": "src/garmin/metrics/zones.py :: zone_of()",
        "referencias": [
            "ACSM's Guidelines for Exercise Testing and Prescription (prescripción por %FCmax).",
            "Seiler, S. (2010). What is best practice for training intensity and duration "
            "distribution in endurance athletes? IJSPP 5(3):276-291.",
        ],
        "limitaciones": "Los cortes por %FCmax son una convención práctica, no umbrales "
                        "fisiológicos medidos: los umbrales reales (LT1/LT2) exigen test de "
                        "laboratorio o de campo que aquí no existen.",
        "guia": "zonas",
    },

    # ----------------------------------------------------------- RECUPERACIÓN
    {
        "clave": "swc",
        "nombre": "Banda personal (smallest worthwhile change)",
        "categoria": "recuperacion",
        "pregunta": "¿Este valor se salió de MI rango normal, o es ruido?",
        "latex": r"\mu_{28}(t)\pm k\cdot\sigma_{28}(t)"
                 r"\qquad\text{con}\qquad k=0.5"
                 r"\\[6pt]"
                 r"\text{estado}=\begin{cases}"
                 r"\text{sobre\_banda} & x_t>\mu_{28}+k\sigma_{28}\\"
                 r"\text{bajo\_banda} & x_t<\mu_{28}-k\sigma_{28}\\"
                 r"\text{dentro} & \text{en otro caso}\end{cases}",
        "variables": {r"\mu_{28},\ \sigma_{28}": "media y desviación móviles de 28 días",
                      "k": "constante del SWC intraindividual"},
        "parametros": {"k": "0.5", "ventana": "28 días", "mínimo de días medidos": "14",
                       "banda real de Jorge": "±1.8 ppm (σ ≈ 3.6 ppm)",
                       "regla anterior, jubilada": "+5 ppm ≈ 1.4 σ, entre 3 y 5× menos sensible"},
        "implementacion": "src/garmin/metrics/recovery.py :: banda_swc(), clasificar_banda()",
        "referencias": [
            "Hopkins, W.G. (2000). Measures of reliability in sports medicine and science. "
            "Sports Medicine 30(1):1-15. — SWC = 0.5 · DE individual.",
            "Buchheit, M. (2014). Monitoring training status with HR measures: do all roads "
            "lead to Rome? Frontiers in Physiology 5:73.",
        ],
        "limitaciones": "La FC en reposo de Garmin es un valor propietario derivado de PPG de "
                        "muñeca, no un promedio nocturno auditable. Lo que importa es la racha "
                        "de días fuera de banda, no el día suelto.",
        "guia": "banda_personal",
    },
    {
        "clave": "deuda_sueno",
        "nombre": "Deuda de sueño acumulada",
        "categoria": "recuperacion",
        "pregunta": "¿Cuántas horas de sueño llevo debiendo?",
        "latex": r"D_W(t)=\sum_{i\in M_W}\max\!\left(0,\;h_{nec}-h_i\right)"
                 r"\qquad\text{si}\quad |M_W|\ge n_{min}(W)"
                 r"\\[6pt]"
                 r"\mathrm{cobertura}_W=\frac{|M_W|}{W}",
        "variables": {"M_W": "noches MEDIDAS dentro de la ventana W (las ausentes no cuentan)",
                      "h_{nec}": "horas de sueño necesarias", "h_i": "horas dormidas esa noche"},
        "parametros": {"h_nec": "8.0 h (configurable)", "ventanas": "7, 14 y 28 días",
                       "mínimo de noches": "5 / 10 / 20 respectivamente",
                       "situación de Jorge": "media 5.4 h · deuda típica ~12.7 h por semana"},
        "implementacion": "src/garmin/metrics/recovery.py :: deuda_sueno(), cobertura_sueno()",
        "referencias": [
            "Milewski, M.D. et al. (2014). Chronic lack of sleep is associated with increased "
            "sports injuries in adolescent athletes. Journal of Pediatric Orthopaedics "
            "34(2):129-133. — dormir <8 h multiplicaba por 1.7 la probabilidad de lesión.",
            "von Rosen, P. et al. (2017). Too little sleep and an unhealthy diet could "
            "increase the risk of sustaining a new injury. Scandinavian Journal of Medicine "
            "& Science in Sports 27(11):1364-1371. — >8 h reducía las odds un 61 %.",
        ],
        "limitaciones": "REGLA CLAVE: una noche sin dato NO es deuda cero; por debajo del "
                        "mínimo de noches el resultado es nulo y se muestra la cobertura. "
                        "Además el reloj SOBREESTIMA el sueño frente a polisomnografía "
                        "(confunde vigilia tranquila con dormir), así que 5.4 h medidas son "
                        "probablemente menos en la realidad.",
        "guia": "deuda_sueno",
    },
    {
        "clave": "lnrmssd",
        "nombre": "Ln rMSSD con puerta de validez",
        "categoria": "recuperacion",
        "pregunta": "¿Mi sistema nervioso está absorbiendo la carga?",
        "latex": r"\overline{\ln\mathrm{rMSSD}}_{7}=\frac{1}{7}\sum_{i=t-6}^{t}\ln(\mathrm{rMSSD}_i)"
                 r"\qquad\quad \mathrm{CV}=\frac{s(\ln \mathrm{rMSSD})}"
                 r"{\overline{\ln\mathrm{rMSSD}}}\times 100",
        "variables": {"rMSSD": "raíz cuadrática media de diferencias sucesivas entre latidos (ms)",
                      "CV": "coeficiente de variación: la variabilidad de la variabilidad"},
        "parametros": {"puerta de validez": "≥3 noches por semana Y ≥21 días de historia",
                       "por qué el logaritmo": "el rMSSD tiene distribución sesgada a la derecha",
                       "estado en este proyecto": "HRV nace el 18-jul-2026; aún no interpretable"},
        "implementacion": "src/garmin/metrics/recovery.py :: ln_rmssd_movil(), estado_hrv()",
        "referencias": [
            "Plews, D.J. et al. (2013). Training adaptation and heart rate variability in "
            "elite endurance athletes: opening the door to effective monitoring. "
            "Sports Medicine 43(9):773-781.",
            "Buchheit, M. (2014). Frontiers in Physiology 5:73.",
        ],
        "limitaciones": "Por debajo de la puerta de validez la función devuelve nulo CON el "
                        "motivo, en vez de dibujar ruido. El rMSSD de muñeca no equivale al de "
                        "banda pectoral, y la saturación parasimpática puede hacer que un HRV "
                        "muy alto signifique fatiga, no frescura.",
        "guia": "hrv",
    },
    {
        "clave": "readiness",
        "nombre": "Índice de disposición por dominios",
        "categoria": "recuperacion",
        "pregunta": "¿Cómo estoy hoy, en conjunto?",
        "latex": r"z_v(t)=\pm\frac{x_v(t)-\mu_{60,v}(t)}{\sigma_{60,v}(t)}"
                 r"\qquad\qquad "
                 r"z_D=\frac{1}{|V_D|}\sum_{v\in V_D} z_v"
                 r"\\[6pt]"
                 r"I(t)=\frac{1}{|\mathcal{D}(t)|}\sum_{D\in\mathcal{D}(t)} z_D"
                 r"\qquad\text{definido solo si}\quad |\mathcal{D}(t)|\ge 2",
        "variables": {"z_v": "z-score de la variable v (signo invertido si 'más es peor')",
                      "z_D": "promedio del dominio D", r"\mathcal{D}(t)": "dominios DISPONIBLES ese día"},
        "parametros": {"ventana": "60 días", "mínimo de observaciones": "30",
                       "dominios": "autonómico · sueño · carga · subjetivo",
                       "umbrales": "alerta z ≤ −1.0 · atención z ≤ −0.5",
                       "invertidas": "FC en reposo y estrés"},
        "implementacion": "src/garmin/metrics/readiness.py :: _rolling_z(), build_readiness_frame()",
        "referencias": [
            "Buchheit, M. (2014). Frontiers in Physiology 5:73.",
            "Thornton, H.R. et al. (2019). Developing Athlete Monitoring Systems in Team "
            "Sports: Data Analysis and Visualization. IJSPP 14(6):698-705.",
            "Robertson, S., Bartlett, J.D. & Gastin, P.B. (2017). Red, Amber, or Green? "
            "Athlete Monitoring in Team Sport: The Need for Decision-Support Systems. "
            "IJSPP 12(Suppl 2):S2-73-S2-79.",
        ],
        "limitaciones": "Se agrupa por DOMINIO antes de promediar porque sleep_score, estrés y "
                        "Body Battery salen del mismo motor propietario de Garmin y "
                        "promediarlos como independientes le daría triple peso a ese bloque. "
                        "Nunca se imputa: si falta un dato, baja el contador. Y sobre todo: "
                        "z ≤ −1 es una CONVENCIÓN, no un corte clínico, y un conteo de "
                        "banderas NO es un modelo de riesgo calibrado.",
        "guia": "readiness",
    },

    # ---------------------------------------------------- CARGA EXTERNA
    {
        "clave": "m_por_min",
        "nombre": "Metros por minuto",
        "categoria": "externa",
        "pregunta": "¿Qué tan intensa fue la sesión en términos de movimiento?",
        "latex": r"\mathrm{m/min}=\frac{d_{total}}{T_{activo}}"
                 r"\qquad\text{con}\qquad "
                 r"T_{activo}=\frac{1}{60}\sum_{z=2}^{5} t_z",
        "variables": {"d_{total}": "distancia de la sesión (del firmware, no recalculada)",
                      "t_z": "segundos en la zona z"},
        "parametros": {"tiempo activo": "suma de Z2..Z5 (≥60 % FCmax) como proxy del tiempo jugado",
                       "por qué": "la duración total incluye calentamiento y banca",
                       "observado en fútbol": "~63 m/min"},
        "implementacion": "src/garmin/metrics/external.py :: session_external()",
        "referencias": [
            "Casamichana, D. et al. (2013). Relationship Between Indicators of Training Load "
            "in Soccer Players. Journal of Strength and Conditioning Research 27(2):369-374.",
            "Vanrenterghem, J. et al. (2017). Training load monitoring in team sports: a "
            "novel framework separating physiological and biomechanical load-adaptation "
            "pathways. Sports Medicine 47(11):2135-2142.",
        ],
        "limitaciones": "El error típico de distancia con GPS de muñeca es 5-7 %: diferencias "
                        "menores al 10 % entre sesiones NO son interpretables. Los valores "
                        "absolutos no se pueden comparar con la literatura de fútbol "
                        "profesional, medida con dispositivos de 10 Hz en la espalda.",
        "guia": "carga_externa",
    },
    {
        "clave": "eficiencia",
        "nombre": "Índice de eficiencia (externa : interna)",
        "categoria": "externa",
        "pregunta": "¿Cuántos metros me rinde cada unidad de esfuerzo cardíaco?",
        "latex": r"\mathrm{Eff}=\frac{d_{total}}{\mathrm{TRIMP}}",
        "variables": {"d_{total}": "metros recorridos en la sesión",
                      r"\mathrm{TRIMP}": "carga interna de esa misma sesión"},
        "parametros": {"criterios de validez": "trimp_method = 'samples' · cobertura FC ≥ 0.9 · "
                                               "duración ≥ 30 min · distancia presente"},
        "implementacion": "src/garmin/metrics/load.py :: efficiency_index()",
        "referencias": [
            "Akubat, I. et al. (2014). Integrating the internal and external training loads "
            "in soccer. International Journal of Sports Physiology and Performance 9(3):457-462.",
        ],
        "limitaciones": "DESVIACIÓN DECLARADA: el paper original usa iTRIMP, que exige un perfil "
                        "individual FC-lactato de laboratorio inexistente aquí; se sustituye por "
                        "el TRIMP de Banister. Además es un ratio y hereda el mismo problema de "
                        "acoplamiento matemático del ACWR. Solo comparable entre sesiones del "
                        "mismo deporte y formato.",
        "guia": "eficiencia",
    },
    {
        "clave": "decoupling",
        "nombre": "Fatiga intra-partido (decoupling)",
        "categoria": "externa",
        "pregunta": "¿La segunda mitad me costó más pulso por metro que la primera?",
        "latex": r"C_m=\frac{\overline{\mathrm{HR}_r}^{(m)}}{\overline{v}^{(m)}}"
                 r"\qquad\qquad"
                 r"\mathrm{Decoupling}=\left(\frac{C_2}{C_1}-1\right)\times 100",
        "variables": {"C_m": "coste cardíaco de la mitad m: reserva de FC por unidad de velocidad",
                      r"\overline{\mathrm{HR}_r}": "reserva cardíaca media ponderada por tiempo",
                      r"\overline{v}": "velocidad media válida de la mitad"},
        "parametros": {"corte": "por TIEMPO transcurrido (90 de 96 partidos tienen un solo lap)",
                       "guardas": "duración ≥ 30 min · cobertura FC ≥ 0.8 · velocidad ≥ 0.5 m/s",
                       "sin velocidad utilizable": "se informa solo la deriva de %FCmax",
                       "observado": "media +4.1 % en 75 partidos"},
        "implementacion": "src/garmin/metrics/intrasession.py :: _mitad(), rebuild_intrasession()",
        "referencias": [
            "Mohr, M., Krustrup, P. & Bangsbo, J. (2003). Match performance of high-standard "
            "soccer players with special reference to development of fatigue. Journal of "
            "Sports Sciences 21(7):519-528.",
            "Bangsbo, J., Mohr, M. & Krustrup, P. (2006). Physical and metabolic demands of "
            "training and match-play in the elite football player. Journal of Sports Sciences "
            "24(7):665-674.",
        ],
        "limitaciones": "Son partidos RECREATIVOS: no hay control de sustituciones, de tiempo "
                        "realmente jugado, ni de si el reloj siguió corriendo en el banco o el "
                        "descanso. Con muestreo de 2.74 s la velocidad es de baja calidad. Se "
                        "lee como serie contra sí misma, NUNCA como valor absoluto.",
        "guia": "decoupling",
    },

    # ------------------------------------------------------------ SUBJETIVA
    {
        "clave": "srpe",
        "nombre": "sRPE y RPE diferencial",
        "categoria": "subjetiva",
        "pregunta": "¿Cuánto me costó, y me costó de piernas o de pulmón?",
        "latex": r"\mathrm{sRPE}=\mathrm{RPE}\times T_{min}"
                 r"\\[6pt]"
                 r"\mathrm{sRPE}_L=\mathrm{RPE}_L\times T_{min},\qquad"
                 r"\mathrm{sRPE}_B=\mathrm{RPE}_B\times T_{min}"
                 r"\\[6pt]"
                 r"\Delta_{dRPE}=\mathrm{RPE}_L-\mathrm{RPE}_B",
        "variables": {r"\mathrm{RPE}_L": "esfuerzo percibido de PIERNAS (carga neuromuscular)",
                      r"\mathrm{RPE}_B": "esfuerzo percibido RESPIRATORIO (cardiorrespiratorio)",
                      "T_{min}": "duración de la sesión en minutos"},
        "parametros": {"escala": "CR10 de Foster (0-10)",
                       "cuál manda": "sRPE-piernas para lesión muscular · TRIMP para lo aeróbico",
                       "cuándo registrar": "dentro de los 30 min posteriores"},
        "implementacion": "src/garmin/metrics/wellness.py :: save_log(), drpe_series()",
        "referencias": [
            "Foster, C. et al. (2001). A new approach to monitoring exercise training. "
            "Journal of Strength and Conditioning Research 15(1):109-115.",
            "Los Arcos, A. et al. (2014). Rating of Muscular and Respiratory Perceived "
            "Exertion in Professional Soccer Players. JSCR 28(11):3280-3288. — tras partidos "
            "oficiales el RPE muscular SUPERA al respiratorio (7.4 vs 6.4).",
            "McLaren, S.J. et al. (2017). A detailed quantification of differential ratings "
            "of perceived exertion during team-sport training. JSAMS 20(3):290-295.",
        ],
        "limitaciones": "Es autorreporte: sesgo de expectativa y de ánimo, y se degrada si se "
                        "registra tarde. No hay evidencia de valor predictivo de lesión: es un "
                        "descriptor de carga, no un semáforo. Su valor aquí es que el dRPE es el "
                        "ÚNICO canal disponible para estimar carga mecánica con este hardware.",
        "guia": "drpe",
    },
    {
        "clave": "hooper",
        "nombre": "Hooper: z-score por ítem",
        "categoria": "subjetiva",
        "pregunta": "¿Cómo amanecí, comparado con mi propia normalidad?",
        "latex": r"z_j(t)=\frac{x_j(t)-\mu_{30,j}(t)}{\sigma_{30,j}(t)}"
                 r"\qquad j\in\{\text{sueño},\text{fatiga},\text{estrés},\text{DOMS}\}"
                 r"\\[6pt]"
                 r"\text{precaución}\iff \#\{j: z_j \le -1\}\ge 2",
        "variables": {"x_j": "puntuación del ítem j en escala 1-7 (7 = PEOR)",
                      r"\mu_{30},\sigma_{30}": "línea base móvil individual de 30 días"},
        "parametros": {"ventana": "30 días", "mínimo de observaciones": "14",
                       "regla": "conteo de ítems en rojo, NO un índice sumado"},
        "implementacion": "src/garmin/metrics/wellness.py :: hooper_zscores(), hooper_status()",
        "referencias": [
            "Hooper, S.L. et al. (1995). Markers for monitoring overtraining and recovery. "
            "Medicine & Science in Sports & Exercise 27(1):106-112.",
            "Saw, A.E., Main, L.C. & Gastin, P.B. (2016). Monitoring the athlete training "
            "response: subjective self-reported measures trump commonly used objective "
            "measures: a systematic review. British Journal of Sports Medicine 50(5):281-291.",
            "NO SUMAR — Duignan, C. et al. (2020). Single-item self-report measures of "
            "team-sport athlete wellbeing and their relationship with training load: a "
            "systematic review. Journal of Athletic Training 55(9):944-953.",
        ],
        "limitaciones": "El sumatorio Hooper NO tiene propiedades de medición aceptables como "
                        "constructo unitario: por eso se analizan los ítems por separado. La "
                        "escala invertida (7 = peor) se presta a errores de registro. Con "
                        "ventanas móviles la línea base deriva, así que un deterioro LENTO "
                        "puede volverse invisible.",
        "guia": "hooper",
    },
    {
        "clave": "ostrc",
        "nombre": "OSTRC-H2: severidad de problemas",
        "categoria": "subjetiva",
        "pregunta": "¿Esta molestia me está cambiando cómo entreno?",
        "latex": r"S=q_1+q_2+q_3+q_4\ \in[0,100]"
                 r"\\[6pt]"
                 r"q_1,q_4\in\{0,8,17,25\}\qquad q_2,q_3\in\{0,6,13,19,25\}"
                 r"\\[6pt]"
                 r"\text{sustancial}\iff q_2\ge 13\ \ \vee\ \ q_3\ge 13",
        "variables": {"q_1": "participación", "q_2": "volumen de entrenamiento",
                      "q_3": "rendimiento", "q_4": "síntomas"},
        "parametros": {"recuerdo": "7 días",
                       "aplicación": "solo a zonas con molestia media semanal ≥ 3/10",
                       "por qué condicional": "4 preguntas × 7 zonas = 28 semanales → abandono"},
        "implementacion": "src/garmin/metrics/wellness.py :: ostrc_severity(), ostrc_clasificacion()",
        "referencias": [
            "Clarsen, B., Myklebust, G. & Bahr, R. (2013). Development and validation of a "
            "new method for the registration of overuse injuries in sports injury "
            "epidemiology: the OSTRC Overuse Injury Questionnaire. British Journal of Sports "
            "Medicine 47(8):495-502.",
            "Clarsen, B. et al. (2014). The Oslo Sports Trauma Research Center questionnaire "
            "on health problems. British Journal of Sports Medicine 48(9):754-760.",
        ],
        "limitaciones": "CRÍTICO PARA UNA SOLA PERSONA: Franke et al. (2021) estimaron que el "
                        "cambio mínimo DETECTABLE individual del puntaje es ~35 puntos, mayor "
                        "que el cambio mínimo importante (~18.5). Solo los saltos grandes son "
                        "fiables; moverse 10-20 puntos es ruido.",
        "guia": "ostrc",
    },

    # -------------------------------------------------------------- CALIDAD
    {
        "clave": "limpieza_fc",
        "nombre": "Limpieza de frecuencia cardíaca",
        "categoria": "calidad",
        "pregunta": "¿En qué muestras de pulso se puede confiar?",
        "latex": r"\text{flag}=\begin{cases}"
                 r"\text{sin\_dato} & \mathrm{FC}=\varnothing\\"
                 r"\text{fuera\_de\_rango} & \mathrm{FC}<30\ \vee\ \mathrm{FC}>230\\"
                 r"\text{pico\_artefacto} & \dfrac{|\mathrm{FC}_t-\mathrm{FC}_{ref}|}{\Delta t}>30\\"
                 r"\text{válida} & \text{en otro caso}\end{cases}",
        "variables": {r"\mathrm{FC}_{ref}": "última muestra CONFIABLE previa, no la anterior cruda",
                      r"\Delta t": "segundos desde esa muestra confiable"},
        "parametros": {"rango plausible": "30-230 ppm", "salto máximo": "30 ppm/s",
                       "resultado real": "1.134 muestras marcadas de 243.543"},
        "implementacion": "src/garmin/transform/clean.py :: flag_heart_rate()",
        "referencias": [
            "Decisión de proyecto D-008, motivada por el registro con FC óptica de muñeca sin "
            "banda pectoral en deporte intermitente (D-006).",
        ],
        "limitaciones": "Se compara contra la última muestra confiable, no contra la anterior, "
                        "para que un artefacto no contamine a su vecino sano. El valor crudo "
                        "NUNCA se altera: solo se marca (invariante 2). Aún no se detectan "
                        "cascadas de picos consecutivos.",
        "guia": "fc_actividad",
    },
    {
        "clave": "limpieza_velocidad",
        "nombre": "Limpieza de velocidad",
        "categoria": "calidad",
        "pregunta": "¿En qué muestras de velocidad se puede confiar?",
        "latex": r"\text{flag}=\begin{cases}"
                 r"\text{fuera\_de\_rango} & v>9.0\ \mathrm{m/s}\ \vee\ v<0\\"
                 r"\text{salto\_imposible} & \left|\dfrac{v_t-v_{ref}}{\Delta t}\right|>6\ \mathrm{m/s^2}\\"
                 r"\text{sin\_gps} & \mathrm{lat}=\varnothing\ \vee\ \mathrm{lon}=\varnothing\\"
                 r"\text{válida} & \text{en otro caso}\end{cases}",
        "variables": {"v": "velocidad de la muestra", "v_{ref}": "última muestra confiable previa"},
        "parametros": {"techo": "9.0 m/s = 32.4 km/h", "aceleración máxima": "6 m/s²",
                       "por qué hace falta": "el crudo tiene p99 = 12.12 m/s y máximo 31.67 m/s "
                                             "(114 km/h) en fútbol"},
        "implementacion": "src/garmin/transform/clean.py :: flag_speed()",
        "referencias": [
            "Rawstorn, J.C. et al. (2014). Rapid directional change degrades GPS distance "
            "measurement validity during intermittent intensity running. PLoS ONE 9(4):e93693.",
            "Scott, M.T.U., Scott, T.J. & Kelly, V.G. (2016). The Validity and Reliability of "
            "Global Positioning Systems in Team Sport: A Brief Review. JSCR 30(5):1470-1490.",
        ],
        "limitaciones": "Marcar artefactos NO recupera la información perdida: la distancia "
                        "del partido sigue subestimada por los cambios de dirección. "
                        "'sin_gps' es una anotación de contexto y no invalida el valor por sí "
                        "sola, porque el firmware también deriva velocidad del acelerómetro.",
        "guia": "carga_externa",
    },
    {
        "clave": "gps_grade",
        "nombre": "Grado de la señal GPS (el portero)",
        "categoria": "calidad",
        "pregunta": "¿Esta sesión soporta métricas de alta velocidad?",
        "latex": r"\widetilde{\Delta t}=\mathrm{mediana}\left(\{t_{i+1}-t_i\}\right)"
                 r"\\[6pt]"
                 r"\mathrm{grado}=\begin{cases}"
                 r"\text{alta} & \widetilde{\Delta t}\le 1.2\ \mathrm{s}\\"
                 r"\text{media} & 1.2<\widetilde{\Delta t}\le 2.0\ \mathrm{s}\\"
                 r"\text{baja} & \widetilde{\Delta t}>2.0\ \mathrm{s}\\"
                 r"\text{sin\_gps} & \text{no hay lat/lon}\end{cases}",
        "variables": {r"\widetilde{\Delta t}": "intervalo mediano entre muestras de la sesión"},
        "parametros": {"perfil Fútbol de Jorge": "2.74 s → grado BAJO (Smart Recording)",
                       "perfiles de carrera": "1.00 s → grado ALTO",
                       "reparto real": "41 alta · 86 media · 43 baja · 23 sin GPS",
                       "consecuencia": "HSR y conteo de sprints SOLO con grado alto"},
        "implementacion": "src/garmin/metrics/external.py :: grade_gps()",
        "referencias": [
            "Scott, M.T.U., Scott, T.J. & Kelly, V.G. (2016). JSCR 30(5):1470-1490.",
            "Jennings, D. et al. (2010). The validity and reliability of GPS units for "
            "measuring distance in team sport specific running patterns. IJSPP 5(3):328-341.",
        ],
        "limitaciones": "Un sprint de fútbol dura 2-4 s: con 2.74 s entre muestras cae en una "
                        "o dos muestras y no se puede reconstruir. Por eso esas métricas quedan "
                        "en NULL en vez de dar un número inventado (D-016). El histórico no se "
                        "puede reparar: el reloj descartó las muestras en origen.",
        "guia": "carga_externa",
    },
    {
        "clave": "cobertura",
        "nombre": "Cobertura de FC de la sesión",
        "categoria": "calidad",
        "pregunta": "¿Qué tan completo está el pulso de esta sesión?",
        "latex": r"\mathrm{cobertura}=\frac{\#\{\text{muestras con FC válida}\}}"
                 r"{\#\{\text{muestras totales}\}}",
        "variables": {"numerador": "muestras que pasaron la limpieza D-008"},
        "parametros": {"mínimo para TRIMP integrado": "0.30",
                       "mínimo para índice de eficiencia": "0.90",
                       "mínimo para decoupling": "0.80"},
        "implementacion": "src/garmin/transform/clean.py :: hr_coverage()",
        "referencias": ["Decisión de proyecto D-008/D-011."],
        "limitaciones": "Una cobertura alta no garantiza que la FC sea correcta: solo que pasó "
                        "las reglas. Un sensor que se despega puede dar valores plausibles pero "
                        "erróneos.",
        "guia": "fc_actividad",
    },
]

# Índice por clave, para enlazar desde las guías ℹ️ y desde el dashboard.
POR_CLAVE = {f["clave"]: f for f in FORMULAS}


def por_categoria(cat: str) -> list[dict]:
    return [f for f in FORMULAS if f["categoria"] == cat]


def buscar(texto: str) -> list[dict]:
    """Busca en nombre, pregunta, referencias y limitaciones (sin distinguir tildes)."""
    if not texto:
        return FORMULAS
    t = _normalizar(texto)
    return [
        f for f in FORMULAS
        if t in _normalizar(
            " ".join([f["nombre"], f["pregunta"], f["limitaciones"],
                      f["implementacion"], " ".join(f["referencias"])])
        )
    ]


def _normalizar(s: str) -> str:
    tabla = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")
    return s.lower().translate(tabla)
