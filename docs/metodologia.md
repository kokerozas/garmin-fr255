# Metodología científica del proyecto (D-016)

**Regla del proyecto:** toda métrica, análisis o visualización avanzada implementada
aquí sigue un framework publicado en la literatura de ciencias del deporte.
**No se inventa nada.** Cada métrica futura entra SOLO con su referencia primaria
anotada en este documento, junto a sus limitaciones conocidas.

---

## Métricas implementadas y su base

### TRIMP (impulso de entrenamiento) — carga interna por sesión
- **Fórmula:** TRIMP = Σ Δt(min) · HRr · 0.64 · e^(1.92·HRr), con HRr = (FC − FCrep)/(FCmax − FCrep), integrado muestra a muestra sobre FC válida (coeficientes masculinos).
- **Referencia:** Banister, E.W. (1991) *Modeling elite athletic performance*, en Physiological Testing of the High-Performance Athlete; coeficientes exponenciales de Morton, Fitz-Clarke & Banister (1990), J Appl Physiol.
- **Por qué aquí:** unifica la carga entre deportes usando solo FC (D-006: fútbol y running no comparten ritmo). Limitación: FC de muñeca en fútbol tiene artefactos → limpieza D-008 previa.

### ATL / CTL / TSB (fitness–fatiga)
- **Fórmula:** medias móviles exponenciales del TRIMP diario, span 7 días (ATL, "fatiga") y 42 días (CTL, "forma"); TSB = CTL − ATL.
- **Referencia:** modelo fitness-fatiga de Banister (1991); operacionalización tipo Performance Management Chart (Allen & Coggan, *Training and Racing with a Power Meter*). Uso de EWMA para cargas: Williams et al. (2017), Br J Sports Med.

### ACWR (ratio agudo:crónico) — el semáforo
- **Fórmula:** media móvil 7 días ÷ media móvil 28 días del TRIMP diario. Bandas: <0.8 subcarga · 0.8–1.3 óptima · 1.3–1.5 precaución · >1.5 riesgo alto.
- **Referencias:** Hulin et al. (2016), Br J Sports Med; Gabbett (2016), Br J Sports Med — *the training-injury prevention paradox*.
- **Limitaciones (documentadas a propósito):** el ACWR tiene críticas metodológicas serias — acoplamiento matemático, evidencia asociativa y no causal, heterogeneidad entre deportes (Impellizzeri et al., 2020, Int J Sports Physiol Perform). **Por eso en este proyecto el ACWR es una SEÑAL para conversar con el cuerpo, no un oráculo** — siempre acompañado de recuperación y molestias (tarjeta "¿Puedo jugar hoy?").

### Monotonía y strain semanales
- **Fórmula:** monotonía = media(TRIMP diario 7d) / DE(TRIMP diario 7d); strain = carga semanal × monotonía. Umbral de atención: monotonía > 2.0.
- **Referencia:** Foster (1998), Med Sci Sports Exerc — *Monitoring training in athletes with reference to overtraining syndrome*.

### sRPE (carga por esfuerzo percibido)
- **Fórmula:** sRPE = RPE (escala 0-10) × duración (min).
- **Referencia:** Foster et al. (2001), J Strength Cond Res — *A new approach to monitoring exercise training*. La divergencia sistemática entre sRPE y carga por FC es una señal de fatiga/estrés no capturado por el pulso.

### Zonas de FC y tiempo en zona
- **Fórmula:** Z1–Z5 en cortes 50/60/70/80/90 %FCmax; FCmax estimada de los propios datos (percentil 99.7 de FC válida) con override manual (D-007).
- **Referencia:** convención de prescripción por %FCmax (ACSM, *Guidelines for Exercise Testing and Prescription*). La referencia de distribución 80/20 (polarizado) para resistencia: Seiler (2010), Int J Sports Physiol Perform.

