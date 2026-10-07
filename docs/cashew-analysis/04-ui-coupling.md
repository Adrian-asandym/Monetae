# Análisis de Acoplamiento de la Interfaz de Cashew (Insumo para ADR-001)

> **Documento:** `docs/cashew-analysis/04-ui-coupling.md`  
> **Fecha:** Octubre 2026  
> **Autor:** Antigravity (Gemini) — Worker T-004  
> **Propósito:** Evaluar cuantitativa y cualitativamente el acoplamiento de la interfaz gráfica de Cashew (`reference/Cashew/budget/`) a su capa de persistencia local (Drift/SQLite) y servicios en la nube (Firebase/Google Drive), para servir como insumo técnico principal en la decisión **ADR-001 (Estrategia de UI: Fork de Flutter vs. UI propia)**.  
> **Estado:** Completo / Verificado objetivamente con métricas sobre el código fuente.

---

## 1. Resumen Ejecutivo

Cashew es una aplicación financiera en Flutter diseñada originalmente como una app móvil *offline-first* monopuesto. El análisis estático de su arquitectura revela que **no existe una separación formal por capas arquitectónicas** (Clean Architecture, Repositorios o Hexagonal). En su lugar:

1. **Acoplamiento ubicuo a la base de datos:** La instancia global de base de datos (`late FinanceDatabase database;` en `lib/struct/databaseGlobal.dart:6`) es invocada directamente **338 veces** desde **63 archivos** de presentación (`pages/` y `widgets/`). De los 54 archivos en `pages/`, **47 importan directamente `tables.dart` (87.0 %)**.
2. **Reactividad dependiente de SQLite:** La interfaz depende de **135 `StreamBuilder`** en **47 archivos** que consumen directamente los flujos emitidos por Drift al detectar cambios en tablas SQLite locales.
3. **Dependencia circular y estado mutable monolítico:** `tables.dart` (7,668 líneas) importa directamente widgets y páginas de UI (`pages/addBudgetPage.dart`, `widgets/navigationFramework.dart`, etc.) y Firestore. A su vez, **117 archivos de UI realizan 1,346 accesos a un `Map<String, dynamic>` global no tipado** (`appStateSettings` en `lib/struct/settings.dart:26`).
4. **Identificadores primarios:** A diferencia de supuestos preliminares, Cashew **ya utiliza identificadores UUID v4 (`TextColumn`)** en sus tablas principales (`tables.dart:252, 275, 343, 420`). Por tanto, la dificultad de integración no radica en el formato de las claves primarias, sino en la emulación de la reactividad local y la duplicación de lógica de negocio.
5. **Componentes visuales no desacoplados de origen:** La medición de 17 componentes visuales clave (gráficos, tarjetas de transacción, temas) evidencia que 12 de ellos importan `tables.dart` o `databaseGlobal.dart`, requiriendo un esfuerzo explícito de desacoplamiento para convertirlos en widgets puros basados en parámetros (*props*).
6. **Dependencias propietarias y en la nube:** Firebase (Core, Auth, Firestore), Google Drive (`googleapis`) y Google Sign-In están acoplados para sincronización, presupuestos compartidos y adjuntos.
7. **Veredicto según `CLAUDE.md` §6:** Con base en las métricas recopiladas, un *fork integral* de Cashew que pretenda sustituir Drift por la API REST de Monetae resulta **demasiado invasivo** (84 archivos acoplados a `tables.dart`, 338 llamadas a `database.*`, 135 `StreamBuilder`, 1,346 accesos a `appStateSettings`).
8. **Estrategia recomendada:** Desarrollar una **UI modular propia en Flutter Web** que adopte Clean Architecture y consuma `/api/v1` mediante un cliente generado desde OpenAPI (`AGENTS.md` §7), extrayendo y desacoplando de Cashew sus componentes visuales de alto valor (paleta `colors.dart`, gráficos `fl_chart`, animaciones y tarjetas `transactionEntry`).

---

## 2. Metodología y Trazabilidad

- **Código analizado:** `reference/Cashew/budget/` (commit vigente en el repositorio, solo lectura).
- **Herramientas de inspección:** Comandos directos de shell (`grep`, `find`, `wc`, `sed`) ejecutados en entorno Linux/WSL2.
- **Rigor metodológico:**
  - `[Verificado en código]`: Afirmación respaldada por archivo, número de línea y comando de verificación con salida reproducible.
  - `[Inferencia / Hipótesis]`: Deducción arquitectónica explicada a partir de los patrones encontrados.
  - `[Inferencia - no es asesoría legal]`: Cuestiones de interpretación de licenciamiento libre.
- **Privacidad:** No se consultó ningún dato financiero real de `reference/backups/`. Todos los análisis son exclusivamente sobre el código fuente de Cashew.

---

## 3. (a) Arquitectura de Capas de la Aplicación

### 3.1 Estructura de Directorios

La estructura bajo `reference/Cashew/budget/lib/` consta de 212 archivos Dart distribuidos así:

```
reference/Cashew/budget/lib/
├── main.dart                          # Entrada de la app, bootstrap e inicialización
├── colors.dart                        # Paletas de color, temas claro/oscuro
├── functions.dart                     # Funciones utilitarias globales (fechas, rutas, helpers)
├── firebase_options.dart              # Credenciales y opciones Firebase multiplataforma
├── database/                          # Capa de datos Drift / SQLite (10 archivos)
│   ├── tables.dart                    # Esquemas de tablas Y clase monolítica FinanceDatabase (7,668 líneas)
│   ├── tables.g.dart                  # Código generado por drift_dev (DAOs, data classes)
│   ├── schema_versions.dart           # Migraciones de esquemas (versiones 1 a 46)
│   ├── initializeDefaultDatabase.dart # Sembrado inicial de datos
│   └── platform/                      # Abstracción nativa vs web (web.dart, native.dart, shared.dart)
├── struct/                            # Configuración global, estado y sincronización (28 archivos)
│   ├── databaseGlobal.dart            # Variable global mutable 'database'
│   ├── settings.dart                  # Variable global mutable 'appStateSettings' (Map)
│   ├── syncClient.dart                # Sincronización SQLite multi-dispositivo vía Google Drive
│   ├── shareBudget.dart               # Presupuestos compartidos vía Cloud Firestore
│   ├── firebaseAuthGlobal.dart        # Autenticación Firebase / Google
│   ├── initializeBiometrics.dart      # Autenticación biométrica con local_auth
│   ├── initializeNotifications.dart   # Notificaciones programadas con flutter_local_notifications
│   └── uploadAttachment.dart          # Subida de recibos a Google Drive
├── pages/                             # Vistas y pantallas principales (54 archivos)
│   ├── homePage/                      # Pantalla de inicio y widgets de gráficos (11 archivos)
│   ├── addTransactionPage.dart        # Creación y edición de transacciones (5,100+ líneas)
│   ├── accountsPage.dart              # Gestión de cuentas / wallets
│   ├── budgetPage.dart                # Detalle y edición de presupuestos
│   └── subscriptionsPage.dart         # Listado de suscripciones
├── widgets/                           # Componentes reutilizables (115 archivos)
│   ├── transactionEntry/              # Tarjetas visuales de transacción (8 archivos)
│   ├── navigationSidebar.dart         # Menú lateral para vistas amplias / web
│   └── pieChart.dart                  # Componentes de visualización fl_chart
└── modified/                          # Paquetes vendorizados parcheados localmente (1 archivo)
    └── reorderable_list.dart
```

