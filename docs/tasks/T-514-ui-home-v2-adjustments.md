# T-514 — UI: 4 ajustes de Inicio (v2) fieles a Cashew

> **ESTADO: LANZADA el 2026-10-10** (Run `run_c2cebe1745b9`; instrucciones de Adrian del 2026-10-10).
> Agente: **Codex**, modelo `gpt-6.1-sol`, esfuerzo `high`.

## Fuente

Son las instrucciones de Adrian, copiadas abajo sin cambios de fondo. Ten en cuenta estas equivalencias:
- La skill que mencionan, «cashew-ui», es **`.claude/skills/cashew-inicio-ui/SKILL.md`**. El coordinador la actualizará al integrar esta tarea: **no toques `.claude/`**.
- **Capturas** (solo lectura; **contienen datos reales**: nunca las copies al repositorio): `/home/artur/propio2/Monetae-master-dev/reference/cashew-inicio-ui/v2-01-top.png`, `v2-02-pie-ingresos.png`, `v2-03-linea.png`, `v2-04-editar.png`. En cada una, a la izquierda está Monetae actual y a la derecha Cashew (el objetivo).
- **Código de Cashew** (solo lectura): `/home/artur/propio2/Monetae/reference/Cashew/budget/lib/`. **PROHIBIDO** `reference/backups/`.
- **Verificación visual:** «localhost:8080» es la pila de Adrian y **no la toques**.
  - Compara a **400×642** los goldens de Inicio (superficie de prueba de 400×642) con las capturas.
  - Si quieres ver la app viva, usa una pila propia: `COMPOSE_PROJECT_NAME=monetae-t514`, `MONETAE_DB_PORT=5472`, `MONETAE_API_PORT=8012`, `MONETAE_WEB_PORT=8092`, con `scripts/seed_review_data.py`. Bájala con `down -v` al terminar.
- **No hace falta plan mode.** Un commit por ajuste, con sus goldens **versionados en el mismo commit**. Abre los PNG y comprueba que **se lee el texto**.

## Hechos ya comprobados por el coordinador (repórtalos, no los construyas)

- **No existen** formularios de creación de objetivos ni de presupuestos en `apps/web`: solo la API. Ajuste 1: la tarjeta «añadir» se dibuja, pero su acción queda como **TODO** (handler vacío documentado), y se reporta.
- **No existe** una pantalla de detalle de categorías. Ajuste 2: la lista de categorías y el selector de mes salen de Inicio y su código queda **sin conectar** (sin borrarlo), y se reporta.

## Los 4 ajustes (instrucciones de Adrian)

**1) Crear objetivo/presupuesto desde Inicio**
- Al final de cada carrusel (Objetivos y Presupuestos), una tarjeta «añadir» como la de Cashew (`v2-01-top.png`, a la derecha): icono de lista con «+» y la etiqueta «Objetivo» / «Presupuesto».
  - Mismo alto, ancho y radio que las tarjetas de su carrusel.
  - Fondo transparente y borde fino gris (~1.5 dp, gris ~35 %).
  - Icono centrado (~28 dp) y etiqueta gris debajo.
- Si un carrusel está vacío, esa tarjeta es lo único que se muestra en él.
- Confirma en el código de Cashew cómo se ve y dónde va esa tarjeta, y copia sus medidas.

**2) Gráfico circular: la 2.ª página es el de ingresos**
- La 2.ª página es el mismo gráfico circular que la 1.ª, pero con los ingresos (`v2-02-pie-ingresos.png`).
- Mismo layout en las dos páginas:
  - leyenda de categorías arriba a la izquierda (punto de color + nombre; puede ocupar 2 líneas);
  - triángulo arriba a la derecha: ▼ rojo en gastos, ▲ verde en ingresos;
  - dona con los iconos de categoría sobre el anillo;
  - puntos de paginación abajo, con el activo más claro.
- **Un solo widget parametrizado por tipo** (gasto/ingreso), sin código duplicado.
- **Estado vacío** (sin ingresos en el periodo): anillo vacío, sin romper el layout.

