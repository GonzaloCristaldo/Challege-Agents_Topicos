# Sistema de Gestión de Reservas de Laboratorio con Agentes

[![CI Tests](https://github.com/GonzaloCristaldo/Challege-Agents_Topicos/actions/workflows/ci.yml/badge.svg)](https://github.com/GonzaloCristaldo/Challege-Agents_Topicos/actions/workflows/ci.yml)

Solución verificable para la coordinación de reservas de equipamiento de laboratorio, desarrollada mediante asistencia de un agente de programación bajo el entorno **Google Antigravity IDE** con el modelo **Gemini 3.8 Flash**.

---

## 1. Especificación Breve

### 1.1. Problema y Necesidad de Negocio
La coordinación de un laboratorio gestiona pedidos mediante mensajes y planillas manuales, lo que causa tres inconsistencias operativas críticas:
* **Superposición de horarios:** Se asigna la misma unidad física a solicitantes distintos en horarios superpuestos.
* **Bloqueos por cancelación:** Al cancelarse un turno, la unidad continúa figurando como ocupada impidiendo su reutilización.
* **Falta de auditoría:** Pérdida del historial de reservas y cancelaciones previas.

### 1.2. Alcance
* **Dentro del alcance:**
  * Lectura de inventario precargado e inmutable con 5 equipos físicos.
  * Consulta determinista de disponibilidad por unidad e intervalo semiabierto `[inicio, fin)`.
  * Creación de reservas con identificador único, solicitante ficticio y rango temporal.
  * Cancelación de reservas liberando el horario pero conservando el identificador y sus datos históricos.
  * Persistencia en disco local (JSON) con recuperación completa tras reinicios.
* **Fuera del alcance:** Autenticación/roles de usuarios, pagos, notificaciones por email, base de datos distribuida y frontend gráfico complejo.

### 1.3. Inventario Precargado
| ID de Unidad | Equipo |
| :--- | :--- |
| `MIC-01` | Microscopio digital |
| `MIC-02` | Microscopio digital |
| `OSC-01` | Osciloscopio |
| `MUL-01` | Multímetro |
| `FUE-01` | Fuente de alimentación |

### 1.4. Reglas de Negocio e Invariantes
* **RN-01 (Unidad Conocida):** La unidad debe existir en el catálogo precargado.
* **RN-02 (Solicitante Válido):** No puede ser nulo ni compuesto solo de espacios en blanco.
* **RN-03 (Consistencia Temporal):** Formato ISO 8601 (`YYYY-MM-DDTHH:MM`). El `inicio` debe ser estrictamente anterior al `fin` (`inicio < fin`).
* **RN-04 (Rechazo de Superposición):** Se rechaza cualquier solapamiento horario entre reservas activas para una misma unidad:
  $$\max(inicio_1, inicio_2) < \min(fin_1, fin_2)$$
* **RN-05 (Límites Consecutivos Permitidos):** Intervalos semiabiertos `[inicio, fin)`. Si $fin_1 = inicio_2$, se permite la reserva contigua.
* **RN-06 (Simultaneidad entre Unidades):** Unidades distintas pueden reservarse en el mismo intervalo sin conflicto.
* **RN-07 (Canceladas no Bloquean):** Una reserva cancelada no interfiere con nuevas solicitudes.
* **RN-08 (Idempotencia de Cancelación):** Cancelar una reserva ya cancelada arroja un error controlado.

### 1.5. Supuestos Técnicos
* **Formato de fechas:** ISO 8601 estándar (`YYYY-MM-DDTHH:MM` o `YYYY-MM-DDTHH:MM:SS`).
* **Zona horaria:** Local estandarizada sin desfase arbitrario (naive datetime).
* **Tratamiento de fechas:** Se admiten fechas explícitas (pasadas o futuras) siempre que `inicio < fin`, asegurando la reproducibilidad de las pruebas automatizadas en cualquier momento temporal sin depender del reloj del sistema.
* **Límites:** Sin restricción artificial de anticipación máxima.

> La especificación detallada completa se encuentra documentada en [docs/especificacion.md](docs/especificacion.md).

---

## 2. Solución

### 2.1. Estructura del Proyecto
```text
Challege-Agents_Topicos/
├── .github/
│   └── workflows/
│       └── ci.yml              # Pipeline de Integración Continua (GitHub Actions)
├── .gitignore
├── app.py                      # Interfaz gráfica interactiva web (Streamlit)
├── pyproject.toml              # Configuración moderna del proyecto y pytest
├── requirements.txt            # Dependencias del proyecto (pytest, streamlit)
├── README.md                   # Documentación central del desafío
├── Documentos/                 # Consignas de la cátedra
│   └── challenge-agents.pdf
├── docs/                       # Documentación extendida
│   ├── especificacion.md       # Especificación y criterios de aceptación
│   └── preparacion_agente.md   # Configuración, harness y adaptaciones del agente
├── data/                       # Almacenamiento y persistencia
│   ├── inventario.json         # Catálogo fijo precargado
│   └── reservas.json           # Persistencia de reservas (generado al operar)
├── src/                        # Código fuente modular
│   ├── __init__.py
│   ├── modelos.py              # Entidades: Equipo, Reserva, EstadoReserva, Excepciones
│   ├── repositorio.py          # Repositorio JSON con persistencia atómica
│   ├── servicio.py             # Lógica de negocio, validaciones y colisiones
│   └── cli.py                  # Interfaz de línea de comandos interactiva
├── scripts/                    # Scripts de soporte y utilitarios
│   └── demo.py                 # Demostración interactiva guiada end-to-end
└── tests/                      # Suite de pruebas automatizadas
    ├── __init__.py
    ├── conftest.py             # Fixtures con tmp_path aislado
    ├── test_reservas.py        # Casos de prueba requeridos por la consigna
    ├── test_cli.py             # Pruebas automatizadas de la CLI
    ├── test_demo.py            # Validación automatizada del script de demo
    └── test_app.py             # Validación de la interfaz gráfica Streamlit
```

### 2.2. Decisiones Técnicas y Requisitos Previos
* **Lenguaje:** Python 3.10 o superior (desarrollado y probado sobre Python 3.14.0).
* **Dependencias:** `pytest` para testing automatizado (incluido en `requirements.txt`).
* **Persistencia:** Archivo JSON local (`data/reservas.json`) con serialización atómica (escritura en archivo temporal `.tmp` y posterior reemplazo atómico) y soporte UTF-8.

### 2.3. Instalación y Ejecución
1. **Clonar el repositorio:**
   ```bash
   git clone <url-del-repositorio>
   cd Challege-Agents_Topicos
   ```
2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Ejecutar la suite de pruebas automatizadas:**
   ```bash
   python -m pytest -v
   ```
4. **Ejecutar la demostración guiada completa:**
   ```bash
   python scripts/demo.py
   ```
5. **Ejecutar la aplicación de consola (CLI):**
   ```bash
   python -m src.cli --help
   ```
6. **Ejecutar la interfaz gráfica interactiva (Streamlit):**
   ```bash
   python -m streamlit run app.py
   ```

### 2.4. Ejemplos de Entrada y Salida (Comandos CLI)

#### Consultar inventario:
```bash
python -m src.cli inventario
```
*Salida:*
```text
--- INVENTARIO DE EQUIPOS DE LABORATORIO ---
ID         | DESCRIPCIÓN
---------------------------------------------
MIC-01     | Microscopio digital
MIC-02     | Microscopio digital
OSC-01     | Osciloscopio
MUL-01     | Multímetro
FUE-01     | Fuente de alimentación

Total: 5 unidades precargadas.
```

#### Crear una reserva:
```bash
python -m src.cli reservar MIC-01 "Dr. Bernardo Houssay" 2026-11-01T10:00 2026-11-01T11:00
```
*Salida:*
```text
=== RESERVA CONFIRMADA EXITOSAMENTE ===
ID Reserva  : RES-46AB2B60
Unidad      : MIC-01
Solicitante : Dr. Bernardo Houssay
Inicio      : 2026-11-01T10:00:00
Fin         : 2026-11-01T11:00:00
Estado      : ACTIVA
```

#### Consultar disponibilidad ante superposición:
```bash
python -m src.cli disponibilidad MIC-01 2026-11-01T10:30 2026-11-01T11:30
```
*Salida:*
```text
[NO DISPONIBLE] La unidad 'MIC-01' está OCUPADA por la reserva 'RES-46AB2B60' (Dr. Bernardo Houssay) entre 2026-11-01T10:00:00 y 2026-11-01T11:00:00.
```

#### Consultar disponibilidad en límite consecutivo permitido:
```bash
python -m src.cli disponibilidad MIC-01 2026-11-01T11:00 2026-11-01T12:00
```
*Salida:*
```text
[DISPONIBLE] La unidad 'MIC-01' está LIBRE entre 2026-11-01T11:00:00 y 2026-11-01T12:00:00.
```

#### Cancelar reserva y liberar horario:
```bash
python -m src.cli cancelar RES-46AB2B60
```
*Salida:*
```text
=== RESERVA CANCELADA ===
ID Reserva  : RES-46AB2B60
Unidad      : MIC-01
Solicitante : Dr. Bernardo Houssay
Horario     : 2026-11-01T10:00:00 a 2026-11-01T11:00:00
Nuevo Estado: CANCELADA (Horario liberado)
```

### 2.5. Dónde Persisten los Datos y Advertencia de Reinicio
* Las reservas persisten en el archivo JSON local `data/reservas.json`.
* **Advertencia:** El reinicio manual o eliminación del archivo `data/reservas.json` provocará el borrado permanente de todas las reservas registradas. El catálogo `data/inventario.json` es de solo lectura y nunca se modifica.

### 2.6. Pendientes y Limitaciones
* No implementa autenticación de usuarios ni control de acceso basado en roles.
* Operación sincrónica local: no cuenta con soporte para transacciones concurrentes distribuidas multi-nodo en entornos cloud.

---

## 3. Preparación del Agente

* **Entorno y Harness:** Google Antigravity IDE (Advanced Agentic Coding Environment).
* **Modelo:** Gemini 3.8 Flash (`gemini-3.8-flash-high`) de Google DeepMind.
* **Función y Elección:** Pair programmer agentic capaz de razonar sobre invariantes matemáticos, estructurar código modular y ejecutar pruebas automatizadas en la terminal PowerShell con baja latencia.
* **Instrucciones y Contexto Saneado:** Se suministró la consigna oficial (`challenge-agents.pdf`) y directivas de arquitectura limpia. Se excluyeron deliberadamente secretos, APIs pagas y componentes fuera de alcance.
* **Herramientas Utilizadas y Controles Humanos:**
  * Filesystem (`read_file`, `write_file`, `edit_file`) y Terminal (`run_command`).
  * Toda propuesta y comando fue revisado y validado interactivamente por el usuario humano.
* **Adaptaciones Específicas Comprobables:**
  1. *Intervalos Semiabiertos para Límites Consecutivos:* Formulación matemática $\max(inicio_1, inicio_2) < \min(fin_1, fin_2)$ que garantiza la aceptación de turnos contiguos (evidencia en [src/modelos.py](src/modelos.py) y [tests/test_reservas.py](tests/test_reservas.py)).
  2. *Inyección de Rutas para Persistencia Aislada:* Desacoplamiento de las rutas de persistencia en `JsonReservaRepositorio` permitiendo tests no destructivos con `tmp_path` (evidencia en [tests/conftest.py](tests/conftest.py)).

> Documentación ampliada disponible en [docs/preparacion_agente.md](docs/preparacion_agente.md).

---

## 4. Registro de Decisiones y Delegación

### 4.1. Decisiones Significativas
* **Persistencia en JSON:** Se priorizó JSON estructurado sobre SQLite por su total transparencia, facilidad de inspección directa sin clientes externos y portabilidad nativa.
* **Intervalos Semiabiertos `[inicio, fin)`:** Eliminan ambigüedad en los extremos de turnos y formalizan el comportamiento de límites consecutivos.
* **Centralización en Capa de Servicio:** Las validaciones de invariantes residen exclusivamente en `ReservaServicio`, asegurando que la CLI y las pruebas compartan las mismas reglas.

### 4.2. Tres Episodios Reales de Delegación

#### Episodio 1: Modelado de Dominio e Invariantes con Límites Consecutivos
* **Objetivo y requisito:** Implementar las entidades de dominio y el algoritmo de detección de solapamientos que permita límites consecutivos, rechace superposiciones en la misma unidad y admita unidades simultáneas.
* **Contexto e instrucción suministrada:**
  > *"Define las entidades `Equipo`, `Reserva`, `EstadoReserva` y una función pura `hay_superposicion` basada en intervalos semiabiertos `[inicio, fin)` tal que $\max(inicio_1, inicio_2) < \min(fin_1, fin_2)$ para que turnos contiguos no colisionen."*
* **Acción o resultado del agente:** Implementación de [src/modelos.py](src/modelos.py) con dataclasses, enumeración de estados y excepciones de dominio especializadas.
* **Decisión humana:** *Aceptado.* Se verificó analíticamente que la desigualdad estricta `<` garantiza que si $fin_1 = inicio_2$, el resultado es `False` (sin colisión).
* **Evidencia verificable:** Pruebas `test_limites_consecutivos_permitidos`, `test_rechazo_superposicion_misma_unidad` y `test_simultaneidad_unidades_distintas` en [tests/test_reservas.py](tests/test_reservas.py).

#### Episodio 2: Capa de Persistencia Atómica y Aislamiento de Pruebas
* **Objetivo y requisito:** Desarrollar el repositorio de persistencia local en JSON con soporte de inyección de rutas para testing reproducible sin afectar los datos reales.
* **Contexto e instrucción suministrada:**
  > *"Crea `JsonReservaRepositorio` para gestionar `data/reservas.json` y `data/inventario.json`. Permite parametrizar las rutas en el constructor y utiliza escritura atómica mediante archivos temporales."*
* **Acción o resultado del agente:** Creación de [src/repositorio.py](src/repositorio.py) con escritura segura (`.tmp` $\to$ `.replace()`) y fixture `repo_aislado` con `tmp_path` en [tests/conftest.py](tests/conftest.py).
* **Decisión humana:** *Aceptado.* Se revisó el mecanismo atómico y se validó la recuperación completa tras reiniciar el servicio.
* **Evidencia verificable:** Prueba `test_persistencia_recupera_estado_tras_reinicio` en [tests/test_reservas.py](tests/test_reservas.py).

#### Episodio 3: Interfaz CLI, Manejo de Codificación y Verificación Humana
* **Objetivo y requisito:** Diseñar la interfaz de comandos de consola (`src/cli.py`) con subcomandos completos y validación ante fallos.
* **Contexto e instrucción suministrada:**
  > *"Implementa la CLI con subcomandos `inventario`, `disponibilidad`, `reservar`, `cancelar` y `listar`. Muestra salidas legibles con tablas formateadas y maneja errores de negocio amigablemente."*
* **Acción o resultado del agente:** Implementación inicial de [src/cli.py](src/cli.py). Al ejecutar la prueba en la terminal PowerShell de Windows, se observaron caracteres corruptos en las tildes (`DESCRIPCIN`). El agente detectó la discordancia de página de códigos y añadió `sys.stdout.reconfigure(encoding="utf-8")`.
* **Decisión humana:** *Corregido por problema de codificación en consola Windows y aceptado tras prueba manual.* Se ejecutó manualmente la secuencia completa (reserva, consulta de superposición, límites consecutivos, cancelación, disponibilidad liberada y persistencia) y la suite automatizada completa de 17 tests.
* **Evidencia verificable:** [src/cli.py](src/cli.py), [tests/test_cli.py](tests/test_cli.py), registro de comprobaciones ejecutadas en terminal y bitácora detallada en [docs/verificacion_humana.md](docs/verificacion_humana.md).

---

## 5. Verificación de Pruebas y Resultados

Ejecución de la suite completa de pruebas:
```bash
python -m pytest -v
```

Resultado obtenido:
```text
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Topicos de Ingenieria del Software\Challege-Agents_Topicos
configfile: pyproject.toml
testpaths: tests
collected 19 items

tests/test_app.py::test_app_streamlit_importable PASSED                  [  5%]
tests/test_cli.py::test_cli_inventario PASSED                            [ 10%]
tests/test_cli.py::test_cli_ayuda_sin_argumentos PASSED                  [ 11%]
tests/test_demo.py::test_ejecucion_demostracion_sin_errores PASSED       [ 16%]
tests/test_reservas.py::test_creacion_reserva_valida PASSED              [ 22%]
tests/test_reservas.py::test_rechazo_superposicion_misma_unidad[2026-11-01T10:30-2026-11-01T11:30] PASSED [ 27%]
tests/test_reservas.py::test_rechazo_superposicion_misma_unidad[2026-11-01T09:30-2026-11-01T10:30] PASSED [ 33%]
tests/test_reservas.py::test_rechazo_superposicion_misma_unidad[2026-11-01T10:15-2026-11-01T10:45] PASSED [ 38%]
tests/test_reservas.py::test_rechazo_superposicion_misma_unidad[2026-11-01T09:00-2026-11-01T12:00] PASSED [ 44%]
tests/test_reservas.py::test_rechazo_superposicion_misma_unidad[2026-11-01T10:00-2026-11-01T11:00] PASSED [ 50%]
tests/test_reservas.py::test_limites_consecutivos_permitidos PASSED      [ 55%]
tests/test_reservas.py::test_simultaneidad_unidades_distintas PASSED     [ 61%]
tests/test_reservas.py::test_solicitante_vacio_rechazado[] PASSED        [ 66%]
tests/test_reservas.py::test_solicitante_vacio_rechazado[   ] PASSED     [ 72%]
tests/test_reservas.py::test_solicitante_vacio_rechazado[\t\n  ] PASSED  [ 77%]
tests/test_reservas.py::test_inicio_mayor_o_igual_a_fin_rechazado PASSED [ 83%]
tests/test_reservas.py::test_unidad_inexistente_rechazada PASSED         [ 88%]
tests/test_reservas.py::test_cancelacion_conserva_historial_y_libera_horario PASSED [ 94%]
tests/test_reservas.py::test_persistencia_recupera_estado_tras_reinicio PASSED [100%]

============================= 19 passed in 1.03s ==============================
```
