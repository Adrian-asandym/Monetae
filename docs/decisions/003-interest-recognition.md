# ADR-003 — Reconocimiento contable del interés de los préstamos

- **Estado:** PROPUESTO (pendiente de decisión de Adrian)
- **Fecha:** 2026-10-07 · **Autor:** Claude
- **Relacionado:** SPEC §7 (reglas 1 y 4), RF-15, RF-18; P2

## Contexto

SPEC §7 define el saldo de un préstamo como `principal + intereses + ajustes − pagos − condonaciones`. El interés se registra como un movimiento (`interest`) que **sube el saldo** aunque no mueva dinero. La pregunta es **cuándo cuenta ese interés como gasto o ingreso** en categorías, presupuestos y gráficos: el capital nunca cuenta (SPEC §7.4); el interés sí.

Con los números del Ejemplo A (me prestan S/ 200, interés 5 % = S/ 10, pago S/ 100 y luego S/ 110) el total reconocido es S/ 10 con cualquier criterio. Lo que cambia es **en qué fecha** aparece ese S/ 10 en los reportes y cómo se parte cada pago entre interés y capital.

## Opciones

### A (recomendada) — Base caja: el interés cuenta cuando se paga o se cobra
- Registrar un `interest` solo sube el saldo; **no** crea gasto/ingreso.
- Cada `payment` se reparte **primero a interés pendiente y luego a capital** (por orden de antigüedad). La parte de interés genera el gasto/ingreso en la categoría de sistema "Intereses" **en la fecha del pago**.
- El reparto se guarda en el movimiento (`interest_part`, `principal_part`), es editable al registrar el pago y queda auditable.
- Un pago que llega antes que cualquier interés es capital íntegro.
- **Pros:** coincide con cómo lo piensa Adrian ("cuánto me costó realmente este mes"); las estadísticas solo muestran dinero que se movió; es el valor por defecto de SPEC §7.4.
- **Contras:** un interés acordado en marzo y pagado en mayo aparece en mayo; hace falta guardar el reparto por pago.

### B — Base devengada: el interés cuenta al registrarlo
- El movimiento `interest` genera el gasto/ingreso en su fecha, haya o no dinero; los pagos son siempre capital+interés ya reconocido.
- **Pros:** el reporte mensual refleja lo acordado; modelo de pago más simple.
- **Contras:** aparecen gastos sin salida de dinero (el saldo de la cuenta no cuadra con las estadísticas de gasto); contradice la preferencia expresada en SPEC.

### C — Elegible por préstamo
- Un campo `interest_basis` (`cash`/`accrual`) por préstamo.
- **Pros:** flexible. **Contras:** dos caminos de cálculo en dominio, reportes y pruebas; riesgo de inconsistencias entre préstamos.

## Recomendación

**Opción A.** Guardar el reparto interés/capital en cada pago deja abierta la puerta a un reporte devengado en el futuro sin migrar datos.

## Consecuencias si se acepta A

- `loan_movements` incluye `interest_part` y `principal_part` en los pagos (suman el monto aplicado al préstamo).
- Los ejemplos A y E de SPEC §7 se escriben como tests literales, incluido el orden "primero interés".
- La categoría de sistema "Intereses" se alimenta solo desde pagos (y condonaciones de interés, si se definen).

## Decisión de Adrian

_Pendiente._