**3) Gráfico de línea: eje vertical con 4 valores**
- **Etiquetas:** 4, equiespaciadas, como en Cashew (`v2-03-linea.png`): el máximo y sus 3/4, 1/2 y 1/4. El 0 queda como línea base, sin etiqueta.
  - Cada una alineada con su línea punteada horizontal, dentro de la tarjeta, a la izquierda.
  - En gris ~50 %, con formato «842 S/.» (enteros, formato es).
- **Valores negativos:** si la serie baja de 0, el eje cubre del mínimo al máximo, las 4 etiquetas siguen equiespaciadas en ese rango y se dibuja una línea de referencia en 0. **Replica cómo calcula Cashew el rango con negativos.**
- **Pruebas:**
  - el cálculo del eje lleva pruebas unitarias con datos sintéticos, también negativos, y esas **sí** se versionan;
  - cualquier dato temporal que uses para mirar la app **no** se versiona.
- **Contenedor:** el gráfico va dentro de una **tarjeta** con el mismo fondo y radio que la de Cashew (hoy no se distingue).

**4) Menú ⋮ → botón «Editar»**
- Quita «Actualizar» y el logo grande del menú. En su lugar va el botón «Editar» de Cashew (`v2-04-editar.png`):
  - píldora gris oscuro, radio ~14 dp, ~114×45 dp;
  - icono de lápiz + texto «Editar», arriba a la derecha.
- Servirá para editar el orden de los componentes de Inicio. Por ahora solo el diseño: **handler vacío con un TODO**, sin reordenamiento.
- **Conserva la lógica de recarga** existente, sin UI visible. No la reubiques; en el informe, propón dónde ponerla (por ejemplo, *pull-to-refresh*).

## Reglas

- **Solo presentación:** no cambies modelos, DTO, API ni lógica de datos.
- Sin dependencias nuevas.
- Los tokens van en el tema (sin valores sueltos).
- i18n es/en.

## Archivos permitidos

`apps/web/**` y `docs/cashew-analysis/05-ui-spike-results.md` (sección nueva «T-514»).
No tocar `.claude/`, `services/`, `infra/`, `scripts/`, `docs/SPEC.md`, `docs/api/`, `docs/tasks/`, `reference/`.

## Criterios de aceptación (con salidas reales en `worker_done`)

1. `dart analyze` → «No issues found!» y `flutter test` todo en verde. Pruebas nuevas:
   - tarjeta «añadir» en carrusel con datos y en carrusel vacío;
   - un solo widget de gráfico circular para gasto e ingreso, incluido el estado vacío;
   - cálculo del eje Y: 4 valores, rango con negativos y línea en 0;
   - botón «Editar».
   Además, goldens claro y oscuro de Inicio y de cada componente tocado, **con texto visible**.
2. `flutter build web --release` compila. `grep -rE "drift|firebase|appStateSettings|package:budget/" apps/web/lib` vacío.
3. `git status --short` vacío al terminar: sin `test/failures/`, sin `build/` y sin scripts sueltos.
4. **Informe (sección T-514):**
   - medidas copiadas del código de Cashew (con su archivo);
   - lo que quedó distinto de Cashew y por qué, incluidos los dos «no existe» de arriba;
   - dónde propones poner la recarga.

```bash
export PATH="$HOME/flutter/bin:$PATH"
cd apps/web && flutter pub get && dart analyze && flutter test && flutter build web --release
grep -rE "drift|firebase|appStateSettings|package:budget/" lib || echo "limpio"
cd ../.. && git status --short && git diff --stat master-dev...HEAD
```

Disco justo (≈ 2,4 GB): borra `build/` al terminar. Commits pequeños en inglés (`feat(web):`, `test(web):`, `docs(ui):`). Actualiza tu rama con `master-dev` antes de reportar. Ante una duda real, usa `orca orchestration ask`. Reporta `worker_done` una sola vez.