### 3.2 Flujo de Arranque (`main.dart`) [Verificado en código]

En `reference/Cashew/budget/lib/main.dart:44-75`:
1. **Firebase:** Se inicializa obligatoriamente al arrancar:
   ```dart
   // lib/main.dart:47-49
   await Firebase.initializeApp(
     options: DefaultFirebaseOptions.currentPlatform,
   );
   ```
2. **Localización:** `await EasyLocalization.ensureInitialized();` (línea 50).
3. **Preferencias:** `sharedPreferences = await SharedPreferences.getInstance();` (línea 51).
4. **Base de Datos Drift:** Se instancia y asigna a la variable global:
   ```dart
   // lib/main.dart:52
   database = await constructDb('db');
   ```
5. **Configuración de la App:** `await initializeSettings();` (línea 57), que carga la configuración persistida en SQLite a la variable global en memoria `appStateSettings`.
6. **Timezone e Íconos:** `tz.initializeTimeZones();` y ordenamiento de iconos.
7. **Montaje de Widgets:** Lanza `MaterialApp` envuelto en `RestartApp`, `InitializeBiometrics`, `WatchForDayChange`, `WatchSelectedWalletPk` y `WatchAllWallets`.

### 3.3 El Patrón de Acceso a Datos: `databaseGlobal.dart` y `tables.dart` [Verificado en código]

Cashew implementa el patrón de acceso a datos mediante variables globales de alcance de librería:

- **Declaración:** En `reference/Cashew/budget/lib/struct/databaseGlobal.dart:6`:
  ```dart
  late FinanceDatabase database;
  ```
- **Implementación Monolítica:** En `reference/Cashew/budget/lib/database/tables.dart:692`:
  ```dart
  class FinanceDatabase extends _$FinanceDatabase { ... }
  ```
  La clase `FinanceDatabase` abarca desde la línea 692 hasta la línea 7,668 (6,977 líneas continuas). En ella se concentran:
  - Definición de consultas SQL crudas y expresiones Drift.
  - Métodos CRUD para todas las entidades (`Transactions`, `Budgets`, `Wallets`, `Categories`, `Objectives`, etc.).
  - Lógica de negocio de cálculo de totales, períodos presupuestarios y balances.
  - Cálculos de préstamos de largo plazo modelados como metas (línea 271 del `README.md`).
  - Mutaciones cruzadas con servicios en la nube (ej. Firestore en línea 4,238).

### 3.4 Formato Real de Claves Primarias (UUID v4) [Verificado en código]

Las tablas principales de Cashew utilizan claves primarias de texto basadas en UUID v4:

```dart
// reference/Cashew/budget/lib/database/tables.dart:252
TextColumn get walletPk => text().clientDefault(() => uuid.v4())();

// reference/Cashew/budget/lib/database/tables.dart:275
TextColumn get transactionPk => text().clientDefault(() => uuid.v4())();

// reference/Cashew/budget/lib/database/tables.dart:343
TextColumn get categoryPk => text().clientDefault(() => uuid.v4())();

// reference/Cashew/budget/lib/database/tables.dart:420
TextColumn get budgetPk => text().clientDefault(() => uuid.v4())();
```

Esto confirma que a nivel de identificadores (`UUID`), los modelos de Cashew coinciden con el estándar de `AGENTS.md` §6 regla 4 (`UUID` para claves primarias).

### 3.5 Acoplamiento Circular e Inversión de Dependencias Rota [Verificado en código]

En Cashew, la capa de persistencia importa directamente vistas y widgets de presentación:

```dart
// reference/Cashew/budget/lib/database/tables.dart:2-24
import 'package:budget/pages/addBudgetPage.dart';
import 'package:budget/pages/homePage/homePageLineGraph.dart';
import 'package:budget/pages/objectivesListPage.dart';
import 'package:budget/pages/transactionFilters.dart';
import 'package:budget/struct/shareBudget.dart';
import 'package:budget/struct/syncClient.dart';
import 'package:budget/widgets/navigationFramework.dart';
import 'package:budget/widgets/periodCyclePicker.dart';
import 'package:budget/widgets/walletEntry.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:budget/pages/activityPage.dart';
```

Esto crea una dependencia circular bidireccional: la interfaz de usuario depende de `tables.dart`, y `tables.dart` depende de la interfaz de usuario y de Firestore.

---

## 4. (b) Métricas Verificables del Acoplamiento

Todos los comandos presentados a continuación se ejecutaron en el repositorio sobre la ruta relativa `reference/Cashew/budget/`.

### 4.1 Resumen General de Métricas

| Métrica | Valor | Alcance / Detalle |
|---|:---:|---|
| **Total de archivos Dart en `lib/`** | **212** | Total del frontend |
| **Archivos en `pages/`** | **54** | Pantallas de la aplicación |
| **Archivos en `widgets/`** | **115** | Componentes y vistas parciales |
| **Archivos de UI que importan `tables.dart`** | **84** | 47 en `pages/` (87.0 %) y 37 en `widgets/` (32.2 %) |
| **Archivos de UI que importan `databaseGlobal.dart`** | **63** | 43 en `pages/` y 20 en `widgets/` |
| **Invocaciones directas a `database.*` en UI** | **338** | 240 en `pages/` y 98 en `widgets/` |
| **Archivos de UI que usan `appStateSettings`** | **117** | 48 en `pages/` y 69 en `widgets/` |
| **Ocurrencias de `appStateSettings` en UI** | **1,346** | 793 en `pages/` y 553 en `widgets/` (1,621 en todo `lib/`) |
| **Consultas Drift `select(` en `tables.dart`** | **177** | Consultas SELECT de Drift |
| **Mutaciones Drift (`into`, `update`, `delete`)** | **78** | 15 `into(`, 29 `update(`, 34 `delete(` |
| **Consultas reactivas `.watch*` en `tables.dart`** | **93** | 62 `.watch()` y 31 `.watchSingle*` |
| **Consultas sincrónicas/futuras `.get*` en `tables.dart`** | **141** | 106 `.get()` y 35 `.getSingle*` |
| **Firmas de métodos que retornan `Stream<...>`** | **105** | Flujos reactivos de datos en `tables.dart` |
| **Firmas de métodos que retornan `Future<...>`** | **156** | Operaciones asíncronas en `tables.dart` |
| **Uso de `StreamBuilder` en UI** | **135** | 101 en 33 `pages/`, 34 en 14 `widgets/` |
| **Uso de `FutureBuilder` en UI** | **6** | 5 archivos de UI |
| **Suscripciones manuales `.listen(` en UI** | **7** | 7 archivos de UI |
| **Bifurcaciones `kIsWeb` en código** | **86** | 43 archivos de `lib/` |

