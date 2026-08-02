"""Guías por panel (D-014): explicación técnica e intuitiva de cada gráfico.

Se muestran con el botón ℹ️ junto a cada panel. Formato: qué muestra, cómo se
calcula, qué mirar y cuándo preocuparse.
"""

GUIDES: dict[str, str] = {
    # ------------------------------------------------------------- Semana y carga
    "kpis_carga": """
**Los 4 números de tu estado de entrenamiento**

- **Forma (CTL):** promedio ponderado de tu carga de las últimas ~6 semanas (EWMA 42 días).
  Es tu "fondo de ahorro" de fitness: sube lento con constancia y baja lento al parar.
- **Fatiga (ATL):** lo mismo pero de los últimos 7 días. Sube y baja rápido.
- **Balance (TSB) = Forma − Fatiga:** positivo = fresco (ideal pre-partido);
  muy negativo (< −25) = fatiga acumulada; positivo por semanas = estás perdiendo base.
- **ACWR:** ver el panel del semáforo.

**Qué mirar:** que la Forma suba de a poco a lo largo de meses; que la Fatiga oscile
sin quedarse semanas en cero (abandono) ni al doble de tu Forma (sobrecarga).
""",
    "carga_diaria": """
**Carga diaria (TRIMP) y tendencias**

- **Barras azules:** la dosis de cada día — TRIMP de Banister: minutos × intensidad
  cardíaca, con peso exponencial (30 min intensos cargan más que 60 suaves).
  Se calcula muestra a muestra con tu FC válida (limpieza D-008).
- **Línea naranja (ATL):** fatiga — media móvil exponencial 7 días.
- **Línea verde (CTL):** forma — media móvil exponencial 42 días.

**Qué mirar:** el patrón de las barras. Dosis regulares (2-3 por semana) hacen subir
la verde de forma sostenida. Picos aislados con valles largos = la firma clásica del
riesgo: cada partido cae sobre un cuerpo desacostumbrado.

**Alerta si:** una barra supera ~2× tu barra típica reciente, o pasas >7 días en cero.
""",
    "acwr": """
**Ratio agudo:crónico — el semáforo de lesión**

- **Cálculo:** carga media de los últimos 7 días ÷ carga media de los últimos 28.
  Responde: *¿cuánto hiciste esta semana comparado con lo que tu cuerpo esperaba?*
- **Bandas:** gris <0.8 subcarga (pierdes base y el regreso será más riesgoso) ·
  verde 0.8–1.3 zona óptima · amarillo 1.3–1.5 precaución · rojo >1.5 riesgo alto
  (la evidencia en deportes de equipo asocia esta zona con más lesiones musculares
  y tendinosas en los días siguientes).

**Qué mirar:** cuánto tiempo pasas en verde. Las subidas a rojo tras semanas quietas
son tu patrón histórico — el partido no es el problema, el contraste sí.

**Evolución sana:** línea que ondula dentro de la banda verde, sin dientes de sierra.
""",
    "semanal_deporte": """
**TRIMP semanal por deporte**

Suma de tu carga por semana, apilada por deporte (color fijo por deporte).

**Qué mirar:**
- La **altura total** = tu volumen semanal. Cambios de más del ~30% de una semana a
  otra son los que dispara el semáforo.
- La **mezcla de colores**: tus rachas multideporte históricamente coinciden con
  semanas en banda verde — el volumen suave (caminatas, senderismo) construye base
  aeróbica que amortigua los partidos.

**Alerta si:** semanas monocolor intenso alternadas con semanas vacías.
""",
    "recomendaciones": """
**¿De dónde salen estas recomendaciones?**

De un motor de **reglas transparentes** (sin caja negra) que evalúa tus números de
hoy: ACWR, días desde la última actividad, balance TSB, monotonía de la última
semana, HRV vs tu banda, sueño reciente y tendencia de tu FC en reposo. Cada
recomendación cita el dato que la disparó — puedes verificarla en los paneles.

Las reglas vienen de la literatura de ciencias del deporte (Gabbett: ACWR y parones;
Foster: monotonía; consenso sobre sueño <7 h y riesgo). **No es consejo médico**: el
sistema ve tu carga, no tu cuerpo. Dolor real manda sobre cualquier número.
""",
    # -------------------------------------------------------------- Recuperación
    "kpis_recuperacion": """
**Tu estado de recuperación de hoy**

- **FC en reposo:** el valor oficial de Garmin del último día con dato. Tu rango
  histórico es 38–69 ppm. Más bajo = mejor recuperado, en general.
- **Último sueño:** horas dormidas (profundo+ligero+REM) y el puntaje 0-100 de Garmin.
- **HRV última noche:** variabilidad RMSSD en ms — sensibilidad del sistema nervioso.
- **Estado HRV:** cómo se compara con TU banda personal (no con tablas genéricas).

**Qué mirar:** la combinación. Un mal dato aislado no dice nada; FC reposo alta +
HRV bajo + mal sueño el mismo día = señal seria de parar o suavizar.
""",
    "sueno": """
**Sueño por etapas**

Cada barra es una noche: profundo (azul oscuro, reparación física), REM (azul,
consolidación mental), ligero (celeste) y despierto (gris). El puntaje 0-100 de
Garmin va en el hover.

**Qué mirar:**
- **Duración total:** 7–9 h sostenidas. Tu media histórica está visible al comparar eras.
- **Profundo:** idealmente >1 h por noche; cae con estrés, alcohol y acostarse tarde.
- **Huecos** = noches sin reloj (no noches sin dormir).

**Por qué importa aquí:** dormir <7 h de forma sostenida se asocia a mayor riesgo de
lesión y peor recuperación de carga — es la palanca de prevención más barata que tienes.
""",
    "hrv": """
**HRV nocturno (RMSSD) vs tu banda personal**

Variabilidad entre latidos durante el sueño, en milisegundos. Contraintuitivo pero
clave: **más variabilidad = mejor** (sistema nervioso flexible, listo para cargar).

- **Banda verde:** el rango "equilibrado" que Garmin calibró para TI (~42–59 ms).
- **Bajo la banda:** recuperación incompleta — típico tras partidos intensos, mal
  sueño, alcohol o enfermedad incubando. Tu caída a 33 ms tras el pico de carga de
  julio es el ejemplo de libro.

**Nota de cobertura (verificado):** tu reloj empezó a registrar HRV el 18-jul-2026;
antes este dato no existía en ninguna fuente. Crece noche a noche desde ahora.
""",
    "fc_reposo": """
**FC en reposo diaria**

El pulso mínimo estable del día (dato oficial de Garmin; si falta, usamos la mínima
del monitoreo continuo del reloj).

**Qué mirar:**
- **Tendencia de meses:** si baja lentamente, tu base aeróbica mejora.
- **Saltos de +5–8 ppm sobre tu media de las últimas semanas** durante 2-3 días:
  fatiga acumulada, mal sueño o infección en camino — baja la intensidad esos días.

Tu rango histórico: 38–69 ppm, con media ~50 — nivel de deportista recreativo sólido.
""",
    "estres": """
**Estrés medio diario**

Índice 0-100 de Garmin, derivado de tu HRV durante el día (no es un cuestionario:
es fisiología). <25 reposo · 25-50 bajo · 50-75 medio · >75 alto.

**Qué mirar:** los promedios sostenidos, no los picos sueltos (un partido dispara
"estrés" fisiológico normal). Semanas con media >45 + mal sueño = terreno fértil
para lesiones y enfermedad; considera bajar una dosis de entrenamiento.
""",
    "vo2max": """
**VO2max (medición de Garmin)**

Máximo consumo de oxígeno estimado (ml/kg/min) — el estándar de capacidad aeróbica.
Garmin lo estima en tus trotes con GPS + FC. Tu rango: 45–50, un nivel bueno para
deportista recreativo (percentil alto para tu grupo etario).

**Qué mirar:** la tendencia por trimestres, no el valor del día. Sube con volumen
aeróbico constante (zona 2) y baja con inactividad — compárala con tus eras de carga
en el panel semanal. Solo se actualiza cuando corres (no en fútbol), por eso hay
períodos sin puntos.
""",
    "puedo_jugar": """
**¿Puedo jugar hoy? — el semáforo pre-partido**

Síntesis de 3 factores, pensada para leerse en 5 segundos antes de decidir
cuántos minutos jugar:

- **Carga:** ¿tu ACWR está en banda y sin parones largos? (>10 días sin actividad
  o ACWR >1.5 = ⛔).
- **Recuperación:** sueño de anoche, HRV vs tu banda y FC reposo vs tu norma.
- **Molestias:** lo que TÚ registraste (últimos 7 días). Dolor 7+/10 = ⛔;
  molestia 4-6 = ⚠️.

**Cómo usarlo:** 🟢 juega normal · 🟡 juega, pero calienta largo, evita el 100% en
sprints tempranos y considera no jugar completo · 🔴 el partido de hoy te cuesta
más de lo que te da — modera minutos o descansa. El semáforo aconseja, no decide:
tu cuerpo tiene la última palabra.
""",
    "registro": """
**Registro subjetivo (RPE + molestias)**

Los sensores miden tu corazón; esto mide lo que solo tú sabes.

- **RPE (0-10):** cuán dura se SINTIÓ la sesión (escala de Foster). Con la duración
  produce la carga sRPE (RPE × minutos), una segunda vara junto al TRIMP: cuando el
  sRPE dice "durísimo" y la FC dice "normal", hay fatiga escondida.
- **Molestias por zona (0-10):** la señal MÁS temprana de lesión que existe.
  0-3 = ruido normal · 4-6 = relevante (el motor lo vigila) · 7+ = dolor serio
  (el motor lo trata como alerta).

**El hábito:** 30 segundos después de cada sesión, idealmente el mismo día.
La constancia vale más que la precisión — reporta lo que sientas, sin pensarlo tanto.
""",
    # ------------------------------------------------------------------ Detalle
    "fc_actividad": """
**Frecuencia cardíaca de la sesión**

Tu FC segundo a segundo. Las ✕ grises son muestras descartadas por las reglas de
calidad (picos imposibles, rangos no fisiológicos) — se marcan, jamás se borran, y
no entran al cálculo de carga.

**Qué mirar en fútbol:** perfil dientes de sierra (jugadas intensas / pausas) y
cuánto tiempo sostienes >85% de tu FCmax (182). **En trote:** deriva ascendente con
ritmo constante = fatiga/calor (desacople cardíaco).
""",
    "ritmo": """
**Ritmo / velocidad**

En trote y caminata: ritmo en min/km con el **eje invertido a propósito** (arriba =
más rápido, porque 4:30 es mejor que 6:00). En fútbol y otros: velocidad en km/h.

**Qué mirar en fútbol:** la densidad de picos = sprints repetidos; su decaimiento en
el segundo tiempo es un proxy de fatiga. **En trote:** la estabilidad del ritmo a FC
constante — si el ritmo cae con la misma FC, ahí está tu límite aeróbico actual.
""",
    "zonas": """
**Tiempo en zona (Z1–Z5)**

Minutos de la sesión en cada franja de %FCmax (Z1 50-60% … Z5 90-100%), calculadas
con tu FCmax estimada de los datos (182 ppm, ajustable en config/settings.yaml).

**Qué mirar:** el perfil según el objetivo del día. Partido típico tuyo: mucho Z3-Z4
y ráfagas Z5. Trote de base saludable: mayoría Z2. Si TODAS tus sesiones viven en
Z4-Z5, falta el volumen suave que construye base — el famoso 80/20 (80% suave,
20% intenso) es la referencia en deportes de resistencia.
""",
}
