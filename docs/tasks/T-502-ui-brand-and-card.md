# T-502 — UI: marca por modo (favicon/ícono), tarjeta de transacción configurable e íconos SVG de categoría

> **ESTADO: ACEPTADA e integrada en `master-dev` el 2026-10-09** (verificada por el coordinador: analyze limpio, 29 pruebas, build web). (Run `run_c2cebe1745b9`; decisiones D10-A y D11-A de Adrian; SPEC v0.4, contrato 0.4.0).
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `high`. Corre **en paralelo con T-505** (backend; archivos disjuntos). T-503 (cliente HTTP) va **después** de esta.

## Contexto

Adrian revisó el spike T-501 (`apps/web`) y le agrada. Pide: (1) favicon e ícono de la app **según el modo** con sus SVG; (2) conservar la **superficie azul del modo oscuro**; (3) **tarjeta de transacción configurable** (RF-47); (4) poder usar **SVG propios como íconos de categoría** (RF-46; la API llega en la Fase 6, aquí solo la parte visual con datos mock). Todo debe seguir **fiel al diseño de Cashew**.

## Leer primero

`AGENTS.md` §7, `docs/SPEC.md` v0.4 (**RF-39, RF-46, RF-47** y la regla de fidelidad visual en §5.10), `docs/api/openapi.json` 0.4.0 (`TransactionCardPreferences`, `UserPreferences`, `UserIcon`, `Category.icon`), `docs/cashew-analysis/05-ui-spike-results.md`, y el código de `apps/web` (sobre todo `lib/theme/monetae_theme.dart`, `lib/widgets/transaction_card.dart`, `lib/presentation/component_models.dart`, `lib/main.dart`, `web/index.html`, `web/manifest.json`, `tool/generate_dtos.py`).

Código de Cashew (solo lectura, para fidelidad): `/home/artur/propio2/Monetae/reference/Cashew/budget/lib/` (por ejemplo `widgets/transactionEntry/*` y `struct/defaultPreferences.dart`). **PROHIBIDO** leer o listar `/home/artur/propio2/Monetae/reference/backups/` (datos reales).

## Alcance

1. **Marca por modo.**
   - Fuentes: `img/icono-Monetae.svg` (claro) y `img/icono-Monetae-dark.svg` (oscuro) del repositorio; logos con nombre: `img/Monetae-Logo-Nombre.jpg` y `img/Monetae-Logo-Nombre-dark.jpg`. Cópialos a `apps/web` (por ejemplo `assets/brand/` y `web/icons/`); no modifiques los originales de `img/`.
   - **Favicon:** dos `<link rel="icon" type="image/svg+xml">` con `media="(prefers-color-scheme: light|dark)"` y un PNG de respaldo. El favicon sigue el modo **del sistema/navegador** (limitación del navegador: no puede seguir el tema interno de la app); documéntalo.
   - **Manifiesto:** PNG 192 y 512 (y `maskable` 512) generados **desde el SVG claro** mediante una herramienta reproducible en `apps/web/tool/` que use el propio Flutter (`flutter_svg` + `toImage`, por ejemplo como `flutter test` dedicado). **No instales** rasterizadores del sistema. `apple-touch-icon` en PNG.
   - **Dentro de la app:** el ícono/logo se dibuja con `flutter_svg` y cambia con el **tema de la app** (claro/oscuro). Retira el `monetae-logo.jpg` antiguo donde lo sustituyan los nuevos.
2. **Superficie azul en oscuro por defecto.** El aspecto oscuro actual (superficie azul tintada por el acento) queda como **predeterminado**; fíjalo con un golden.
3. **Tarjeta configurable (RF-47).**
   - Regenera los DTO con `tool/generate_dtos.py` desde el contrato **0.4.0** (incluye `TransactionCardPreferences`).
   - `TransactionCard` respeta `show_date`, `show_time`, `show_note`, `show_tags`, `show_account`, `show_actions`, con los **valores por defecto del contrato** (que reproducen Cashew: fecha, nota y etiquetas visibles; hora, cuenta y acciones ocultas). `show_date` en Cashew es la cabecera de grupo por día: respétalo en la lista de demostración.
   - Las acciones visibles (editar, duplicar, borrar) son **callbacks**; sin lógica de negocio.
   - En la pantalla de demostración, un panel de ajustes con interruptores (estado local; la persistencia vía API llega con T-503 y T-505). Textos por i18n `es`/`en`.
4. **Íconos de categoría (parte visual de RF-46).**
   - El modelo de vista acepta un **ícono del catálogo base** (clave → `Icons.*` de Material, Apache-2.0) **o un SVG propio** (bytes), según `Category.icon` (`custom:<uuid>`).
   - Dibuja los SVG propios con `flutter_svg` dentro del mismo círculo coloreado de Cashew (tinte opcional como `colorTintCategoryIcon`), en la tarjeta y en el gráfico circular.
   - Mock con **SVG sintéticos** creados por ti. Incluye una prueba con un SVG que contenga `<script>` y un `onload` para demostrar que no se ejecuta nada y que el render no falla.
   - **No copies** los PNG de categoría de Cashew (licencia no verificada).

## Archivos permitidos

`apps/web/**` y `docs/cashew-analysis/05-ui-spike-results.md` (añade una sección «T-502»). No tocar `img/`, `services/`, `infra/`, `docs/SPEC.md`, `docs/api/`, `AGENTS.md`, `reference/`. Dependencia nueva permitida: `flutter_svg` (justifícala); cualquier otra, con `ask`.

## Criterios de aceptación (con salidas en `worker_done`)

1. `dart analyze` sin avisos; `flutter test` verde con **goldens claro/oscuro** de: logo en ambos temas, tarjeta con valores por defecto, tarjeta con **todos** los detalles y con **ninguno**, categoría con SVG propio, y el SVG con `<script>`.
2. `flutter build web --release` compila. `web/index.html` tiene los dos favicons SVG con `media` y el PNG de respaldo; `manifest.json` apunta a PNG reales generados por la herramienta.
3. `grep -rE "drift|firebase|appStateSettings|package:budget/" apps/web/lib` vacío; ningún PNG de categoría de Cashew en el repo.
4. Diferencias frente a Cashew documentadas en el informe (sección T-502).

```bash
export PATH="$HOME/flutter/bin:$PATH"
cd apps/web
python3 -I tool/generate_dtos.py   # o el comando que documente la herramienta
flutter pub get && dart analyze && flutter test && flutter build web --release
grep -rE "drift|firebase|appStateSettings|package:budget/" lib || echo "limpio"
cd ../.. && git status --short && git diff --stat master-dev...HEAD   # solo archivos permitidos; sin build/
```

## Reglas

Commits pequeños en inglés (`feat(web):`, `test(web):`, `chore(web):`, `docs(ui):`). Actualiza tu rama con `master-dev` antes de reportar. Ante un caso no cubierto, `orca orchestration ask`. Reporta `worker_done` una sola vez.