### HRV nocturno (RMSSD) vs banda personal
- **Interpretación:** RMSSD nocturno comparado contra la banda individual (calibrada por Garmin); valores bajo la banda tras carga alta = recuperación incompleta. Se privilegian tendencias multi-día sobre valores sueltos.
- **Referencias:** Plews et al. (2013), Sports Med; Buchheit (2014), Front Physiol — *Monitoring training status with HR measures: do all roads lead to Rome?*

### FC en reposo elevada como señal
- **Regla:** media 7 días > media de los 28 previos + 5 ppm → fatiga/enfermedad posible.
- **Referencia:** Buchheit (2014), Front Physiol (la FC de reposo elevada como marcador de estado, con la misma cautela de tendencia vs valor único).

### Sueño y riesgo de lesión
- **Regla:** media reciente < 6.5–7 h → recomendación de atención.
- **Referencias:** Milewski et al. (2014), J Pediatr Orthop — horas de sueño y tasa de lesión en deportistas jóvenes; von Rosen et al. (2017), Scand J Med Sci Sports.

### Molestias autorreportadas por zona
- **Racional:** los cuestionarios de bienestar/molestias autorreportados responden a la carga aguda con más sensibilidad que muchas medidas objetivas; el dolor localizado recurrente es señal temprana estándar en el monitoreo de disponibilidad del jugador.
- **Referencia:** Saw, Main & Gastin (2016), Br J Sports Med — *Monitoring the athlete training response: subjective self-reported measures trump commonly used objective measures*. Registro por zonas inspirado en cuestionarios de disponibilidad tipo OSTRC (Clarsen et al., 2013, Br J Sports Med).

---

## Reglas de incorporación futura

1. **Antes de programar una métrica nueva:** anotar aquí fórmula + referencia primaria + limitaciones. Sin referencia, no se implementa.
2. Las **guías ℹ️** del dashboard deben ser consistentes con lo escrito aquí.
3. Los valores de Garmin (VO2max, Training Effect, HRV status) se tratan como **mediciones de un tercero con metodología parcialmente cerrada**: se usan como referencia y tendencia, no como verdad absoluta (D-007).
4. Las recomendaciones son **señales educativas, no prescripción médica** — el disclaimer es obligatorio en la interfaz.

---

# Ampliación de agosto 2026 (D-017 · D-018 · D-019)

Esta sección documenta las métricas y criterios incorporados tras una revisión de
literatura 2013-2025. Sigue la misma regla: fórmula, referencia primaria,
limitaciones, y cómo se presenta.

## 1. Carga absoluta y el ocaso del ACWR

### Por qué el ACWR dejó de ser el número principal

Es el cambio conceptual más importante de esta iteración, y conviene entenderlo bien
porque contradice lo que este mismo documento afirmaba antes.

- **Impellizzeri et al. (2021)**, *What Role Do Chronic Workloads Play in the Acute to
  Chronic Workload Ratio? Time to Dismiss ACWR and Its Underlying Theory*,
  Sports Medicine 51(3):581-592. Los autores reemplazaron la carga crónica —el
  denominador del ratio— por **valores aleatorios**, y el ACWR siguió asociándose con
  lesión igual de bien. Si el denominador puede ser ruido sin que la asociación se
  degrade, la señal nunca estuvo en el cociente: estaba en la carga aguda y en el
  tiempo de exposición.
- **Lolli et al. (2019)**, BJSM 53(15):921-922: el acoplamiento matemático entre
  numerador y denominador genera correlación espuria por construcción.
- **Impellizzeri et al. (2020)**, IJSPP 15(6):907-913: problemas conceptuales y
  errores fundamentales en el uso del ratio.
- **Dalen-Lorentsen et al. (2021)**, BJSM: el **único ensayo controlado** existente
  (482 futbolistas juveniles de élite, 10 meses) no encontró diferencia en problemas
  de salud al planificar la carga con principios ACWR.

**Consecuencia en este proyecto:** el ACWR **no se elimina** —sigue describiendo el
contraste entre lo reciente y lo habitual, que es real— pero se degrada a señal
secundaria y se mueve a un panel plegable. El panel principal pasa a ser la carga
absoluta con su percentil personal.

