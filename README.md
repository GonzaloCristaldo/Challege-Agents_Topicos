# Sistema de Gestión de Reservas de Laboratorio con Agentes

Solución verificable para la coordinación de reservas de equipamiento de laboratorio, desarrollada mediante asistencia de un agente de programación bajo el entorno **Google Antigravity IDE** con el modelo **Gemini 3.8 Flash**.

---

## 1. Especificación Breve

### 1.1. Problema y Necesidad de Negocio
La coordinación de un laboratorio gestiona pedidos mediante mensajes y planillas manuales, lo que causa dos inconsistencias graves:
* **Superposición de horarios:** Se asigna la misma unidad física a solicitantes distintos en horarios superpuestos.
* **Bloqueos por cancelación:** Al cancelarse un turno, la unidad continúa figurando como ocupada impidiendo su reutilización.
* **Falta de auditoría:** Pérdida del historial de reservas y cancelaciones previas.

### 1.2. Alcance
* **Dentro del alcance:**
  * Lectura de inventario precargado e inmutable con 5 equipos físicos.
  * Consulta determinista de disponibilidad por unidad e intervalo `[inicio, fin)`.
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

### 1.5. Supuestos Técnicos
* **Formato de fechas:** ISO 8601 estándar (`YYYY-MM-DDTHH:MM` o `YYYY-MM-DDTHH:MM:SS`).
* **Zona horaria:** Local estandarizada sin desfase arbitrario.
* **Tratamiento de fechas:** Se admiten fechas explícitas (pasadas o futuras) siempre que `inicio < fin`, asegurando la reproducibilidad de las pruebas automatizadas en cualquier momento temporal.
* **Límites:** Sin restricción artificial de anticipación máxima.

> La especificación detallada completa se encuentra documentada en [docs/especificacion.md](docs/especificacion.md).

---

## 2. Solución

### 2.1. Estructura del Proyecto
```text
Challege-Agents_Topicos/
├── .gitignore
├── requirements.txt            # Dependencias del proyecto (pytest)
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
│   ├── modelos.py              # Entidades: Equipo, Reserva, EstadoReserva
│   ├── repositorio.py          # Repositorio JSON con persistencia atómica
│   ├── servicio.py             # Lógica de negocio, validaciones y colisiones
│   └── cli.py                  # Interfaz de línea de comandos interactiva
└── tests/                      # Suite de pruebas automatizadas
    ├── __init__.py
    ├── conftest.py             # Fixtures con tmp_path aislado
    └── test_reservas.py        # Casos de prueba requeridos por la consigna
```

### 2.2. Decisiones Técnicas y Requisitos Previos
* **Lenguaje:** Python 3.10 o superior (desarrollado y probado sobre Python 3.14.0).
* **Dependencias:** `pytest` para testing automatizado (incluido en `requirements.txt`).
* **Persistencia:** Archivo JSON local (`data/reservas.json`) con serialización atómica y manejo de codificación UTF-8.

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
4. **Ejecutar la aplicación de consola (CLI):**
   ```bash
   python -m src.cli --help
   ```

### 2.4. Ejemplos de Comandos de la CLI
* **Listar inventario:**
  ```bash
  python -m src.cli inventario
  ```
* **Consultar disponibilidad:**
  ```bash
  python -m src.cli disponibilidad MIC-01 2026-11-01T10:00 2026-11-01T11:00
  ```
* **Crear una reserva:**
  ```bash
  python -m src.cli reservar MIC-01 "Dra. Juana Manso" 2026-11-01T10:00 2026-11-01T11:00
  ```
* **Cancelar una reserva:**
  ```bash
  python -m src.cli cancelar <ID-RESERVA>
  ```
* **Listar todas las reservas (historial):**
  ```bash
  python -m src.cli listar
  ```

### 2.5. Persistencia y Advertencia sobre Reinicio de Datos
* Las reservas persisten en `data/reservas.json`.
* **Advertencia:** Eliminar o reiniciar el archivo `data/reservas.json` provocará el borrado permanente de las reservas registradas. El catálogo base en `data/inventario.json` es de solo lectura y nunca se modifica.