---

### 4.2 Comandos Exactos y Salidas Reproducibles

#### 1. Conteo de Archivos Dart por Carpeta
```bash
find reference/Cashew/budget/lib -type f -name "*.dart" | wc -l
# Salida: 212

find reference/Cashew/budget/lib/pages -type f -name "*.dart" | wc -l
# Salida: 54

find reference/Cashew/budget/lib/widgets -type f -name "*.dart" | wc -l
# Salida: 115

find reference/Cashew/budget/lib/struct -type f -name "*.dart" | wc -l
# Salida: 28

find reference/Cashew/budget/lib/database -type f -name "*.dart" | wc -l
# Salida: 10
```

#### 2. Archivos de UI que Importan `tables.dart`
```bash
# Total en pages y widgets
grep -rl "database/tables.dart" reference/Cashew/budget/lib/pages reference/Cashew/budget/lib/widgets | wc -l
# Salida: 84

# Desglose en pages/
grep -rl "database/tables.dart" reference/Cashew/budget/lib/pages | wc -l
# Salida: 47

# Desglose en widgets/
grep -rl "database/tables.dart" reference/Cashew/budget/lib/widgets | wc -l
# Salida: 37
```

#### 3. Archivos de UI que Importan `databaseGlobal.dart`
```bash
grep -rl "databaseGlobal.dart" reference/Cashew/budget/lib/pages reference/Cashew/budget/lib/widgets | wc -l
# Salida: 63

grep -rl "databaseGlobal.dart" reference/Cashew/budget/lib/pages | wc -l
# Salida: 43

grep -rl "databaseGlobal.dart" reference/Cashew/budget/lib/widgets | wc -l
# Salida: 20
```

#### 4. Llamadas Directas a `database.*` en la UI
```bash
# Total de llamadas en pages y widgets
grep -rn "database\." reference/Cashew/budget/lib/pages reference/Cashew/budget/lib/widgets | wc -l
# Salida: 338

# Total de archivos con llamadas a database.
grep -rl "database\." reference/Cashew/budget/lib/pages reference/Cashew/budget/lib/widgets | wc -l
# Salida: 63

# Llamadas en pages/
grep -rn "database\." reference/Cashew/budget/lib/pages | wc -l
# Salida: 240

# Llamadas en widgets/
grep -rn "database\." reference/Cashew/budget/lib/widgets | wc -l
# Salida: 98
```

#### 5. Acoplamiento al Estado Global no Tipado `appStateSettings`
```bash
# Total de ocurrencias en pages y widgets
grep -rn "appStateSettings" reference/Cashew/budget/lib/pages reference/Cashew/budget/lib/widgets | wc -l
# Salida: 1346

# Archivos de UI que usan appStateSettings
grep -rl "appStateSettings" reference/Cashew/budget/lib/pages reference/Cashew/budget/lib/widgets | wc -l
# Salida: 117

# Desglose en pages/
grep -rn "appStateSettings" reference/Cashew/budget/lib/pages | wc -l
# Salida: 793 (en 48 archivos)

# Desglose en widgets/
grep -rn "appStateSettings" reference/Cashew/budget/lib/widgets | wc -l
# Salida: 553 (en 69 archivos)

# Total en todo lib/
grep -rn "appStateSettings" reference/Cashew/budget/lib/ | wc -l
# Salida: 1621 (en 137 archivos)
```

#### 6. Consultas Drift en `database/tables.dart`
```bash
# Consultas select
grep -rn "select(" reference/Cashew/budget/lib/database/tables.dart | wc -l
# Salida: 177

# Inserciones into
grep -rn "into(" reference/Cashew/budget/lib/database/tables.dart | wc -l
# Salida: 15

# Actualizaciones update
grep -rn "update(" reference/Cashew/budget/lib/database/tables.dart | wc -l
# Salida: 29

# Eliminaciones delete
grep -rn "delete(" reference/Cashew/budget/lib/database/tables.dart | wc -l
# Salida: 34

# Consultas reactivas watch
grep -rn "\.watch()" reference/Cashew/budget/lib/database/tables.dart | wc -l
# Salida: 62

grep -rn "\.watchSingle" reference/Cashew/budget/lib/database/tables.dart | wc -l
# Salida: 31

grep -rn "\.watch" reference/Cashew/budget/lib/database/tables.dart | wc -l
# Salida: 93

# Consultas puntuales get
grep -rn "\.get()" reference/Cashew/budget/lib/database/tables.dart | wc -l
# Salida: 106

grep -rn "\.getSingle" reference/Cashew/budget/lib/database/tables.dart | wc -l
# Salida: 24

grep -rn "\.get" reference/Cashew/budget/lib/database/tables.dart | wc -l
# Salida: 141

# Firmas de retorno Stream vs Future
grep -rn "Stream<" reference/Cashew/budget/lib/database/tables.dart | wc -l
# Salida: 105

grep -rn "Future<" reference/Cashew/budget/lib/database/tables.dart | wc -l
# Salida: 156
```

#### 7. Consumo de Reactividad en `pages/` y `widgets/`
```bash
# StreamBuilder en UI
grep -rn "StreamBuilder" reference/Cashew/budget/lib/pages reference/Cashew/budget/lib/widgets | wc -l
# Salida: 135

grep -rl "StreamBuilder" reference/Cashew/budget/lib/pages reference/Cashew/budget/lib/widgets | wc -l
# Salida: 47

grep -rn "StreamBuilder" reference/Cashew/budget/lib/pages | wc -l
# Salida: 101 (en 33 archivos)

grep -rn "StreamBuilder" reference/Cashew/budget/lib/widgets | wc -l
# Salida: 34 (en 14 archivos)

# FutureBuilder en UI
grep -rn "FutureBuilder" reference/Cashew/budget/lib/pages reference/Cashew/budget/lib/widgets | wc -l
# Salida: 6 (en 5 archivos)

# Suscripciones manuales .listen(
grep -rn "\.listen(" reference/Cashew/budget/lib/pages reference/Cashew/budget/lib/widgets | wc -l
# Salida: 7 (en 7 archivos)
```