### Carga aguda absoluta y percentil personal
- **Fórmula:** `load_7d` = suma móvil de TRIMP de 7 días (también 14, 21 y 28).
  `load_7d_pct` = percentil de esa suma dentro de los últimos 365 días
  (`rolling(365, min_periods=120).rank(pct=True)`).
- **Racional:** no existe un umbral universal de "cuánto TRIMP es mucho". El percentil
  usa la propia historia del atleta como vara, que es lo único defendible en n=1.
- **Limitación:** el percentil asume que la distribución histórica sigue siendo un buen
  referente; se rompe tras lesiones largas o cambios de temporada. Y las unidades TRIMP
  no son comparables con umbrales publicados, que están en AU de sRPE o metros de GPS.

### Cambio semana a semana y cargas acumuladas
- **Fórmula:** `wow_change` = load_7d / load_7d(t−7) − 1, con guarda que devuelve
  nulo cuando la semana previa fue muy baja (dividir por casi cero produce cifras
  absurdas). Bandera individualizada: ámbar si |cambio| > 1.5 × DE de los propios
  cambios históricos, rojo si > 2 × DE.
- **Referencias:** **Rogalski et al. (2013)**, J Sci Med Sport 16(6):499-503;
  **Cross et al. (2016)**, IJSPP 11(3):350-355 — en 173 jugadores de rugby
  profesional, un aumento de 2 DE en el cambio semanal elevaba las odds de lesión
  (OR 1.58), y la carga acumulada a 4 semanas mostraba relación **no lineal**
  (riesgo reducido en la banda media, elevado en los extremos).
  **Gabbett (2016)**, BJSM 50(5):273-280, popularizó la regla del 15 %.
- **Por qué el umbral es individualizado:** los AU de rugby no son transferibles.
  Se operacionaliza el "2 DE" de Cross con la variabilidad propia de Jorge.
- **Limitación:** asociación no es predicción (Fanchini 2018). Con muchos días de
  TRIMP cero —deporte amateur, semanas irregulares— el porcentaje es inestable.

### Monotonía y strain como serie diaria
- **Fórmula:** monotonía = media(TRIMP 7d) / DE(TRIMP 7d); strain = load_7d × monotonía.
  Ahora se calculan como serie móvil diaria, no solo puntualmente.
- **Referencia:** **Foster (1998)**, Med Sci Sports Exerc 30(7):1164-1168.
- **Detalle de implementación:** con DE = 0 (semana de ceros o perfectamente plana) el
  resultado es nulo, no infinito.

### Índice de eficiencia (carga externa : interna)
- **Fórmula:** metros ÷ TRIMP de la sesión. Solo con `trimp_method='samples'`,
  cobertura de FC ≥ 0.9, duración ≥ 30 min y distancia presente.
- **Referencia:** **Akubat et al. (2014)**, *Integrating the internal and external
  training loads in soccer*, IJSPP 9(3):457-462.
- **Desviación declarada:** el trabajo original usa iTRIMP, que exige un perfil
  individual FC-lactato de laboratorio inexistente aquí. Se sustituye por el TRIMP de
  Banister ya implementado.
- **Limitación:** es un ratio y hereda el problema de acoplamiento matemático ya
  descrito. Solo comparable entre sesiones del mismo deporte y formato similar.

## 2. Recuperación con bandas personales

### Smallest worthwhile change para FC en reposo
- **Fórmula:** banda = media móvil 28 días ± 0.5 × DE de esa ventana, con mínimo de
  días válidos. Estado ∈ {bajo_banda, dentro, sobre_banda} y contador de días
  consecutivos fuera.
- **Referencias:** **Hopkins (2000)**, *Measures of reliability in sports medicine and
  science*, Sports Medicine 30(1):1-15 (SWC = 0.5 × DE intraindividual);
  **Buchheit (2014)**, *Monitoring training status with HR measures: do all roads lead
  to Rome?*, Frontiers in Physiology 5:73.
