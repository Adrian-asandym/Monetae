# T-512 — UI: Inicio móvil fiel a Cashew según la skill `cashew-inicio-ui`

> **ESTADO: ACEPTADA e integrada en `master-dev` el 2026-10-10** (`2903271`; 179 pruebas UI; seguimiento T-512b por goldens sin texto, avisos de `analyze` y desviaciones; el coordinador versionó los goldens regenerados). **Detalles pendientes para la tarea de ajuste tras la revisión de Adrian:** botón final «Ver todas las transacciones» (hoy «Transacciones»); fecha del día sin año en el año en curso; total neto del día a la derecha del encabezado; redondeo de «X/día» a medio-arriba (hoy hacia arriba: 55,03 en vez de 55,02). (Run `run_c2cebe1745b9`; decisiones S1–S6 de Adrian; SPEC v0.6, contrato 0.6.0). Corre **en paralelo con T-603** (API `display_name`; archivos disjuntos).
> Agente: **Antigravity**, modelo **Pro** (lo fija Adrian en el panel), esfuerzo alto.

## La guía manda

**Sigue al pie de la letra `.claude/skills/cashew-inicio-ui/SKILL.md`** (ya está en tu worktree). Esta spec solo añade lo que la skill no puede saber: rutas, decisiones de Adrian, entorno y límites.

## Rutas (absolutas; NO están en tu worktree)

- **Capturas de referencia:** `/home/artur/propio2/Monetae-master-dev/reference/cashew-inicio-ui/1.png` … `6.png`.
  - Equivalen a `01-inicio-top.png` … `06-inicio-fin.png` de la skill: izquierda Monetae, derecha Cashew.
  - **Contienen datos reales de Adrian: solo lectura.** Nunca las copies ni las recortes dentro del repositorio, ni las cites con cifras.
- **Código de Cashew:** usa la copia local `/home/artur/propio2/Monetae/reference/Cashew/budget/lib/`, en lugar de clonarlo (equivale al paso 1 de la skill). Solo lectura.
- **PROHIBIDO** leer o listar `/home/artur/propio2/Monetae/reference/backups/`.

## Decisiones de Adrian (2026-10-10) que debes aplicar

- **S2:** la skill **sustituye** preferencias anteriores. Fondo neutro casi negro (se acabó la superficie azul) y montos con el formato de Cashew, **«100,46 S/.»** (coma decimal, símbolo al final, sin decimales cuando son cero).
  - Cambia el formato compartido (`currency_format.dart`) y actualiza todas las pruebas y goldens afectados. Verifica en el código de Cashew el separador de miles.
- **S4:** los textos «Puedes gastar X S/./día para N días más» (presupuesto) y «X S/./día para N días» (objetivo) **se calculan en la UI**. Es una excepción aprobada por Adrian, solo de presentación.
  - **Nunca con `double`.** Usa aritmética decimal exacta (el paquete `decimal` de pub está autorizado), con redondeo hacia arriba en el medio a 2 decimales.
  - Replica la fórmula de Cashew: `days_left` cuenta desde **hoy en America/Lima** hasta el final del periodo o `due_on`.
  - Si el presupuesto está excedido o la meta está cumplida, muestra lo que muestre Cashew en ese caso.
  - Pon la fórmula, con pruebas, en un único archivo de `presentation/`.
- **S5:** tipografía **DM Sans** (OFL; los TTF están en `reference/Cashew/budget/assets/fonts/`).
  - Inclúyela en `apps/web` con su licencia OFL y anótala en `NOTICE`.
  - **Avenir no** se puede usar: es una fuente comercial y el repositorio es público.
- **S3:** el **nombre del saludo** llega con T-603 (`CurrentUser.display_name`, contrato 0.6.0).
  - **No regeneres los DTO** desde el contrato 0.6.0 hasta que el coordinador te avise de que T-603 está integrada: el backend actual aún no envía el campo y el DTO estricto fallaría.
  - Haz el saludo por hora **al final**; mientras tanto, saludo sin nombre.

## Lo que no está en el contrato (no lo inventes)

- **Total neto del día** en la lista: tómalo de `GET /reports/cash-flow?period=daily` (ya lo calcula el servidor). No lo sumes en la UI.
- **Monto convertido** de una transacción en moneda extranjera (Cashew muestra el convertido y debajo el original): no está en el contrato. Muestra **solo el original** con su símbolo y anótalo como diferencia.
- **Ícono de recurrente** y **agrupación de transferencias:** usa los campos que ya tenga el contrato. Si falta alguno, anótalo como diferencia, sin inventar datos.
- **Botón de historial del presupuesto:** de momento lleva a la pestaña Presupuestos (el historial es D12, pendiente). **«Ver todas las transacciones»** lleva a la pestaña Transacciones.
- La **funcionalidad no se pierde:** la elección de cuenta por defecto sigue (ahora se marca con borde), igual que el cambio gasto/ingreso, el selector de mes, la recarga, el «+», etc.