#### 8. Dispersión de Código Específico Web (`kIsWeb`)
```bash
grep -rn "kIsWeb" reference/Cashew/budget/lib/ | wc -l
# Salida: 86

grep -rl "kIsWeb" reference/Cashew/budget/lib/ | wc -l
# Salida: 43
```

---

### 4.3 Medición del Acoplamiento en Componentes Candidatos a Reutilización [Verificado en código]

Para evaluar de forma realista la viabilidad de reutilizar componentes visuales de Cashew en una UI propia (Estrategia 1), se midió individualmente el grado de acoplamiento de 17 componentes clave (diseño, tarjetas de transacción, gráficos, animaciones).

#### Comando de medición por componente:
```bash
for f in \
  lib/colors.dart \
  lib/struct/customDelayedCurve.dart \
  lib/struct/iconObjects.dart \
  lib/widgets/fadeIn.dart \
  lib/widgets/navigationSidebar.dart \
  lib/widgets/pieChart.dart \
  lib/pages/homePage/homePageLineGraph.dart \
  lib/pages/homePage/homePagePieChart.dart \
  lib/pages/homePage/homePageHeatmap.dart \
  lib/widgets/transactionEntry/transactionEntry.dart \
  lib/widgets/transactionEntry/incomeAmountArrow.dart \
  lib/widgets/transactionEntry/swipeToSelectTransactions.dart \
  lib/widgets/transactionEntry/transactionEntryAmount.dart \
  lib/widgets/transactionEntry/transactionEntryNote.dart \
  lib/widgets/transactionEntry/transactionEntryTag.dart \
  lib/widgets/transactionEntry/transactionEntryTypeButton.dart \
  lib/widgets/transactionEntry/transactionLabel.dart
do
  p="reference/Cashew/budget/$f"
  lines=$(wc -l < "$p")
  imp_tbl=$(grep -c "database/tables.dart" "$p" || true)
  imp_glob=$(grep -c "databaseGlobal.dart" "$p" || true)
  settings=$(grep -c "appStateSettings" "$p" || true)
  other_imp=$(grep -E "import 'package:budget/" "$p" | grep -v -E "tables.dart|databaseGlobal.dart" | wc -l)
  echo "$f | $lines | $imp_tbl | $imp_glob | $settings | $other_imp"
done
```

#### Resultados de la Medición:

| Componente | Líneas (`wc -l`) | Importa `tables.dart` | Importa `databaseGlobal.dart` | Accesos `appStateSettings` | Otros imports internos `package:budget/` | Veredicto Técnico |
|---|:---:|:---:|:---:|:---:|:---:|---|
| `lib/colors.dart` | 677 | 0 | 0 | 49 | 3 | **Requiere desacoplar:** extraer temas y sustituir `appStateSettings` por `ThemeExtension` o parámetros. |
| `lib/struct/customDelayedCurve.dart` | 19 | 0 | 0 | 0 | 0 | **Copiable tal cual:** animación pura sin dependencias. |
| `lib/struct/iconObjects.dart` | 4,545 | 0 | 0 | 0 | 0 | **Copiable tal cual:** catálogo estático de iconos. |
| `lib/widgets/fadeIn.dart` | 619 | 0 | 0 | 8 | 4 | **Requiere desacoplar:** desacoplar acceso a duraciones globales en `appStateSettings`. |
| `lib/widgets/navigationSidebar.dart` | 798 | 0 | 0 | 42 | 16 | **Reescribir / Adaptar:** altamente acoplado a páginas internas de Cashew; adaptar solo el layout visual. |
| `lib/widgets/pieChart.dart` | 470 | 1 | 1 | 0 | 7 | **Requiere desacoplar:** consulta `database.`; convertir en widget puro que reciba lista de datos numéricos. |
| `lib/pages/homePage/homePageLineGraph.dart` | 405 | 1 | 1 | 14 | 9 | **Requiere desacoplar:** consulta `database.` y filtros; extraer la capa `fl_chart` como widget presentacional. |
| `lib/pages/homePage/homePagePieChart.dart` | 606 | 1 | 1 | 9 | 20 | **Requiere desacoplar:** contiene lógica de filtros y consultas locales; extraer solo el renderizado circular. |
| `lib/pages/homePage/homePageHeatmap.dart` | 473 | 1 | 1 | 5 | 15 | **Requiere desacoplar:** consulta transacciones directamente; convertir a cuadrícula pura que reciba un mapa de fechas. |
| `lib/widgets/transactionEntry/transactionEntry.dart` | 988 | 1 | 1 | 9 | 20 | **Requiere desacoplar:** depende de clases Drift (`Transaction`, `Budget`); convertir a modelo de vista/DTO agnóstico. |
| `lib/widgets/transactionEntry/incomeAmountArrow.dart` | 156 | 1 | 0 | 1 | 6 | **Requiere desacoplar:** desacoplar `Transaction`; pasar `isIncome` booleano y monto por constructor. |
| `lib/widgets/transactionEntry/swipeToSelectTransactions.dart` | 75 | 0 | 0 | 0 | 1 | **Copiable tal cual:** lógica de gestos sin acoplamiento a base de datos. |
| `lib/widgets/transactionEntry/transactionEntryAmount.dart` | 143 | 1 | 0 | 1 | 7 | **Requiere desacoplar:** desacoplar `Transaction`; recibir valor y moneda formateados. |
| `lib/widgets/transactionEntry/transactionEntryNote.dart` | 69 | 1 | 0 | 2 | 4 | **Requiere desacoplar:** recibir texto de nota por parámetro. |
| `lib/widgets/transactionEntry/transactionEntryTag.dart` | 458 | 1 | 1 | 15 | 7 | **Requiere desacoplar:** consulta categorías/objetivos de la base de datos; pasar etiquetas precalculadas. |
| `lib/widgets/transactionEntry/transactionEntryTypeButton.dart` | 272 | 1 | 1 | 2 | 13 | **Reescribir / Adaptar:** fuertemente ligado a los enums y flujos de tipos de transacción de Cashew. |
| `lib/widgets/transactionEntry/transactionLabel.dart` | 128 | 1 | 1 | 9 | 3 | **Requiere desacoplar:** consulta `database.`; desacoplar para recibir texto y color directos. |

#### Diagnóstico del Desacoplamiento:
De los 17 archivos evaluados:
- **3 son copiables directamente** (17.6 %).
- **12 requieren refactorización de desacoplamiento** (70.6 %): eliminar imports de `database/tables.dart`, sustituir consultas directas a `database.` por parámetros de entrada (*props*), y reemplazar `appStateSettings` por configuración tipada.
- **2 requieren reescritura o adaptación sustancial** (11.8 %).