- **Por qué se jubiló la regla anterior:** el proyecto usaba "+5 ppm sobre la media de
  28 días". Con la DE real de Jorge (3.6 ppm) eso equivale a **1.4 desviaciones**, es
  decir entre 3 y 5 veces más insensible que el estándar de la literatura. Su banda
  real es de ±1.8 ppm.
- **Limitación:** la FC en reposo de Garmin es un valor propietario derivado de PPG de
  muñeca, no un promedio nocturno auditable; su error de medida no es el CV de
  laboratorio de Buchheit. La cobertura tiene huecos (90 % con lagunas), así que toda
  media móvil exige un mínimo de días válidos.

### Deuda de sueño acumulada
- **Fórmula:** deuda(t) = Σ max(0, necesidad − horas dormidas) en ventanas de 7, 14 y
  28 días. Necesidad configurable, default 8.0 h. Se expone además la **cobertura**
  (% de noches con dato) de cada ventana.
- **Regla no negociable:** una noche **sin dato no es deuda cero**. Si la ventana no
  alcanza el mínimo de noches válidas, el resultado es nulo, no un número optimista.
- **Referencias:** **Milewski et al. (2014)**, J Pediatr Orthop 34(2):129-133 (dormir
  <8 h multiplicaba por 1.7 la probabilidad de lesión en deportistas adolescentes);
  **von Rosen et al. (2017)**, Scand J Med Sci Sports 27(11):1364-1371 (dormir >8 h
  entre semana reducía las odds de lesión un 61 %, OR 0.39); **Gao et al. (2019)**,
  meta-análisis, OR 1.58 para falta crónica de sueño.
- **Hallazgo en los datos de Jorge:** media de 5.41 ± 1.63 h en el último año (n=169),
  82 % de noches bajo 7 h, 94 % bajo 8 h; deuda media de ~12.7 h por semana (n=521
  ventanas válidas), peor caso 29.8 h.
- **Limitación central:** el sueño medido por reloj de muñeca **sobreestima** frente a
  polisomnografía, porque clasifica vigilia tranquila como sueño. Las 5.4 h medidas son
  probablemente menos en la realidad — lo que agrava el hallazgo, no lo relativiza.

### Ln rMSSD con puerta de validez
- **Fórmula:** media móvil de 7 días de Ln(rMSSD) y su coeficiente de variación.
- **Referencia:** **Plews et al. (2013)**, *Training adaptation and heart rate
  variability in elite endurance athletes*, Sports Medicine 43(9):773-781.
- **Puerta de validez explícita:** mínimo 3 noches válidas por semana y ≥21 días de
  historia. Por debajo de eso la función devuelve nulo **con el motivo y cuántos días
  faltan**, en lugar de dibujar ruido. Con el HRV nacido el 18-jul-2026, esta métrica
  todavía no es interpretable y el sistema lo dice explícitamente.

## 3. Índice de disposición por dominios

- **Fórmula:** z = (x − media móvil 60 d) / DE móvil, invertido en las variables donde
  "más es peor" (FC en reposo, estrés). Los z se agrupan en cuatro **dominios**
  —autonómico, sueño, carga, subjetivo— y el índice es el promedio de los dominios
  disponibles, con `n_dominios` explícito. Con menos de 2 dominios no se calcula índice.
- **Referencias:** **Buchheit (2014)**, Front Physiol 5:73; **Thornton et al. (2019)**,
  *Developing Athlete Monitoring Systems in Team Sports: Data Analysis and
  Visualization*, IJSPP 14(6):698-705; **Robertson, Bartlett & Gastin (2017)**,
  *Red, Amber, or Green? Athlete Monitoring in Team Sport: The Need for
  Decision-Support Systems*, IJSPP 12(Suppl 2):S2-73-S2-79; **Saw, Main & Gastin
  (2016)**, BJSM 50(5):281-291.
- **Por qué se agrupa por dominio antes de promediar:** `sleep_score`, `stress_avg` y
  Body Battery salen del **mismo motor propietario de Garmin** y están correlacionados
  entre sí. Promediarlos como variables independientes daría triple peso implícito a
  ese bloque.
