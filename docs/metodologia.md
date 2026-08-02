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