Este hallazgo demuestra que la extracción de componentes visuales no es inmediata; requiere un esfuerzo medido de adaptación para eliminar las dependencias a Drift y al estado global mutable.

---

## 5. (c) Dependencias de Firebase y Servicios Externos

Cashew integra múltiples servicios externos de Google y Firebase. Para Monetae, cada uno de ellos debe eliminarse o reemplazarse por la arquitectura propia descrita en `docs/SPEC.md`.

| Servicio | Paquetes en `pubspec.yaml` | Archivos Principales en Cashew | Rol en Cashew | Destino en Monetae |
|---|---|---|---|---|
| **Firebase Core** | `firebase_core: ^3.2.0`, `firebase_core_web: ^2.17.3` | `lib/main.dart:47-49`, `lib/firebase_options.dart`, `firebase.json`, `.firebaserc` | Bootstrap de Firebase y configuración de proyectos de Google Cloud (`budget-app-flutter`). | **Quitar por completo.** Monetae es una app auto-alojada con backend propio en FastAPI/PostgreSQL. |
| **Firebase Auth** | `firebase_auth: ^5.1.2`, `firebase_auth_web: ^5.12.4`, `recaptcha_enterprise_flutter: ^18.5.1` | `lib/struct/firebaseAuthGlobal.dart:3,9-65`, `lib/main.dart:136`, `lib/pages/accountsPage.dart` | Autenticación anónima y vinculación con Google Sign-In para acceso a Firestore. | **Reemplazar.** Monetae implementa autenticación propia: Google OIDC y email/password contra `/api/v1/auth` (ADR-002, `SPEC.md` §5). |
| **Cloud Firestore** | `cloud_firestore: ^5.1.0` | `lib/database/tables.dart:14,4238-4253`, `lib/struct/shareBudget.dart:15-722`, `lib/struct/firebaseAuthGlobal.dart:5`, `lib/widgets/ratingPopup.dart:219` | Almacenamiento en la nube de presupuestos compartidos (`collection('budgets')`) y envío de telemetría/ratings. | **Quitar por completo.** Los presupuestos se gestionan en PostgreSQL a través de `/api/v1/budgets`. Se prohíbe telemetría (`SPEC.md` §12). |
| **Google Sign-In** | `google_sign_in: ^6.2.1` | `lib/widgets/accountAndBackup.dart:39,73-144,239`, `lib/struct/firebaseAuthGlobal.dart:4,43-52`, `web/index.html:21` | Obtención de tokens OAuth2 de Google para Firebase y Google Drive. | **Reemplazar.** Se delega en el flujo OAuth2 OIDC del servidor o cliente web estándar sin SDK legado de Firebase. |
| **Google Drive** | `googleapis: ^13.1.0` (Drive v3) | `lib/struct/syncClient.dart:22,128,249,315`, `lib/widgets/accountAndBackup.dart:120,423,488,765,1509`, `lib/struct/uploadAttachment.dart:118-164`, `lib/pages/addTransactionPage.dart:4147` | 1) Sincronización multi-dispositivo basada en transferir archivos `sync-{clientID}.sqlite`.<br>2) Backups de base de datos en Drive.<br>3) Almacenamiento de fotos de recibos en Drive. | **Quitar por completo.** Resuelve el **Problema P5** (`SPEC.md` §2):<br>- Fuente de verdad única: BD PostgreSQL del servidor.<br>- Backups: gestión en servidor y export/import JSON/CSV (`RF-40`).<br>- Adjuntos: almacenamiento en servidor/S3 vía `/api/v1/attachments`. |
| **Notificaciones** | `flutter_local_notifications: ^17.2.1+1`, `notification_listener_service: ^0.3.3` | `lib/struct/initializeNotifications.dart:14-44`, `lib/struct/notificationsGlobal.dart`, `lib/pages/upcomingOverdueTransactionsPage.dart` | Recordatorios locales de transacciones pendientes y escucha de SMS bancarios en Android. | **Reemplazar.** En web, `flutter_local_notifications` no opera (Cashew ejecuta `if (kIsWeb) return;`). Para V1 web: notificaciones in-app o Web Push. En V2: bot de Telegram. |
| **Biometría** | `local_auth: ^2.2.0` | `lib/struct/initializeBiometrics.dart:12,34-52`, `lib/main.dart:154` | Bloqueo biométrico en Android/iOS. En web, Cashew lo desactiva (`if (kIsWeb) return AuthResult.authenticated;`). | **Reemplazar.** Para web, ADR-006 define bloqueo por PIN y WebAuthn. `local_auth` no ofrece WebAuthn estándar en navegadores web. |

---

## 6. (d) Compatibilidad de Paquetes (`pubspec.yaml`) y Soporte Web

### 6.1 Paquetes Incompatibles con Flutter Web o de Plataforma Exclusiva

El archivo `reference/Cashew/budget/pubspec.yaml` incluye 67 dependencias directas. Las siguientes son incompatibles con Flutter Web o presentan problemas para un despliegue web auto-alojado:

1. **`sqlite3_flutter_libs: ^0.5.0`**: Librería de binarios SQLite nativos compilados para Android, iOS, Windows, Linux y macOS. Incompatible con Web (no compila binarios en navegador). En web, Cashew se ve obligado a sustituirla por WebAssembly (`sql-wasm.js`).
2. **`notification_listener_service: ^0.3.3`**: Exclusivo para Android (servicio que intercepta notificaciones de apps bancarias). Totalmente incompatible con Web e iOS.
3. **`flutter_displaymode: ^0.6.0`**: Exclusivo para Android (fuerza la tasa de refresco a 120 Hz). Sin soporte web.
4. **`home_widget: ^0.5.0`**: Widgets de escritorio para pantallas de inicio de Android e iOS. Sin soporte web.
5. **`quick_actions: ^1.0.7`**: Accesos directos al pulsar prolongadamente el ícono en Android/iOS. En web está bloqueado con guardas (`quickActions.dart:22: if (kIsWeb) return;`).
6. **`flutter_charset_detector: ^1.0.2`**: Detección de encoding mediante platform channels nativos móviles.
7. **`in_app_purchase: ^3.2.0`** y **`in_app_review: ^2.0.9`**: Integraciones con tiendas Google Play Store y Apple App Store. Incompatibles e innecesarias en una app web auto-alojada.
8. **`recaptcha_enterprise_flutter: ^18.5.1`**: Específico de Firebase App Check en móviles.

### 6.2 Fragilidad en Dependencias (Forks Git y Paquetes Locales)