- **Nunca se imputa:** si falta un dato ese día, la variable se excluye y baja el
  contador de dominios. Un promedio de una sola cosa no es un compuesto.
- **Limitaciones declaradas en la interfaz:** z ≤ −1 es una **convención práctica, no
  un corte clínico validado**; y un **conteo de banderas no es un modelo de riesgo
  calibrado**. Con varias variables se generan falsas alarmas por azar; agrupar por
  dominio lo mitiga pero no lo elimina.

## 4. Carga externa con GPS de muñeca

Esta es la sección donde más importa la honestidad, porque es la más fácil de llenar
de números con apariencia científica.

- **El portero: `gps_grade`.** Se calcula el intervalo mediano entre muestras de cada
  actividad y se clasifica en alta (≤1.2 s), media (1.2-2.0 s), baja (>2.0 s) o
  sin_gps. Ese grado decide qué métricas se permiten.
- **Hallazgo que motiva la política:** el perfil "Fútbol" del FR255 graba con
  *Smart Recording*, con intervalo mediano de **2.74 s** (los perfiles de carrera sí
  están a 1.00 s). Un sprint de fútbol dura 2-4 s: con esa cadencia cae en 1-2
  muestras y **no se puede reconstruir**. Por eso HSR, conteo de sprints y
  aceleraciones quedan **deshabilitados** en todo el histórico de fútbol. No es una
  limitación de software: es que el dato no existe.
- **Qué sí se calcula:** distancia total (del firmware, no recalculada desde GPS),
  metros por minuto sobre duración total y sobre duración activa (tiempo en Z2-Z5 como
  proxy del tiempo realmente jugado), y velocidad pico como percentil 99 de la
  velocidad válida (no el máximo, que es ruido).
- **Limpieza de velocidad (extensión de D-008):** columnas `speed_valid` / `speed_flag`
  con banderas sin_dato, sin_gps, fuera_de_rango (>9.0 m/s) y salto_imposible
  (|Δv/Δt| > 6 m/s² respecto a la última muestra confiable). Motivo: la velocidad
  cruda en fútbol tiene percentil 99 de 12.12 m/s (43.6 km/h) y máximo de 31.67 m/s
  (114 km/h). Se **marca**, nunca se borra.
- **Referencias:** **Scott, Scott & Kelly (2016)**, *The Validity and Reliability of
  Global Positioning Systems in Team Sport: A Brief Review*, J Strength Cond Res
  30(5):1470-1490; **Rawstorn et al. (2014)**, *Rapid directional change degrades GPS
  distance measurement validity during intermittent intensity running*, PLoS ONE
  9(4):e93693; **Casamichana et al. (2013)**, J Strength Cond Res 27(2):369-374;
  **Vanrenterghem et al. (2017)**, Sports Medicine 47(11):2135-2142 (marco de dos vías:
  carga fisiológica y carga mecánica son caminos distintos).
- **Limitaciones a declarar siempre:** el GPS va en la **muñeca** y el balanceo del
  brazo corrompe la velocidad Doppler; el error típico de distancia es 5-7 %, así que
  **diferencias menores al 10 % entre sesiones no son interpretables**; los umbrales
  de alta velocidad (19.8 y 25.2 km/h) son de la literatura y **no están
  individualizados**; y los valores absolutos no son comparables con el fútbol
  profesional (el ~63 m/min observado sugiere que la duración incluye tiempo no jugado
  o que son canchas reducidas).

## 5. Fatiga intra-sesión

- **Fórmula:** el partido se parte en dos mitades **por tiempo** (90 de 96 partidos
  tienen un solo lap: no hay marcador de medio tiempo). Por mitad se calcula FC media
  ponderada por Δt, %FCmax, distancia, velocidad media y el **coste cardíaco**
  = %FC de reserva ÷ velocidad media. Salida: `decoupling_pct` = (coste₂/coste₁ − 1)·100
  y `dist_drop_pct`.