### 2.6. Pendientes y Limitaciones
* No implementa autenticación ni segregación de permisos por rol.
* No está diseñado para concurrencia multi-proceso distribuida en producción (utiliza lectura y escritura de archivo único sincrónico).

---

## 3. Preparación del Agente

* **Entorno y Harness:** Google Antigravity IDE (Advanced Agentic Coding Environment).
* **Modelo:** Gemini 3.8 Flash (`gemini-3.8-flash-high`) de Google DeepMind.
* **Instrucciones y Contexto:** Saneado de credenciales y acotado estrictamente a las reglas de negocio descritas en `challenge-agents.pdf`.
* **Herramientas Utilizadas:** Herramientas reales de filesystem (`read_file`, `write_file`, `edit_file`) y ejecución de comandos PowerShell (`run_command`), sujetas a revisión humana constante.
* **Adaptaciones Específicas Comprobables:**
  1. *Límites Consecutivos:* Formulación matemática de intervalos semiabiertos $\max(inicio_1, inicio_2) < \min(fin_1, fin_2)$ que garantiza la aceptación de turnos consecutivos.
  2. *Persistencia Aislada:* Desacoplamiento de la ruta del archivo de persistencia mediante inyección de dependencias para permitir tests con `tmp_path` 100% reproducibles y no destructivos.

> La documentación detallada de la preparación del agente se encuentra en [docs/preparacion_agente.md](docs/preparacion_agente.md).

---

## 4. Registro de Decisiones y Delegación

### 4.1. Decisiones Significativas
* **Persistencia en JSON vs. SQLite:** Se eligió JSON estructurado por máxima portabilidad, inspección visual directa sin dependencias adicionales y reproducibilidad inmediata en cualquier entorno con Python estándar.
* **Intervalos Semiabiertos:** Se adoptó formalmente el estándar de intervalos semiabiertos `[inicio, fin)` para eliminar ambigüedades operativas en límites contiguos.
* **Validaciones a Nivel de Capa de Servicio:** Las validaciones de negocio residen en el servicio (`ReservaServicio`), asegurando que tanto la CLI como las pruebas automatizadas apliquen exactamente las mismas reglas.

### 4.2. Tres Episodios Reales de Delegación

#### Episodio 1: Modelado de Dominio, Invariantes y Detección de Colisiones
* **Objetivo y requisito:** Implementar las entidades base y el algoritmo de verificación de solapamientos que permita límites consecutivos y rechace cruces horarios para la misma unidad.
* **Contexto e instrucción:** Se suministró la consigna sobre la regla de límites consecutivos y superposiciones.
* **Acción o resultado del agente:** Implementación de `modelos.py` y función de colisiones en `servicio.py`.
* **Decisión humana:** *Aceptado tras revisión de la fórmula matemática de intervalos semiabiertos.*
* **Evidencia verificable:** Commit y pruebas unitarias correspondientes en `tests/test_reservas.py`.

#### Episodio 2: Capa de Persistencia y Aislamiento en Pruebas
* **Objetivo y requisito:** Diseñar el repositorio de persistencia local en JSON con soporte para inyección de ruta temporal para testing.
* **Contexto e instrucción:** Requisito de persistencia que sobreviva al reinicio y necesidad de pruebas no destructivas.
* **Acción o resultado del agente:** Creación de `repositorio.py` y fixture con `tmp_path` en `conftest.py`.
* **Decisión humana:** *Aceptado y verificado ejecutando pruebas de reinicio de aplicación.*
* **Evidencia verificable:** Prueba de persistencia tras reinicio en `tests/test_reservas.py`.

#### Episodio 3: Interfaz CLI y Verificación Integral de Casos Borde
* **Objetivo y requisito:** Desarrollar la CLI interactiva y completar la suite de pruebas automatizadas con casos de borde (solicitantes vacíos, fechas invertidas, cancelaciones).
* **Contexto e instrucción:** Requisito de interfaz ejecutable por consola y verificación humana independiente.
* **Acción o resultado del agente:** Implementación de `src/cli.py` y casos de prueba negativos exhaustivos.
* **Decisión humana:** *Verificado y validado en terminal con 100% de tests pasando.*
* **Evidencia verificable:** Ejecución limpia de `python -m pytest` y comandos de CLI.