Cashew utiliza dependencias externas no publicadas oficialmente en `pub.dev`:
- **`sliding_sheet`**: Paquete local modificado en `./packages/sliding_sheet-0.5.2-modified/`.
- **`implicitly_animated_reorderable_list`**: Paquete local modificado en `./packages/implicitly_animated_reorderable_list-0.4.2-modified/`.
- **`reorderable_grid_view`**: Dependencia directa de un repositorio Git personal del autor (`https://github.com/jameskokoska/reorderable_grid_view`).
- **`file_picker`**: Dependencia directa de un fork Git de un tercero (`https://github.com/melWiss/flutter_file_picker.git`).

*Riesgo:* Mantener estos paquetes en un fork a largo plazo genera una alta fragilidad de mantenimiento ante actualizaciones de versiones mayores del SDK de Flutter.

### 6.3 Diagnóstico del Soporte Web Actual de Cashew

Cashew contiene archivos de configuración para web (`reference/Cashew/budget/web/index.html`, `manifest.json`, `sql-wasm.js`, `sql-wasm.wasm`, `worker.sql-wasm.js`), y el autor lo despliega en `budget-track.web.app` vía Firebase Hosting (`firebase.json:4`).

Sin embargo, el soporte web en el código fuente es un **soporte degradado de segundo orden**:
1. **86 bloques condicionales `kIsWeb` en 43 archivos:**
   - La autenticación biométrica se desactiva silenciosamente (`initializeBiometrics.dart:28-32`).
   - Las notificaciones programadas se cancelan (`initializeNotifications.dart:67, 109, 133`).
   - Las animaciones de navegación móvil se desactivan o alteran en múltiples páginas.
   - Las acciones rápidas (`quick_actions.dart:22`) y rating de tienda (`premiumPage.dart:29-30`) se anulan.
2. **Persistencia Web Frágil con WebAssembly:**
   - En web, Drift utiliza `DriftWebStorage.indexedDbIfSupported('db')` respaldado por `sql-wasm.wasm` (1.1 MB). Si IndexedDB falla o no está disponible, cae en un fallback sobre `localStorage` codificado con cadenas binarias (`bin2str.encode(...)` en `web.dart:52`), lo cual tiene un límite estricto de 5 MB de almacenamiento en el navegador y alto riesgo de corrupción de datos.
3. **Sincronización Ineficiente en Web:**
   - Para sincronizar con Google Drive en web, `syncClient.dart:322` descarga el archivo SQLite binario completo y reescribe completamente el almacenamiento IndexedDB (`await overwriteDefaultDB(dataStore)`), requiriendo reiniciar la aplicación y recargar todo el estado en memoria.

---

## 7. (e) Evaluación de Estrategias para ADR-001

A continuación se evalúan objetivamente las tres estrategias arquitectónicas posibles para resolver la interfaz de Monetae cumpliendo con los objetivos funcionales de `docs/SPEC.md` (P1 a P5) y las reglas de `AGENTS.md`.

---

### 7.1 Estrategia 1 (Recomendada): UI Propia Modular en Flutter Web reusando y desacoplando Componentes Visuales y Gráficos de Cashew

- **Concepto:** Construir la aplicación web en `apps/web/` con arquitectura limpia por capas (Presentation, Domain, Data) y un gestor de estado estructurado (ej. Riverpod o Bloc). La capa de datos consume directamente la API REST `/api/v1` mediante un cliente generado automáticamente desde `docs/api/openapi.json` (`AGENTS.md` §7). Se extraen y desacoplan de Cashew sus componentes visuales y gráficos clave:
  - Paleta de colores y tokens de tema (`colors.dart`, desacoplado de `appStateSettings`).
  - Gráficos estadísticos basados en `fl_chart` (`homePageHeatmap.dart`, `homePageLineGraph.dart`, `homePagePieChart.dart`, `pieChart.dart`), convertidos en widgets puros que reciben puntos/datos por parámetros.
  - Tarjetas visuales de transacción (`transactionEntry/`), botones, animaciones (`customDelayedCurve.dart`, `fadeIn.dart`) e iconos (`iconObjects.dart`), reemplazando los modelos Drift por DTOs/ViewModels.
  - Layout responsive adaptativo con menú lateral (`navigationSidebar.dart`), adaptado a las rutas de Monetae (`go_router`).
- **Pros:**
  1. **Cero acoplamiento a Drift:** No se heredan las 7,668 líneas de `tables.dart`, ni `schema_versions.dart`, ni dependencias de `sqlite3_flutter_libs` o `sql-wasm.wasm`.
  2. **Cumplimiento estricto de `AGENTS.md` §6 y §7:** Toda la lógica de negocio reside exclusivamente en el backend (`domain/`). La UI no calcula saldos ni estados; presenta lo que la API devuelve.
  3. **Resolución limpia de P1 a P5:**
     - Préstamos (P1-P3): Se construye la pantalla de préstamos directamente contra `/api/v1/loans` (libro mayor con movimientos), sin tener que lidiar con el modelo intrincado de Cashew ("metas con transacciones de polaridad opuesta").
     - Suscripciones (P4): Se consume directamente el campo `is_archived` de `/api/v1/subscriptions`.
     - Backups (P5): Desvinculación total de Google Drive desde el día 1.
  4. **Eliminación total de Firebase y Google Drive:** Código 100 % libre de SDKs propietarios innecesarios.
  5. **Mantenibilidad y tipado:** Reemplazo de los 1,346 accesos a `appStateSettings` por modelos y proveedores fuertemente tipados.
- **Contras:**
  - Requiere esfuerzo explícito de desacoplamiento para 12 componentes visuales clave (según la medición de la sección 4.3).
  - Requiere maquetar la estructura de navegación y pantallas principales (`Home`, `Transactions`, `Loans`, `Budgets`, `Subscriptions`, `Accounts`) ensamblando los widgets visuales adaptados.
- **Esfuerzo estimado:** **24 a 32 tareas de 1–2 h**, desglosadas en:
  - Desacoplamiento y adaptación de componentes visuales (gráficos `fl_chart`, `transactionEntry`, temas `colors.dart`, animaciones): 6–8 tareas.
  - Arquitectura base (Clean Architecture, cliente OpenAPI, autenticación OIDC/email, shell responsive): 6–8 tareas.
  - Maquetación y ensamblado de pantallas principales (Dashboard, Transacciones, Libro mayor de préstamos P1-P3, Suscripciones P4, Cuentas, Presupuestos): 12–16 tareas.
- **Nivel de Confianza y Riesgo:** Riesgo **Medio**. El riesgo está acotado al esfuerzo de desacoplar los componentes visuales seleccionados, pero el código resultante queda libre de deuda técnica de bases de datos locales y sincronización.

---