- **Referencias:** **Mohr, Krustrup & Bangsbo (2003)**, *Match performance of
  high-standard soccer players with special reference to development of fatigue*,
  Journal of Sports Sciences 21(7):519-528; **Bangsbo, Mohr & Krustrup (2006)**,
  Journal of Sports Sciences 24(7):665-674.
- **Por qué importa para el objetivo #1:** el tramo final del partido concentra las
  lesiones musculares por fatiga; los partidos con más decoupling son los candidatos.
- **Limitaciones:** son partidos recreativos sin control de sustituciones ni de tiempo
  real jugado, y el reloj puede seguir corriendo en el banco o el descanso. Con
  `gps_grade` baja se calcula solo la versión cardíaca (deriva de %FCmax) y se deja en
  nulo lo que dependa de velocidad. Se lee como **serie contra sí misma**, nunca como
  valor absoluto.

## 6. Registro subjetivo validado

### RPE diferencial (dRPE)
- **Fórmula:** dos escalas 0-10 separadas —esfuerzo respiratorio (RPE-B) y esfuerzo
  muscular de piernas (RPE-L)— multiplicadas por la duración dan sRPE-B y sRPE-L, más
  el diferencial RPE-L − RPE-B.
- **Referencias:** **Los Arcos et al. (2014)**, *Rating of Muscular and Respiratory
  Perceived Exertion in Professional Soccer Players*, J Strength Cond Res
  28(11):3280-3288 (en 21 futbolistas profesionales y 847 sesiones, tras partidos
  oficiales el RPE muscular **supera** al respiratorio: 7.4 ± 0.6 vs 6.4 ± 1.3);
  **McLaren et al. (2017)**, J Sci Med Sport 20(3):290-295; **Weston et al. (2015)**,
  J Sci Med Sport 18(6):704-708; **Foster et al. (2001)**, J Strength Cond Res
  15(1):109-115 (sRPE).
- **Por qué es la métrica manual de mayor valor aquí:** la carga que rompe
  isquiotibiales, aductores y gemelos en fútbol es **neuromuscular-mecánica**, y el
  TRIMP —puramente cardíaco, sin banda, sin pod, sin dinámica de carrera— es ciego a
  ella. Con este hardware, el RPE de piernas es el **único canal disponible** para
  estimarla.
- **Cuál manda:** sRPE-piernas para prevención de lesión muscular; TRIMP para condición
  aeróbica. Se decide de antemano para no caer en pesca de significancia con dos
  series paralelas.
- **Limitaciones:** es autorreporte, con sesgo de expectativa y de estado de ánimo, y
  se degrada si se registra tarde (la literatura recomienda ~30 min post-sesión). No
  hay evidencia de valor predictivo de lesión: es un descriptor de carga, no un semáforo.

### Hooper: cuatro ítems matinales
- **Fórmula:** calidad de sueño, fatiga, estrés y dolor muscular, cada uno 1-7
  (**7 = peor**). Se analizan por separado con z-scores contra línea base móvil de
  30 días (mínimo 14 observaciones), **nunca sumados** en un índice único.
- **Referencias:** **Hooper et al. (1995)**, Med Sci Sports Exerc 27(1):106-112;
  **Saw, Main & Gastin (2016)**, BJSM 50(5):281-291 (revisión sistemática de 56
  estudios: las medidas subjetivas reflejan la carga con mayor sensibilidad y
  consistencia que las objetivas, y subjetivo y objetivo típicamente **no
  correlacionan** — son complementarios, no redundantes); **McLean et al. (2010)**,
  IJSPP 5(3):367-383 (cinética de la fatiga percibida tras partido).
- **Por qué no se suma:** **Duignan et al. (2020)**, J Athl Train 55(9):944-953, y
  **Jeffries et al. (2020)**, IJSPP 15(9), muestran que el sumatorio no tiene
  propiedades de medición aceptables como constructo unitario.