## Flujo (el de la skill, con un punto de control)

1. Estudia las capturas, la skill y el código (Monetae y Cashew).
2. **Plan (paso 3 de la skill):** antes de tocar código, envía tu plan por componente con `orca orchestration ask`: qué widget cambia, de qué widget de Cashew sale y qué tokens fijas. **Espera la respuesta**: el coordinador lo revisará con Adrian.
3. Un componente a la vez, **un commit por componente**:
   - centraliza los tokens en el archivo de tema (sin valores sueltos);
   - actualiza los goldens claro y oscuro de ese componente.
4. Tras cada componente: compila, levanta tu pila, abre `http://localhost:8090` en tu navegador emulando **400×642** y compara con la captura. Ajusta hasta que coincida.
5. Al final, el informe de diferencias (paso 6 de la skill).

## Tu pila de prueba (propia; nunca la de Adrian)

```bash
# desde la raíz de tu worktree
export PATH="$HOME/.local/bin:$HOME/flutter/bin:$PATH"
export COMPOSE_PROJECT_NAME=monetae-t512 MONETAE_DB_PORT=5470 MONETAE_API_PORT=8010 MONETAE_WEB_PORT=8090
cp .env.example .env && sed -i 's/^MONETAE_COOKIE_SECURE=true$/MONETAE_COOKIE_SECURE=false/' .env
(cd apps/web && flutter build web --release)
docker compose -f infra/docker-compose.yml up -d --build db api web
docker compose -f infra/docker-compose.yml exec -T api alembic upgrade head
python3 -I -c "import secrets;print(secrets.token_urlsafe(18))" > /tmp/t512_pw
docker compose -f infra/docker-compose.yml exec -T api python -m monetae.cli create-user --email inicio@example.test --password-stdin < /tmp/t512_pw
uv run --frozen --project services/api python -I scripts/seed_review_data.py --base http://localhost:8090 --email inicio@example.test --password-file /tmp/t512_pw
# tras cada cambio: (cd apps/web && flutter build web --release) y recargar el navegador (nginx sirve build/web en vivo)
# al terminar: docker compose -f infra/docker-compose.yml down -v && rm -f .env /tmp/t512_pw
```

- Datos **solo sintéticos** (el script crea cuentas, presupuestos, metas y transacciones de octubre de 2026).
- **No** toques la pila de Adrian (`monetae-review`, 5433/8000/8080) ni la de T-603 (`monetae-t603`, 5465).

## Archivos permitidos

`apps/web/**` (incluidos fuentes y `pubspec.yaml` para DM Sans y `decimal`), `apps/web/NOTICE` y `docs/cashew-analysis/05-ui-spike-results.md` (sección nueva «T-512»).
- No tocar `services/`, `infra/`, `scripts/`, `docs/SPEC.md`, `docs/api/`, `docs/tasks/`, `.claude/`, `AGENTS.md`, `reference/`, `img/`.
- Otras dependencias: consúltalas antes con `ask`.

## Criterios de aceptación (con salidas en `worker_done`)

1. Todos los puntos de «Verificación final» de la skill, comprobados contra las capturas a 400×642.
2. `dart analyze` sin avisos y `flutter test` en verde, con goldens claro y oscuro actualizados por componente. Pruebas nuevas:
   - formato «100,46 S/.» (cero decimales y miles);
   - pluralización «1 transacción»;
   - cálculo «por día» (con y sin días restantes, presupuesto excedido, meta cumplida);
   - saludo por hora del día (mañana, tarde, noche).
3. `flutter build web --release` compila. `grep -rE "drift|firebase|appStateSettings|package:budget/" apps/web/lib` vacío. Procedencia y aviso GPL en cada archivo derivado; DM Sans con OFL en `NOTICE`.
4. **Informe (sección T-512):** componentes hechos (commit de cada uno), tokens fijados y la **lista de diferencias restantes con su motivo**.

```bash
export PATH="$HOME/flutter/bin:$PATH"
cd apps/web && flutter pub get && dart analyze && flutter test && flutter build web --release
grep -rE "drift|firebase|appStateSettings|package:budget/" lib || echo "limpio"
cd ../.. && git status --short && git diff --stat master-dev...HEAD   # solo archivos permitidos; sin build/
```

Disco justo (≈ 3 GB libres): una sola compilación a la vez; no dejes contenedores ni volúmenes al terminar. Commits pequeños en inglés (`feat(web):`, `style(web):`, `test(web):`, `docs(ui):`). Actualiza tu rama con `master-dev` antes de reportar. Ante cualquier duda, usa `orca orchestration ask`. Reporta `worker_done` una sola vez.
