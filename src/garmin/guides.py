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
**Ratio agudo:crónico — señal de apoyo (ya no el oráculo)**

- **Cálculo:** carga media de los últimos 7 días ÷ carga media de los últimos 28.
  Responde: *¿cuánto hiciste esta semana comparado con lo que tu cuerpo esperaba?*
- **Bandas:** gris <0.8 subcarga (pierdes base y el regreso será más riesgoso) ·
  verde 0.8–1.3 zona óptima · amarillo 1.3–1.5 precaución · rojo >1.5.

**Por qué este panel bajó de categoría.** Durante años este fue EL número del
monitoreo de carga, y en este proyecto también lo fue. La literatura reciente lo
desarmó de dos maneras difíciles de rebatir. Primero, Impellizzeri y su equipo (2021)
reemplazaron la carga crónica —el denominador— por **números aleatorios**, y el ratio
siguió asociándose con lesiones igual de bien: la señal nunca estuvo en el cociente,
estaba en cuánta carga hiciste esta semana. Segundo, el único ensayo controlado que
existe (Dalen-Lorentsen 2021, 482 futbolistas juveniles seguidos 10 meses) no encontró
**ninguna** diferencia en problemas de salud al planificar usando el ACWR.

**Qué hacer con esto.** No lo borramos, porque sigue describiendo algo real: el
contraste entre lo que hiciste y lo que venías haciendo. Pero el panel que manda ahora
es el de **carga absoluta y percentil personal**, que está arriba. Este míralo después,
como contexto.

**Qué mirar:** las subidas a rojo tras semanas quietas son tu patrón histórico — el
partido no es el problema, el contraste sí.
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

**Tu situación, con los números en la mano.** En el último año tu media es de **5,4 h
por noche**, con el 82 % de las noches bajo 7 h y el 94 % bajo 8 h. Eso acumula una
deuda típica de ~12,7 h por semana (ver el panel de deuda de sueño). No es un detalle
menor: Milewski (2014) encontró que dormir menos de 8 h multiplicaba por 1,7 la
probabilidad de lesión, y von Rosen (2017) que dormir más de 8 h la reducía un 61 %.
De todo lo que este dashboard mide, esto es lo que más margen de mejora te ofrece.

**Y una cautela:** el reloj *sobreestima* el sueño — confunde estar quieto y despierto
con estar dormido. Tus 5,4 h medidas probablemente sean algo menos en la realidad.
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
- **Días seguidos fuera de tu banda** (la franja sombreada), no el día suelto.

**Cambió la regla de alerta, y para mejor.** Antes el sistema avisaba cuando tu pulso
subía **+5 ppm** sobre tu media de 28 días. El problema: tu variabilidad real es de
3,6 ppm, así que esos 5 ppm equivalían a 1,4 desviaciones — una red tan gruesa que
dejaba pasar casi todo. Ahora la banda es tu media móvil de 28 días **± medio desvío**
(el *smallest worthwhile change* de Hopkins), que en tu caso son ±1,8 ppm: entre tres
y cinco veces más sensible, y calculada con tus datos, no con los de otro.

Tu rango histórico: 38–69 ppm, con media ~52 — nivel de deportista recreativo sólido.
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

# ============================================================================
# Guías de los paneles nuevos (D-018 / D-019). Mismo formato que las de D-014:
# qué muestra · cómo se calcula · qué mirar · cuándo preocuparse.
# ============================================================================