- **Limitaciones:** la escala invertida se presta a errores de registro (se avisa en la
  interfaz); riesgo de habituación (responder siempre lo mismo); y con ventanas móviles
  cortas la DE es inestable, de modo que un deterioro lento puede volverse invisible
  por deriva de la línea base.

### OSTRC-H2 condicional
- **Fórmula:** 4 preguntas de recuerdo de 7 días. Q1 y Q4 puntúan 0/8/17/25; Q2 y Q3
  puntúan 0/6/13/19/25; severidad = suma (0-100). "Problema de salud" = severidad > 0;
  "problema sustancial" = respuesta moderada o peor (≥13) en Q2 o Q3.
- **Aplicación condicional:** solo se preguntan las zonas cuya molestia media semanal
  fue ≥3/10. Responder 4 × 7 = 28 preguntas semanales garantiza el abandono; así son
  típicamente 0-8 preguntas.
- **Referencias:** **Clarsen, Myklebust & Bahr (2013)**, BJSM 47(8):495-502;
  **Clarsen et al. (2014)**, BJSM 48(9):754-760 (versión de problemas de salud).
- **Limitación crítica para n=1:** **Franke et al. (2021)** estimaron que el cambio
  mínimo **detectable** individual del severity score es ~35 puntos, mayor que el
  cambio mínimo importante (~18.5). A nivel de una sola persona **solo los saltos
  grandes son fiables**; moverse 10-20 puntos es ruido.

### Adherencia como métrica de primera clase
- **Qué se mide:** % de días registrados en 30, racha actual y **mediana de segundos**
  que toma completar el formulario (se cronometra desde que se abre).
- **Referencias:** **Saw, Main & Gastin (2015)**, J Sports Sci Med 14(1):137-146 y
  14(4):732-739: el fracaso de los sistemas de autorreporte casi nunca es del
  instrumento sino del proceso, y el predictor número uno de abandono es **no recibir
  devolución de los propios datos**.
- **Regla de diseño:** objetivo duro de <30 segundos. Si la mediana sube, se recorta el
  formulario, no se le pide más disciplina al atleta.
- **Regla de datos:** "no registrado" **≠** 0. Los días sin registro quedan nulos y
  jamás se rellenan con ceros, que diluirían las señales reales.

### Lista de exclusión deliberada
Tan importante como qué preguntar es qué **no** preguntar, porque el presupuesto de
30 segundos es finito. **No se registran** por redundancia con el sensor: horas de
sueño, FC en reposo, nivel de energía (Body Battery), pasos y duración de sesión.
**Sí se registran** porque no tienen equivalente sensorial: calidad de sueño percibida,
estrés percibido, fatiga percibida, dolor por zona y dRPE.

## 7. Criterio de visualización y la regla del 3D

### La jerarquía perceptual
**Cleveland & McGill (1984)**, *Graphical perception: theory, experimentation, and
application to the development of graphical methods*, JASA 79(387):531-554, ordenaron
experimentalmente los canales por precisión de lectura: **posición sobre escala común
> posición sobre escalas no alineadas > longitud/ángulo > área > volumen > sombreado**.
Toda elección de gráfico en este proyecto se justifica contra ese orden.

### La regla del 3D, en tres líneas
1. Dato **abstracto** (carga, HRV, molestias) → **2D siempre**.
2. Dato **intrínsecamente espacial** (ruta GPS con altitud) → **3D justificado** para
   comprender la FORMA, nunca para leer valores, y siempre con su equivalente 2D al lado.
3. Todo gráfico 3D lleva **rótulo visible de exploración** y **jamás alimenta** el motor
   de recomendaciones ni la tarjeta "¿Puedo jugar hoy?".

### La evidencia, con sus matices
- **En contra del 3D para datos abstractos:** **Munzner (2014)**, *Visualization
  Analysis and Design*, cap. 6, regla "No Unjustified 3D" (oclusión, distorsión de
  perspectiva, texto inclinado ilegible); **Sedlmair, Munzner & Tory (2013)**,
  IEEE TVCG 19(12):2634-2643, compararon 816 scatterplots de 75 conjuntos de datos
  con scatter 2D, 3D interactivo y SPLOM, y el 3D interactivo "rara vez ayuda y a
  menudo perjudica"; **Tory et al. (2006)**, IEEE TVCG 12(1):2-13.
