# Especificación del Sistema de Reservas de Laboratorio

## 1. Problema de Negocio
La coordinación de un laboratorio registra pedidos de instrumental mediante mensajes y una planilla de cálculo manual. Esta metodología genera dos problemas recurrentes de inconsistencia operativa:
1. **Superposición de horarios:** Se confirma la misma unidad física a diferentes solicitantes en intervalos superpuestos.
2. **Bloqueo fantasma por cancelaciones:** Cuando un usuario cancela un turno, el horario continúa figurando como ocupado, impidiendo que otros investigadores utilicen el equipo.
3. **Pérdida de trazabilidad:** No se cuenta con un historial ordenado y persistente de las solicitudes y cancelaciones.

El sistema resuelve esta necesidad brindando un mecanismo automatizado, local y determinista para consultar disponibilidad, reservar y cancelar turnos conservando el historial completo.

---

## 2. Alcance del Proyecto

### 2.1. Dentro del Alcance (In Scope)
* **Inventario fijo precargado:** Lectura del catálogo de unidades físicas sin soporte de administración (no se requiere alta/baja/modificación de equipos).
* **Consulta de disponibilidad:** Verificación de si una unidad específica está libre en un intervalo `[inicio, fin)`.
* **Creación de reservas:** Registro de reservas indicando unidad, solicitante ficticio, fecha/hora de inicio y fin. Una única unidad por reserva.
* **Cancelación de reservas:** Marcado de reserva como cancelada conservando su identificador, solicitante y rango temporal, liberando inmediatamente el intervalo para nuevos turnos.
* **Persistencia local:** Almacenamiento en disco que asegura la recuperación del estado exacto (activas y canceladas) tras reiniciar la aplicación.
* **Validaciones estrictas y reglas de intervalo:** Tratamiento determinista de límites consecutivos, solapamientos y simultaneidad.

### 2.2. Fuera del Alcance (Out of Scope)
* Autenticación, control de acceso y roles de usuario.
* Pasarelas de pago, cobranzas o facturación.
* Notificaciones por correo electrónico, SMS o webhooks.
* Despliegue en la nube, microservicios, bases de datos distribuidas o esquemas cliente-servidor complejos.
* Interfaz gráfica compleja (se provee interfaz de consola CLI y API/servicios locales).

---

## 3. Inventario Precargado
El catálogo cuenta con 5 unidades físicas inmutables:

| ID de Unidad | Equipo |
| :--- | :--- |
| `MIC-01` | Microscopio digital |
| `MIC-02` | Microscopio digital |
| `OSC-01` | Osciloscopio |
| `MUL-01` | Multímetro |
| `FUE-01` | Fuente de alimentación |

---

## 4. Requisitos Verificables

* **RF-01 (Lectura de Inventario):** La aplicación debe cargar el inventario precargado y listar las unidades físicas con su ID y denominación.
* **RF-02 (Consulta de Disponibilidad):** Dado un `id_unidad`, `inicio` y `fin`, retornar si la unidad se encuentra disponible o rechazar con el detalle del conflicto si está ocupada.
* **RF-03 (Creación de Reserva):** Generar una reserva con identificador único (`UUID` o ID secuencial alfanumérico), registrando `id_unidad`, `solicitante`, `inicio`, `fin` y estado `ACTIVA`.
* **RF-04 (Cancelación de Reserva):** Dada una reserva existente activa, cambiar su estado a `CANCELADA`. No se borra el registro ni se alteran sus metadatos; el intervalo horario queda inmediatamente liberado.
* **RF-05 (Persistencia de Datos):** Guardar el estado en un archivo local (`data/reservas.json`). Al reiniciar la aplicación, deben recuperarse todas las reservas con sus respectivos estados (`ACTIVA` / `CANCELADA`).

---

## 5. Reglas de Negocio e Invariantes

* **RN-01 (Unidad Conocida):** La unidad solicitada debe existir obligatoriamente en el inventario precargado. De lo contrario, la operación se rechaza con error de validación.
* **RN-02 (Solicitante Válido):** El nombre del solicitante no puede ser nulo, vacío ni estar compuesto únicamente por espacios en blanco (`solicitante.strip() != ""`).
* **RN-03 (Consistencia Temporal):** Las fechas y horas deben ser parseables bajo formato ISO 8601. El instante de inicio debe ser estrictamente anterior al fin (`inicio < fin`). Si `inicio >= fin`, la solicitud es inválida.
* **RN-04 (Rechazo de Superposiciones):** Dos reservas activas de una misma unidad no pueden solaparse. Existe colisión si y solo si:
  $$\max(\text{inicio}_1, \text{inicio}_2) < \min(\text{fin}_1, \text{fin}_2)$$
  Si se detecta solapamiento con una reserva activa, la creación es rechazada.
