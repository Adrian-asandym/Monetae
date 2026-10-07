# ADR-004 — Fuente del tipo de cambio (PEN/USD)

- **Estado:** PROPUESTO (pendiente de decisión de Adrian)
- **Fecha:** 2026-10-07 · **Autor:** Claude
- **Relacionado:** SPEC §9, AGENTS.md §6.3, tabla `exchange_rates`

## Contexto

SPEC §9 fija que el tipo de cambio es **manual por defecto** (lo que realmente se pagó o recibió en la casa de cambio) y se guarda en cada transacción (`fx_rate_to_base`, `fx_rate_source`). No se recalcula el pasado. Falta decidir de dónde sale la **sugerencia automática** que se muestra al registrar. Cashew no ayuda: no tiene tabla de tasas, sino un JSON global de configuración (`docs/cashew-analysis/01-data-model.md`).

## Opciones

### A (recomendada) — Manual + sugerencia automática detrás de una interfaz intercambiable
- La tasa manual siempre manda. El servidor define un puerto `RateProvider` y guarda la sugerencia diaria en `exchange_rates` (`from`, `to`, `rate`, `as_of`, `source`), con caché de un día.
- El proveedor concreto se elige **al implementarlo**, tras comprobar disponibilidad, límites y condiciones en ese momento. Candidatos a verificar (no verificados aún): la API de estadísticas del Banco Central de Reserva del Perú (oficial) y una API pública de tasas con soporte de PEN.
- Si el proveedor falla, la app sigue funcionando en modo manual.
- **Pros:** sin dependencia dura de un tercero; la consulta solo envía el par de monedas, ningún dato financiero (SPEC §12); se puede cambiar de proveedor sin migrar.
- **Contras:** hay que mantener una pequeña integración externa y su manejo de fallos.

### B — Solo manual en V1
- Sin llamadas externas; el campo viene vacío y se rellena a mano o con la última tasa usada.
- **Pros:** cero dependencias y cero riesgo de privacidad. **Contras:** más fricción diaria; la interfaz `RateProvider` se pospone.

### C — Automática obligatoria
- La tasa se toma siempre de una fuente.
- **Contras:** contradice la práctica real de Adrian (la tasa pagada en una casa de cambio rara vez es la oficial) y SPEC §9.3. Se descarta.

## Recomendación

**Opción A**, entregando en V1 la interfaz y la tasa manual, y activando un proveedor concreto cuando se verifique. Si prefieres no tener llamadas externas por ahora, B es compatible: A solo añade el proveedor.

## Consecuencias

- `exchange_rates` guarda `source` (`manual`/`auto:<proveedor>`) y fecha; las transacciones copian la tasa vigente.
- Los reportes multimoneda usan las tasas guardadas en cada transacción (SPEC §9.5).
- Tarea de verificación del proveedor antes de implementarlo (condiciones de uso, límites, formato).

## Decisión de Adrian

_Pendiente._