- **Contra el dogma anti-3D (matices que hay que citar de buena fe):**
  **Zacks et al. (1998)**, J Exp Psychol Appl 4(2):119-138, encontraron que las claves
  de profundidad sí bajan la precisión al leer barras, pero que el efecto del contexto
  gráfico es un orden de magnitud **mayor**, y concluyen que las advertencias sobre el
  daño del 3D "pueden estar exageradas"; **Siegrist (1996)**, Behaviour & IT
  15(2):96-100, no halló pérdida de precisión en barras 3D (sí en quesos 3D).
- **A favor del 3D en su nicho:** **St. John et al. (2001)**, *The use of 2D and 3D
  displays for shape-understanding versus relative-position tasks*, Human Factors
  43(1):79-98 — seis experimentos con terreno natural: el 3D **supera** al 2D para
  comprender formas tridimensionales, el 2D gana para posiciones y distancias exactas.

**Síntesis honesta: el 3D no es un crimen, es un impuesto.** Cuesta tiempo de lectura
y algo de precisión, y la pregunta correcta es qué compra a cambio. Para carga y
recuperación no compra nada que el 2D no dé mejor; para un cerro, sí.

### Decisiones concretas derivadas
| Tentación | Decisión | Reemplazo y referencia |
|---|---|---|
| Superficie 3D de carga × tiempo | **Descartada** | Heatmap de calendario — van Wijk & van Selow (1999), IEEE InfoVis '99, 4-9 |
| Scatter 3D carga-recuperación-molestia | **Implementado como juguete rotulado** | Scatter 2D con color y tamaño (4 variables, las 2 clave en posición) y coordenadas paralelas — Inselberg & Dimsdale (1990) |
| Ruta GPS con altitud | **3D implementado** con `aspectmode='data'` | Acompañado siempre del perfil 2D de lectura |
| Radar de las 7 zonas de molestia | **Descartado** | Dot plot ordenado (dumbbell) — Few (2005, 2012); el radar compara mal ángulos, su orden de ejes es arbitrario y el área crece con el **cuadrado** del valor |

La superficie de carga se descarta también por un argumento estadístico independiente:
una superficie de respuesta ajustada sobre ~96 sesiones y molestias aún escasas estaría
sobreajustada, y el ojo lee suavidad donde solo hay interpolación. El equivalente 2D
honesto (heatmap binado) muestra celdas vacías — que es exactamente lo que debe mostrar.

### Otros criterios de presentación
- **Bandas de referencia individuales** (media móvil ± SWC) como patrón visual central
  del monitoreo n=1 — Thornton et al. (2019), IJSPP 14(6):698-705.
- **Jerarquía del reporte:** lo accionable arriba, el detalle abajo —
  **Buchheit (2017)**, *Want to see my report, coach? Aspects of monitoring
  practices in team sports*, IJSPP 12(Suppl 2).
- **Semáforos con redundancia:** color + icono + texto + regla visible, nunca color
  solo — Robertson et al. (2017), IJSPP 12(Suppl 2):S2-73-S2-79.
- **Sparklines y bullet graphs** para la tarjeta pre-partido — Tufte (2006),
  *Beautiful Evidence*; Few (2006), *Information Dashboard Design*.
- **Small multiples** para comparar formas de varias series — Tufte (1983/2001).
- **Librería:** se mantiene **Plotly** en todo el dashboard. No se añaden Altair ni
  ECharts: romperían el sistema de paleta CVD centralizado en `viz.py` a cambio de una
  ganancia marginal. Nota de honestidad: no existen estudios revisados por pares que
  comparen estas librerías; la elección es por **consistencia arquitectónica**, no por
  superioridad demostrada.