* **RN-05 (Límites Consecutivos Permitidos):** Los intervalos se modelan como semiabiertos a derecha: `[inicio, fin)`. Si una reserva termina exactamente en el instante en que inicia otra ($\text{fin}_1 = \text{inicio}_2$), **no existe solapamiento** y ambas son válidas.
* **RN-06 (Simultaneidad entre Unidades Distintas):** Las restricciones de horario aplican por unidad física individual. Dos unidades distintas (ej. `MIC-01` y `MIC-02`) pueden estar reservadas exactamente en el mismo intervalo de tiempo.
* **RN-07 (Inactividad de Canceladas):** Las reservas en estado `CANCELADA` no bloquean el intervalo. Una nueva reserva puede ocupar total o parcialmente el rango de una reserva cancelada previa.
* **RN-08 (Idempotencia de Cancelación):** Intentar cancelar una reserva ya cancelada debe arrojar un error semántico claro o advertencia, sin alterar el estado del sistema.

---

## 6. Supuestos Técnicos y de Diseño

1. **Formato de Fechas:** ISO 8601 estándar extendido (`YYYY-MM-DDTHH:MM` o `YYYY-MM-DDTHH:MM:SS`).
2. **Zona Horaria:** Se asume hora local naive consistente en toda la aplicación. No se aplican conversiones de husos horarios arbitrarios para garantizar predictibilidad en las pruebas locales.
3. **Tratamiento de Fechas Pasadas:** A efectos de pruebas automatizadas reproducibles e independientes del reloj del sistema donde se ejecute la evaluación, se permite agendar reservas con fechas explícitas (pasadas o futuras), siempre y cuando cumplan con el invariante `inicio < fin`.
4. **Límites de Duración y Anticipación:** No se aplican restricciones arbitrarias de duración mínima (salvo `inicio < fin`) ni límite máximo de anticipación, priorizando la generalidad requerida en la consigna.
5. **Persistencia y Aislamiento de Pruebas:** La capa de persistencia permite parametrizar la ruta del archivo de datos (`data_path`). Esto permite que los tests automáticos operen sobre archivos temporales aislados sin modificar los datos reales de la aplicación (`data/reservas.json`).

---

## 7. Criterios de Aceptación Verificables

| Caso de Verificación | Condición de Entrada | Resultado Esperado |
| :--- | :--- | :--- |
| **CA-01: Creación Válida** | `MIC-01`, "Dra. Juana Manso", 10:00 a 11:00 | Reserva creada con ID, estado `ACTIVA` y registrada en persistencia. |
| **CA-02: Rechazo de Solapamiento** | `MIC-01` ocupado de 10:00 a 11:00; intento de 10:30 a 11:30 | Excepción / Rechazo por superposición. La reserva no se crea. |
| **CA-03: Límite Consecutivo Válido** | `MIC-01` ocupado de 10:00 a 11:00; intento de 11:00 a 12:00 | Reserva exitosa permitida. |
| **CA-04: Simultaneidad de Unidades** | `MIC-01` ocupado de 10:00 a 11:00; intento en `MIC-02` de 10:00 a 11:00 | Reserva exitosa en `MIC-02`. |
| **CA-05: Solicitante Inválido** | `solicitante = "   "` o `""` | Error de validación: solicitante no puede estar vacío. |
| **CA-06: Intervalo Inválido** | `inicio = 12:00`, `fin = 11:00` o `inicio == fin` | Error de validación: inicio debe ser estrictamente anterior a fin. |
| **CA-07: Unidad Inexistente** | `id_unidad = "INVENTADO-99"` | Error de validación: unidad no reconocida en catálogo. |
| **CA-08: Cancelación y Liberación** | Cancelar reserva `MIC-01` (10:00-11:00), luego solicitar `MIC-01` (10:00-11:00) | La cancelación conserva datos y pasa a `CANCELADA`. La nueva reserva se crea sin conflicto. |
| **CA-09: Persistencia tras Reinicio** | Cargar datos existentes, reiniciar servicio/proceso | El repositorio contiene exactamente las reservas y estados creados previamente. |