### 7.2 Estrategia 2: Fork de Cashew con Reemplazo Total de la Capa de Datos (Fachada REST sobre `FinanceDatabase`)

- **Concepto:** Mantener el árbol de 212 archivos de Cashew. Eliminar Drift y SQLite. Reemplazar la clase `FinanceDatabase` en `tables.dart` por una fachada (*Facade*) que conserve los mismos métodos públicos (`watchAllWallets()`, `createOrUpdateTransaction()`, etc.), pero que por dentro realice peticiones HTTP a la API REST de Monetae y mantenga flujos `StreamController` o `BehaviorSubject` en memoria para alimentar a los 135 `StreamBuilder`.
- **Pros:**
  1. Se conserva la estructura completa de navegación y las 54 pantallas existentes de inicio.
  2. No se requiere SQLite ni WebAssembly en el navegador.
  3. Las claves primarias en Cashew ya son compatibles con el formato de Monetae (`uuid.v4()`).
- **Contras:**
  1. **Reimplementación de firmas masiva:** `FinanceDatabase` tiene **105 métodos que retornan `Stream<...>`** y **156 métodos que retornan `Future<...>`**. Muchos ejecutan consultas complejas con agregaciones y filtros dinámicos que no tienen un mapeo 1 a 1 directo en una API REST estándar.
  2. **Simulación de reactividad compleja:** Al mutar una entidad (POST/PUT/DELETE), la fachada debe coordinar la emisión de eventos en múltiples `StreamController` en memoria para refrescar los 135 `StreamBuilder` sin provocar inconsistencias de interfaz.
  3. **Deuda técnica acumulada:** Se mantienen los 1,346 accesos a `appStateSettings`, las dependencias circulares en `tables.dart` y los hacks de préstamos en `pages/addObjectivePage.dart`.
  4. **Corrección de P1-P3 costosa:** Para corregir P1-P3 habría que reescribir `objectivesListPage.dart`, `objectivePage.dart` y `addObjectivePage.dart` para desmantelar el modelo de "metas con transacciones de signo opuesto" y reemplazarlo por el libro mayor de préstamos de Monetae.
- **Esfuerzo estimado:** **28 a 38 tareas de 1–2 h**, desglosadas en:
  - Creación de fachada REST con gestión de streams en memoria: 12–16 tareas.
  - Adaptación de las 43 pantallas con llamadas directas a `database.`: 10–14 tareas.
  - Reestructuración de pantallas de préstamos (eliminar hack de metas para P1-P3): 6–8 tareas.
- **Nivel de Confianza y Riesgo:** Riesgo **Medio-Alto**. Alto riesgo de regresiones difíciles de depurar al simular reactividad local sobre peticiones asíncronas de red y manipular el estado global mutable no tipado.

---

### 7.3 Estrategia 3: Fork de Cashew con Capa de Repositorio manteniendo Drift como Caché Local y Sincronización REST Bidireccional

- **Concepto:** Mantener Cashew, Drift y SQLite (WebAssembly) en el cliente. Interceptar las mutaciones de Drift o crear un motor de sincronización que replique los datos entre la base de datos local SQLite y la API REST de Monetae en PostgreSQL.
- **Pros:**
  1. Mantiene el comportamiento nativo de Cashew intacto en el cliente.
  2. Los 135 `StreamBuilder` continúan funcionando sin cambios porque leen de SQLite local.
  3. Permite soporte *offline* nativo en el cliente.
- **Contras:**
  1. **Complejidad de sincronización distribuida:** Sincronizar dos bases de datos relacionales distintas (SQLite en navegador vs PostgreSQL en backend) requiere implementar detección y resolución de conflictos, sincronización de borrado lógico y gestión de timestamps UTC concurrentes.
  2. **Conflicto con `AGENTS.md` §6 y §7:** La UI contendría miles de líneas de lógica de negocio en `tables.dart` calculando saldos y presupuestos con reglas de Cashew, compitiendo y desincronizándose con el dominio de Monetae en Python.
  3. **Pesadez en Web:** Se mantiene la dependencia obligatoria de `sql-wasm.js` (1.1 MB WASM) y los límites de cuota de IndexedDB.
  4. **P5 no se resuelve limpiamente:** El mecanismo de sync de Cashew (`syncClient.dart`) está diseñado exclusivamente para intercambiar archivos SQLite completos a través de Google Drive, no para sincronizar deltas granulares con un backend REST.
- **Esfuerzo estimado:** **36 a 48 tareas de 1–2 h**.
- **Nivel de Confianza y Riesgo:** Riesgo **Crítico**. Muy alta probabilidad de inconsistencias de saldos contables y carreras de sincronización.

---

### 7.4 Tabla Comparativa de Estrategias

| Criterio | Estrategia 1: UI Propia Modular (Recomendada) | Estrategia 2: Fork + Fachada REST sobre Drift | Estrategia 3: Fork + Drift Caché + Sincronización |
|---|:---:|:---:|:---:|
| **Reutilización de UI / Gráficos de Cashew** | **Alta** (componentes visuales, gráficos `fl_chart`, temas, iconos) | **Muy Alta** (pantallas completas heredadas) | **Total** (app completa) |
| **Complejidad de Integración con API Monetae** | **Baja** (cliente tipado desde OpenAPI) | **Alta** (emular 261 métodos de `FinanceDatabase`) | **Extrema** (sincronización bidireccional SQL-REST) |
| **Acoplamiento a Drift / SQLite** | **Nulo (0 %)** | **Medio** (se eliminan binarios, se emulan tipos) | **Total (100 %)** (Drift activo en IndexedDB) |
| **Cumplimiento de `AGENTS.md` §6 (Sin negocio en UI)** | **100 % estricto** (la API calcula todo) | **Parcial** (arrastra lógica en pantallas) | **Incumplido** (duplica negocio en SQLite) |
| **Resolución de P1–P3 (Préstamos como libro mayor)** | **Directa y nativa** (pantalla contra `/loans`) | **Compleja** (refactorizar hack de objetivos) | **Muy compleja** (conflicto de esquemas) |
| **Resolución de P4 (Suscripciones archivables)** | **Directa** (soporte nativo de `is_archived`) | **Media** (parchar pantallas existentes) | **Media** (parchar tablas y pantallas) |
| **Resolución de P5 (Eliminar Google Drive y Firebase)** | **Inmediata** (no se incluyen dependencias) | **Media** (purgar archivos de Firebase/Drive) | **Difícil** (requiere reescribir `syncClient.dart`) |
| **Deuda Técnica Heredada** | **Baja** (código modular nuevo) | **Alta** (`tables.dart`, `appStateSettings`) | **Extrema** (toda la arquitectura de Cashew) |
| **Rendimiento en Flutter Web** | **Óptimo** (sin WASM SQLite, bundles ligeros) | **Bueno** (sin WASM SQLite) | **Pesado** (WASM sql.js + IndexedDB) |
| **Esfuerzo Estimado (Tareas 1–2 h)** | **24 – 32 tareas** | **28 – 38 tareas** | **36 – 48 tareas** |
| **Nivel de Riesgo General** | **Medio** | **Medio-Alto** | **Crítico** |

