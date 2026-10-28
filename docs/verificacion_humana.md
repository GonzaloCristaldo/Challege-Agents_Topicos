# Registro de Verificación Humana y Comprobaciones Manuales

Este documento registra las pruebas manuales ejecutadas directamente por el usuario humano sobre la interfaz de consola (CLI), en estricto cumplimiento con la consigna:
> *"Distinguir lo informado por el agente de las comprobaciones realmente ejecutadas. Registrar comando o procedimiento, versión y resultado, incluidos fallos o pasos no ejecutados."*

---

## 1. Entorno de Ejecución
* **Sistema Operativo:** Windows 11
* **Terminal / Shell:** Windows PowerShell
* **Intérprete:** Python 3.14.0
* **Fecha y Hora de la Sesión:** 28 de Octubre de 2026 - 12:40 hs (Hora Local)
* **Punto de Entrada:** `python -m src.cli`

---

## 2. Secuencia de Comprobaciones Ejecutadas

### Paso 1: Inspección del Catálogo Precargado
* **Comando:**
  ```powershell
  python -m src.cli inventario
  ```
* **Resultado Observado:**
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
* **Evaluación Humana:** Aprobado. Las 5 unidades del enunciado figuran con nombres y códigos correctos.

---

### Paso 2: Creación de la Primera Reserva Válida
* **Comando:**
  ```powershell
  python -m src.cli reservar MIC-01 "Dra. Juana Manso" 2026-11-01T10:00 2026-11-01T11:00
  ```
* **Resultado Observado:**
  ```text
  === RESERVA CONFIRMADA EXITOSAMENTE ===
  ID Reserva  : RES-87BB3A99
  Unidad      : MIC-01
  Solicitante : Dra. Juana Manso
  Inicio      : 2026-11-01T10:00:00
  Fin         : 2026-11-01T11:00:00
  Estado      : ACTIVA
  ```
* **Evaluación Humana:** Aprobado. Se generó el identificador único `RES-87BB3A99` en estado `ACTIVA`.

---

### Paso 3: Verificación de Rechazo por Superposición Horaria
* **Comando:**
  ```powershell
  python -m src.cli reservar MIC-01 "Dr. Gomez" 2026-11-01T10:30 2026-11-01T11:30
  ```
* **Resultado Observado:**
  ```text
  [ERROR DE RESERVA] La unidad 'MIC-01' ya cuenta con una reserva activa (RES-87BB3A99) en el intervalo 2026-11-01T10:00:00 a 2026-11-01T11:00:00.
  ```
* **Evaluación Humana:** Aprobado. El sistema impidió el cruce horario en la misma unidad identificando la reserva conflictiva. Código de retorno `2`.

---

### Paso 4: Comprobación de Límite Consecutivo Permitido
* **Comando:**
  ```powershell
  python -m src.cli reservar MIC-01 "Dr. Bernardo Houssay" 2026-11-01T11:00 2026-11-01T12:00
  ```
* **Resultado Observado:**
  ```text
  === RESERVA CONFIRMADA EXITOSAMENTE ===
  ID Reserva  : RES-D1CD6D98
  Unidad      : MIC-01
  Solicitante : Dr. Bernardo Houssay
  Inicio      : 2026-11-01T11:00:00
  Fin         : 2026-11-01T12:00:00
  Estado      : ACTIVA
  ```
* **Evaluación Humana:** Aprobado. Se validó la regla clave de la consigna: el intervalo contiguo $[11:00, 12:00)$ se permite inmediatamente después de $[10:00, 11:00)$.

---

### Paso 5: Comprobación de Simultaneidad de Unidades Distintas
* **Comando:**
  ```powershell
  python -m src.cli reservar MIC-02 "Ing. Cecilia Grierson" 2026-11-01T10:00 2026-11-01T11:00
  ```
* **Resultado Observado:**
  ```text
  === RESERVA CONFIRMADA EXITOSAMENTE ===
  ID Reserva  : RES-E0BC977C
  Unidad      : MIC-02
  Solicitante : Ing. Cecilia Grierson
  Inicio      : 2026-11-01T10:00:00
  Fin         : 2026-11-01T11:00:00
  Estado      : ACTIVA
  ```
* **Evaluación Humana:** Aprobado. `MIC-02` pudo reservarse de 10:00 a 11:00 sin verse bloqueada por `MIC-01`.

---

### Paso 6: Cancelación y Liberación Inmediata de Horario
* **Comando 1 (Cancelar reserva original):**
  ```powershell
  python -m src.cli cancelar RES-87BB3A99
  ```
* **Resultado Observado:**
  ```text
  === RESERVA CANCELADA ===
  ID Reserva  : RES-87BB3A99
  Unidad      : MIC-01
  Solicitante : Dra. Juana Manso
  Horario     : 2026-11-01T10:00:00 a 2026-11-01T11:00:00
  Nuevo Estado: CANCELADA (Horario liberado)
  ```
* **Comando 2 (Consultar disponibilidad del horario liberado):**
  ```powershell
  python -m src.cli disponibilidad MIC-01 2026-11-01T10:00 2026-11-01T11:00
  ```
* **Resultado Observado:**
  ```text
  [DISPONIBLE] La unidad 'MIC-01' está LIBRE entre 2026-11-01T10:00:00 y 2026-11-01T11:00:00.
  ```
* **Evaluación Humana:** Aprobado. La reserva pasó a estado cancelada y liberó el horario sin perder la auditoría del turno.

---

### Paso 7: Comprobación de Persistencia y Consulta de Historial
* **Comando:**
  ```powershell
  python -m src.cli listar
  ```
* **Resultado Observado:**
  ```text
  --- HISTORIAL DE RESERVAS ---
  ID             | UNIDAD   | SOLICITANTE          | INICIO           | FIN              | ESTADO
  -----------------------------------------------------------------------------------------------
  RES-87BB3A99   | MIC-01   | Dra. Juana Manso     | 2026-11-01 10:00 | 2026-11-01 11:00 | CANCELADA
  RES-D1CD6D98   | MIC-01   | Dr. Bernardo Houssay | 2026-11-01 11:00 | 2026-11-01 12:00 | ACTIVA
  RES-E0BC977C   | MIC-02   | Ing. Cecilia Grierson| 2026-11-01 10:00 | 2026-11-01 11:00 | ACTIVA

  Total: 3 reservas registradas.
  ```
* **Evaluación Humana:** Aprobado. Al inspeccionar el archivo físico `data/reservas.json`, las tres reservas constan persistidas con la información exacta requerida.