GUIDES_NUEVAS: dict[str, str] = {
    "carga_absoluta": """
**Carga de la semana (absoluta) y tu percentil — el panel principal de carga**

- **Arriba:** cuánto TRIMP acumulaste en los últimos 7 días, con tu base de 28 días
  dividida en 4 como línea de comparación (para que ambas estén en "por semana").
- **Abajo:** en qué percentil cae esa semana respecto de todas tus semanas del último
  año. "Percentil 88" = cargaste más que el 88 % de tus semanas.

**Por qué este panel destronó al ACWR.** Durante años el cociente agudo:crónico fue
EL número del monitoreo de carga. En 2021, Impellizzeri y su equipo hicieron algo
demoledor: reemplazaron la carga crónica (el denominador) por **números aleatorios**,
y el ACWR siguió "prediciendo" lesiones igual de bien. Traducción: la señal nunca
estuvo en el cociente, estaba en cuánto cargaste esta semana. Y el único ensayo
controlado que existe (482 futbolistas juveniles, 10 meses) no encontró ninguna
diferencia al planificar con ACWR.

**Qué mirar:** la carga absoluta y su percentil. Un percentil sobre 90 sostenido
varias semanas es un salto real de exigencia, mires el ratio que mires.

**Por qué percentil y no un umbral fijo:** no existe un "400 TRIMP es mucho"
universal. Existe tu historia. El percentil la usa como vara.
""",
    "wow_change": """
**Cambio semana a semana**

- **Cálculo:** carga de los últimos 7 días ÷ carga de los 7 anteriores − 1. Si la
  semana previa fue casi cero, el porcentaje se omite (dividir por un número diminuto
  produce cifras absurdas: pasar de 5 a 50 TRIMP es "+900 %" y no significa nada).
- **La bandera** no usa un umbral copiado de otro deporte, sino **tu propia
  variabilidad**: ámbar si el salto supera 1,5 desviaciones de tus cambios habituales,
  rojo si supera 2. Cross (2016), en rugby profesional, encontró que los saltos de
  2 desviaciones elevaban las probabilidades de lesión.

**Qué mirar:** las semanas de regreso tras un parón. Es cuando el salto porcentual
se dispara sin que la carga absoluta parezca alta — y es tu patrón histórico.

**Ojo:** esto es una señal para planificar, no una predicción. Asociación no es causa.
""",
    "banda_personal": """
**Tu banda personal (y por qué reemplazó a la regla de "+5 pulsaciones")**

- **La franja sombreada** es tu referencia móvil de 28 días ± medio desvío estándar.
  En jerga: el *smallest worthwhile change*, el cambio más pequeño que vale la pena
  mirar. Los días fuera de banda se marcan con un rombo, no solo con color.
- **Antes** el sistema avisaba si tu FC en reposo subía 5 pulsaciones sobre tu media.
  Con tu variabilidad real (desvío de 3,6 ppm), esos 5 ppm equivalían a 1,4 desvíos:
  una red tan gruesa que dejaba pasar casi todo. Tu banda real es de ±1,8 ppm.

**Qué mirar:** no el día suelto, sino **cuántos días seguidos** llevas fuera. Una
noche mala le pasa a cualquiera; tres días seguidos por arriba es una conversación.

**Alerta si:** 3+ días consecutivos sobre la banda. Suele ser fatiga acumulada, mal
dormir o algo incubando — baja la intensidad hasta que vuelva adentro.
""",
    "deuda_sueno": """
**Deuda de sueño acumulada — probablemente tu hallazgo más importante**

- **Cálculo:** cada noche, lo que faltó para llegar a 8 h se suma. La deuda de 7 días
  es la suma de esos déficits. Una noche **sin dato no cuenta como cero**: si faltan
  demasiadas noches en la ventana, el número no se muestra y verás la cobertura.
- **Tu situación real:** promedio de 5,4 h por noche en el último año, con el 82 % de
  las noches bajo 7 h. Eso da una deuda típica de ~12,7 h por semana.

**Por qué importa tanto para lesiones.** Milewski (2014) encontró que dormir menos de
8 h multiplicaba por 1,7 la probabilidad de lesionarse; von Rosen (2017) reportó que
dormir más de 8 h entre semana reducía las probabilidades un 61 %. El efecto no es de
una noche: es la **restricción crónica** la que mueve la aguja. De todas las palancas
de prevención que tienes, esta es la más barata y la que más respaldo científico tiene.

**Cautela honesta:** el reloj *sobreestima* el sueño (confunde estar quieto y despierto
con dormir). Tus 5,4 h medidas probablemente son menos de 5,4 h reales.
""",
    "readiness": """
**Índice de disposición: cuatro dominios, no un número mágico**

- **Cómo se calcula:** cada variable se convierte en "cuántos desvíos estás de tu
  propia normal de 60 días" (z-score), y luego se agrupan en cuatro dominios:
  **autonómico** (FC en reposo, HRV), **sueño** (horas, puntaje), **carga** (balance
  TSB) y **subjetivo** (tu registro Hooper, si lo llenaste).
- **Por qué agrupar antes de promediar:** el puntaje de sueño, el estrés y el Body
  Battery salen todos del mismo motor de Garmin y están correlacionados entre sí.
  Promediarlos como si fueran independientes le daría triple peso a ese bloque.
- **Nunca se inventa un dato.** Si un dominio no tiene información ese día, se excluye
  y baja el contador. Con menos de 2 dominios no se muestra índice.

**Qué mirar:** el conteo de dominios en alerta, no el decimal del índice.

**Advertencia importante:** esto es un **conteo de banderas**, no un modelo de riesgo
calibrado. El umbral de −1 desvío es una convención práctica, no un corte clínico.
""",
    "carga_externa": """
**Carga externa: lo que sufrió el músculo, no lo que sufrió el corazón**

Son dos cosas distintas. El TRIMP mide **carga interna** (cuánto le costó a tu
corazón). La distancia y los metros por minuto miden **carga externa** (cuánto trabajo
mecánico hizo el músculo). Dos partidos con el mismo TRIMP pueden tener demandas
mecánicas muy distintas — y el tejido muscular se rompe por carga mecánica.

- **Distancia y metros/minuto:** disponibles y confiables como serie contra sí misma.
- **Distancia a alta velocidad y conteo de sprints:** **no disponibles en fútbol**, y
  no es un error del programa.

**Por qué no hay conteo de sprints.** Tu reloj, en el perfil Fútbol, está en modo de
grabación "inteligente": toma una muestra cada ~2,7 segundos en vez de cada segundo.
Un sprint de fútbol dura entre 2 y 4 segundos. Es como intentar filmar un colibrí
sacando una foto cada 3 segundos: no se puede reconstruir el movimiento. Preferimos
no mostrar un número antes que mostrar uno inventado.

**Cómo arreglarlo hacia adelante:** en el reloj, *Configuración > Sistema > Grabación
de datos > Cada segundo*. Desde ese día las sesiones nuevas se graban a 1 Hz y estas
métricas se activan solas. Los 96 partidos ya grabados no se pueden reparar: el reloj
descartó esas muestras en el momento de grabar.

**Además:** el GPS va en la muñeca, y el balanceo del brazo ensucia la velocidad. El
error típico de distancia es de 5-7 %, así que **diferencias menores al 10 % entre
sesiones no significan nada**. Y los valores absolutos no son comparables con los del
fútbol profesional, que se miden con dispositivos en la espalda a 10 Hz.
""",
    "eficiencia": """
**Índice de eficiencia: cuántos metros te rinde cada unidad de esfuerzo**

- **Cálculo:** metros recorridos ÷ TRIMP de la sesión. Sube cuando haces más trabajo
  con menos costo cardiovascular, que es la definición práctica de estar en forma.
- Solo se calcula con sesiones de calidad: serie completa de FC, cobertura ≥ 90 % y
  al menos 30 minutos. Con menos que eso el cociente es ruido.

**Qué mirar:** la tendencia de varias sesiones **del mismo tipo**. Comparar un fútbol
7 con un trote largo no dice nada; comparar tus últimos cinco partidos, sí.

**Alerta si:** cae bajo tu banda habitual tres sesiones seguidas mientras tu carga se
mantiene igual. Eso suele ser fatiga acumulada o forma en descenso.

**Nota metodológica:** el trabajo original (Akubat 2014) usa iTRIMP, que requiere un
perfil individual de lactato de laboratorio. Aquí se usa el TRIMP de Banister que ya
calculamos — es una desviación deliberada y documentada del paper.
""",
    "decoupling": """
**Fatiga intra-partido: cuánto más te cuesta la segunda mitad**

- **Cálculo:** se parte el partido en dos mitades por tiempo (tu reloj casi nunca
  marca el medio tiempo) y se compara el **coste cardíaco** de cada una: cuánto pulso
  te cuesta cada metro por segundo. Un valor de +8 % significa que la segunda mitad te
  costó un 8 % más de pulso por el mismo trabajo.
- La banda sombreada es tu rango habitual (±1 desvío de tus propios partidos).

**Por qué importa para lesiones.** Mohr, Krustrup y Bangsbo (2003) documentaron que el
rendimiento de carrera cae en la segunda mitad, y el tramo final del partido es donde
se concentran las lesiones musculares por fatiga. Los partidos con más decoupling son
tus candidatos a mayor riesgo.

**Cautela:** son partidos recreativos. El reloj no sabe si estuviste en el banco, si
te sustituyeron o si el descanso duró 5 o 20 minutos. Léelo como serie contra sí
misma, nunca como valor absoluto comparable con nadie.
""",
    "molestias_zonas": """
**Molestias por zona: hoy contra tu promedio de 28 días**

- Cada zona aparece con dos puntos unidos: el **círculo hueco** es tu promedio del
  último mes, el **punto lleno** es hoy. La distancia entre ambos es lo que cambió.
- Ordenadas por molestia actual, así que lo que más duele salta a la vista.

**Por qué no es un gráfico de radar.** El radar tienta mucho para "el mapa del cuerpo",
pero tiene tres defectos serios: el ojo compara mal longitudes orientadas en ángulos
distintos; el orden de los ejes es arbitrario y cambiarlo dibuja una figura totalmente
distinta con los mismos datos; y el área del polígono crece con el **cuadrado** del
valor, así que una molestia que pasa de 3 a 6 se ve cuatro veces peor, no dos.
Los puntos sobre una línea horizontal usan posición sobre escala común, que es la
forma que el ojo humano lee con más precisión.

**Qué mirar:** las zonas donde el punto lleno se alejó hacia la derecha del hueco.
Eso es empeoramiento reciente, que importa más que el nivel absoluto.
""",
    "hooper": """
**Registro matinal Hooper: cuatro preguntas, veinte segundos**

- Cuatro ítems en escala 1-7: calidad de sueño, fatiga, estrés y dolor muscular
  general. **Ojo con la escala: 7 es lo PEOR**, no lo mejor (así lo definió el
  instrumento original en 1995 y se respeta para poder comparar con la literatura).
- **No se suman en un puntaje único.** Cada ítem se compara con tu propia línea base
  de 30 días por separado, porque un mal dormir no se "compensa" con buen ánimo.
  La regla es de conteo: dos o más ítems en rojo = precaución.

**Por qué vale la pena aunque el reloj ya mida cosas.** Saw y sus colegas (2016)
revisaron 56 estudios y encontraron algo contraintuitivo: las medidas subjetivas
responden a la carga con **más** sensibilidad que muchas objetivas, y —clave— lo
subjetivo y lo objetivo típicamente **no correlacionan**. No son redundantes: son
información complementaria. El reloj sabe cuánto dormiste; solo tú sabes si dormiste
bien.

**Necesita tiempo:** hacen falta unas 3-4 semanas de registros antes de que las
comparaciones con tu línea base signifiquen algo.
""",
    "drpe": """
**RPE diferencial: piernas y pulmón por separado**

- En vez de un solo "cuánto te costó", dos preguntas: **cuánto te costó respirar**
  (esfuerzo cardiorrespiratorio) y **cuánto te pesaron las piernas** (esfuerzo
  neuromuscular). Cinco segundos extra de registro.

**Por qué es la métrica manual más valiosa de todo el proyecto.** Tu reloj mide muy
bien lo cardiovascular: la frecuencia cardíaca alimenta el TRIMP. Pero es
completamente **ciego a la carga mecánica**: las aceleraciones, los frenazos y los
cambios de dirección que rompen isquiotibiales y aductores no mueven el pulso de forma
proporcional al daño que hacen. Sin banda pectoral, sin acelerómetro en la espalda y
sin GPS a 10 Hz, el RPE de piernas es **el único canal disponible** para estimar esa
carga. Los Arcos (2014), con 21 futbolistas profesionales, encontró que tras los
partidos oficiales el esfuerzo muscular percibido supera al respiratorio (7,4 vs 6,4).

**Qué mirar:** el diferencial piernas − respiración a lo largo del tiempo. Si tus
piernas puntúan cada vez más alto que tu respiración en el mismo tipo de sesión, hay
carga mecánica acumulándose que el pulso no está viendo.

**Registra dentro de los 30 minutos posteriores:** más tarde, el recuerdo se degrada.
""",
    "ostrc": """
**OSTRC: vigilancia de problemas por sobrecarga**

- Cuatro preguntas de recuerdo semanal (¿afectó tu participación? ¿tu volumen? ¿tu
  rendimiento? ¿tuviste síntomas?) que producen un puntaje de severidad de 0 a 100.
- **Solo se te preguntan las zonas que ya vienen marcadas** con molestia media ≥3/10
  en la semana. Responder 4 preguntas × 7 zonas serían 28 preguntas semanales: eso se
  abandona en dos semanas. Así son típicamente 0-8 preguntas, ~1 minuto.

**Qué aporta sobre el 0-10 de molestias:** el 0-10 es un invento razonable pero no
validado; el OSTRC es el instrumento estándar de la epidemiología de lesiones por
sobreuso, y distingue "tengo una molestia" de "esta molestia me está cambiando cómo
entreno", que es la definición operativa de *problema sustancial*.

**Limitación seria para una sola persona:** Franke (2021) estimó que a nivel
individual el cambio mínimo **detectable** del puntaje es de unos 35 puntos, mayor que
el cambio mínimo importante (~18,5). Traducción: solo los saltos grandes son fiables.
Moverse de 20 a 30 puntos es ruido, no una tendencia.
""",
    "adherencia": """
**Adherencia: la métrica que decide si todo lo demás sirve**

- Muestra qué porcentaje de los últimos 30 días registraste, tu racha actual y cuántos
  segundos te toma en promedio llenar el formulario.

**Por qué es una métrica de primera clase y no un detalle.** La literatura sobre
cuestionarios de deportistas es clara en algo: el fracaso casi nunca es del
instrumento, es del proceso. Y el predictor número uno de abandono es **no recibir
devolución de los propios datos**. Un cuestionario perfecto sin registrar vale cero.

**El objetivo de diseño es duro:** menos de 30 segundos. Si el tiempo mediano de
registro empieza a subir, el formulario está creciendo demasiado y hay que recortarlo,
no pedirte más disciplina.

**Un detalle que importa:** "no registrado" no es lo mismo que "cero molestias". Los
días sin registro quedan vacíos, nunca se rellenan con ceros — un cero inventado
diluiría las señales reales.
""",
    "calendario_carga": """
**Calendario de carga**

- Cada columna es una semana, cada fila un día. El color es el TRIMP de ese día:
  cuanto más oscuro, más carga. Los huecos claros son días sin actividad.

**Qué mirar:** el **patrón**, no los días sueltos. Bloques oscuros seguidos de zonas
en blanco largas son la firma clásica del riesgo: cada regreso cae sobre un cuerpo que
perdió tolerancia. Lo protector es un moteado regular, 2-3 días con color por semana.

**Por qué un calendario y no una superficie 3D.** Fue una tentación real. Pero la
carga en el tiempo es un dato de una sola dimensión: dibujarlo como superficie obliga
a inventar un segundo eje, y a cambio se paga oclusión (los picos tapan los valles) y
distorsión de perspectiva. El calendario muestra exactamente lo mismo —día, semana,
carga— con las dos dimensiones de tiempo en posición y solo la magnitud en color.
""",
    "carga_vs_recuperacion": """
**Carga contra recuperación: cada punto es un día**

- **Eje horizontal:** cuán alta fue tu carga relativa. **Eje vertical:** cuán
  recuperado estabas, medido en desvíos de tu propia normal. **Color:** la peor
  molestia que registraste ese día. **Tamaño:** el volumen de entrenamiento.
- La franja verde vertical es tu zona de carga habitual; la línea horizontal es tu
  recuperación normal.

**El cuadrante que importa es el de abajo a la derecha:** carga alta con recuperación
baja. Von Rosen (2017), siguiendo 496 deportistas durante un año, encontró que la
combinación de carga en aumento con sueño en descenso daba el riesgo más alto de todo
su modelo (2,25 veces). No es la carga sola ni el descanso solo: es la coincidencia.

**Por qué cuatro variables en 2D y no un scatter 3D.** Un estudio comparó 816
gráficos de dispersión y concluyó que el 3D interactivo "rara vez ayuda y a menudo
perjudica": sin una línea de referencia entre el punto y los ejes, la profundidad no
se puede leer, hay que rotar, y al rotar se pierde lo que estabas viendo. Aquí las dos
variables más importantes están en posición —lo que el ojo lee mejor— y las otras dos
viajan en color y tamaño.
""",
    "ruta_3d": """
**Recorrido en 3D — el único 3D que se ganó su lugar**

- Tu ruta dibujada con longitud, latitud y altitud reales, coloreada por pulso.
  Se puede girar con el mouse.

**Por qué este 3D sí y los otros no.** La regla del proyecto no prohíbe el 3D:
lo condiciona. Un cerro **es** tridimensional — latitud, longitud y altura no son una
codificación inventada, son las tres dimensiones del espacio. St. John y colegas
(2001), en seis experimentos con terreno natural, mostraron que el 3D **supera** al 2D
cuando la tarea es entender la *forma* de algo tridimensional, y que el 2D gana cuando
hay que juzgar posiciones o distancias exactas. Por eso este gráfico **se mira** y el
perfil de altitud de al lado **se lee**.

**Dos advertencias:**
- Los ejes están a escala real (`aspectmode='data'`) a propósito. Si dejáramos que la
  altura se autoescalara, una loma de 40 metros se vería como el Everest — el clásico
  "factor de mentira" de un gráfico.
- La altitud del reloj tiene varios metros de error, y en fútbol este gráfico no
  aparece: una cancha es plana y sería puro ruido.
""",
    "exploracion_3d": """
**Exploración en 3D — un juguete, y está bien que lo sea**

- Carga, recuperación y molestia en tres ejes, girable. Cada punto es un día.

**Honestidad ante todo: la evidencia está en contra de este gráfico.** Sedlmair,
Munzner y Tory (2013) compararon 816 gráficos de dispersión de 75 conjuntos de datos
en 2D, 3D interactivo y matrices de paneles, y concluyeron que el 3D "rara vez ayuda y
a menudo perjudica". El problema de fondo: en un espacio 3D proyectado en una pantalla
plana no hay línea de referencia entre el punto y los ejes, así que la profundidad no
se lee — hay que rotar. Y un "grupo" que parece formarse puede ser un artefacto del
ángulo de cámara.

**Entonces por qué existe.** Porque ese estudio medía una tarea concreta —juzgar si
unos grupos se separan— y no medía otra cosa que también es legítima: construir
intuición sobre tus propios datos, jugando. Girar la nube y ver dónde caen tus días
malos tiene valor exploratorio.

**La regla, entonces:** de aquí no se leen valores, y este gráfico **nunca** alimenta
las recomendaciones ni la tarjeta "¿Puedo jugar hoy?". Para números, los 2D de arriba.
""",
    "coordenadas_paralelas": """
**Coordenadas paralelas — el sustituto honesto del "3D rotable"**

- Cada día es una línea que cruza todos los ejes verticales. Arrastrando el mouse
  sobre un eje se filtran los demás (se llama *brushing*): por ejemplo, selecciona
  solo los días de molestia alta y mira por dónde pasaban esos días en carga y sueño.

**Para qué sirve:** ver cinco o seis variables a la vez sin perder la capacidad de
leer valores, que es justo lo que el 3D no permite.

**Un detalle deliberado:** el orden de los ejes es **fijo** —carga → recuperación →
síntoma— y está documentado. Igual que en el gráfico de radar, cambiar el orden cambia
por completo el dibujo; dejarlo al azar sería cometer el mismo pecado que le criticamos
al radar.

**Cuesta un poco al principio:** es un tipo de gráfico poco familiar. Vale la pena
mirarlo un par de veces antes de decidir si te sirve.
""",
}

GUIDES.update(GUIDES_NUEVAS)