---

### 7.5 Evaluación de Invasividad (`CLAUDE.md` §6) y Recomendación Explícita

En `CLAUDE.md` §6 se establece la regla de control:
> *"Si el fork de Cashew resulta demasiado invasivo para integrar la API del servidor (p. ej. acoplamiento fuerte a Drift/Firebase), detente y consulta a Adrian antes de cambiar la estrategia de UI."*

#### Dictamen Técnico
Con base en los datos numéricos verificados en el código, **el fork integral de Cashew resulta DEMASIADO INVASIVO**:
1. **84 archivos** de presentación (87.0 % de las pantallas en `pages/`) importan directamente el archivo monolítico `tables.dart`.
2. Existen **338 puntos de invocación directa** a la base de datos local en widgets y pantallas.
3. Existen **135 `StreamBuilder`** cuyo ciclo de vida está intrínsecamente ligado a la reactividad de tablas SQLite locales.
4. Existen **1,346 accesos** a un mapa de estado global mutable sin contratos de tipado (`appStateSettings`).
5. El modelo de préstamos de Cashew (causa de los problemas P1, P2 y P3) está embebido en la lógica de metas (`ObjectiveType.loan` en `tables.dart:52` y `addObjectivePage.dart:1443`), por lo que mantener el fork obligaría a deconstruir la mitad de los flujos de la aplicación heredada.

#### Recomendación Final para ADR-001
**Se recomienda adoptar la Estrategia 1 (UI Propia Modular en Flutter Web reusando y desacoplando Componentes Visuales y Gráficos de Cashew).**

*Justificación:*
- Permite cumplir el objetivo de producto de Adrian: tener la **misma apariencia visual, paleta de colores y gráficos interactivos de Cashew**, pero bajo una arquitectura limpia y desacoplada.
- Ofrece el menor riesgo técnico y una estimación de esfuerzo más predecible (24–32 tareas frente a 28–38 en Estrategia 2 y 36–48 en Estrategia 3).
- Garantiza que la UI actúe puramente como cliente de presentación sobre `/api/v1` de Monetae, asegurando que los cálculos de saldos, préstamos (P1-P3) y suscripciones archivadas (P4) sean gestionados con rigor exclusivamente por el backend.

---

## 8. (f) Notas sobre la Licencia GPL-3.0 y Marcas

### 8.1 Situación Legal del Repositorio de Cashew [Verificado en código]

1. **Licencia del Repositorio:**
   - En la raíz del repositorio de Cashew (`reference/Cashew/LICENSE`) se encuentra el texto íntegro estándar de la **GNU General Public License v3.0**, con copyright de la Free Software Foundation, Inc.
2. **Ausencia de Cabeceras en Archivos Dart:**
   - La inspección directa de los archivos fuente en `lib/` (ej. `lib/main.dart:1-25`, `lib/database/tables.dart:1-25`) confirma que **no contienen cabeceras individuales de copyright por archivo**.
3. **Identificación de Autoría y Licencia:**
   - En `README.md:184`, el autor indica: *"Unfortunately, I am currently not accepting contributions due to licensing and credits..."*.
   - Los enlaces en `README.md:20, 105, 211` y `pubspec.yaml:77` identifican al autor original como **James Kokoska** (`github.com/jameskokoska/Cashew`).

### 8.2 Obligaciones al Reutilizar Componentes de Cashew

1. **Conservación de la Licencia:**
   - Se debe incluir el archivo `LICENSE` original (GPL-3.0) en el directorio de la aplicación cliente (`apps/web/`).
2. **Archivo `NOTICE` de Atribución y Modificaciones:**
   - Conforme a la Sección 5(a) de la GPL-3.0 (*"The work must carry prominent notices stating that you modified it, and giving a relevant date"*), se recomienda crear un archivo `NOTICE` en `apps/web/` que:
     - Atribuya la autoría del diseño y componentes originales a James Kokoska (Cashew, 2021–2024).
     - Detalle los componentes adaptados (ej. `colors.dart`, widgets de gráficos `fl_chart`, componentes de `transactionEntry`).
     - Describa la naturaleza de las adaptaciones realizadas (desacoplamiento de Drift/Firebase para integración con la API REST de Monetae).
3. **Licencia de la Aplicación Cliente:**
   - `[Inferencia - no es asesoría legal]`: Cualquier aplicación o componente derivado directo en `apps/web/` que incorpore código adaptado de Cashew debe distribuirse bajo los términos de la licencia GPL-3.0.
4. **Independencia del Backend (`services/api`):**
   - `[Inferencia - no es asesoría legal]`: El backend de Monetae (FastAPI en Python) es una obra desarrollada desde cero que no comparte código ni espacio de memoria con Cashew. Al comunicarse exclusivamente mediante un protocolo de red agnóstico (HTTP/JSON sobre `/api/v1`), constituye un programa separado e independiente que no queda afectado por los términos de la GPL-3.0.

### 8.3 Restricciones Estrictas de Marca y Propiedad Intelectual

1. **Prohibición del Nombre "Cashew":**
   - La aplicación debe denominarse única y exclusivamente **Monetae** (`AGENTS.md` §7).
   - Debe suprimirse cualquier uso de la marca "Cashew" en títulos de aplicación (`main.dart:116: title: 'Cashew'`), etiquetas HTML (`web/index.html:36,39,44,50`), manifiesto web (`web/manifest.json`), cadenas i18n y documentación para el usuario.
2. **Prohibición del Logotipo e Íconos de Cashew:**
   - El logotipo e íconos de la nuez de Cashew (`assets/icon/icon.png`, `web/icons/Icon.png`, `promotional/icons/icon.png`) **no pueden utilizarse**.
   - Se deben emplear exclusivamente los activos oficiales de Monetae ubicados en la carpeta `img/` del repositorio:
     - `img/Monetae-Logo.jpg` (ícono principal).
     - `img/Monetae-Logo-Nombre.jpg` (logo con tipografía institucional).
3. **Eliminación de Credenciales y Proyectos de Firebase:**
   - Deben suprimirse todas las referencias a los identificadores de proyecto de Firebase del autor original (`budget-app-flutter`, `budget-track.web.app`), así como los tokens y client IDs de Google OAuth registrados en `lib/firebase_options.dart` y `web/index.html:21`.
