# Preparación del Agente y Entorno de Desarrollo

Este documento detalla la configuración del entorno, el modelo utilizado, las instrucciones suministradas, las herramientas habilitadas y las adaptaciones comprobables aplicadas durante el desarrollo del sistema de reservas, en cumplimiento de los requisitos de la consigna.

---

## 1. Entorno, Modelo y Harness

* **Harness / Entorno:** Google Antigravity IDE (Advanced Agentic Coding Environment). Provee el entorno de ejecución, gestión de contexto, orquestación de herramientas (*tool-calling*) y terminal interactiva PowerShell sobre Windows.
* **Identificador del Modelo:** Gemini 3.8 Flash (`gemini-3.8-flash-high`) de Google DeepMind.
* **Función del Modelo:** Agente de programación en modalidad *pair programming* encargado de:
  1. Analizar la consigna y estructurar la especificación formal del problema.
  2. Diseñar la arquitectura limpia modular (Dominio, Repositorio, Servicio, CLI).
  3. Escribir código fuente Python 3.14 verificable y tipado.
  4. Diseñar e implementar la suite de pruebas automatizadas con `pytest`.
  5. Ejecutar comandos de verificación y versionar los cambios mediante Git.
* **Motivo de la Elección:**
  - Balance óptimo entre velocidad de inferencia (*low latency*) y capacidades avanzadas de razonamiento lógico.
  - Soporte robusto y nativo de llamadas a herramientas (*tool-calling*) para inspección de archivos, edición segura y ejecución en terminal PowerShell.
  - Alta precisión en la generación de pruebas unitarias que cubren casos de borde sin alucinaciones de API.

---

## 2. Instrucciones y Configuraciones Suministradas

### 2.1. Contexto Suministrado
* Texto completo de la consigna (`challenge-agents.pdf`): inventario fijo de 5 equipos, problemática del laboratorio, reglas de negocio e invariantes temporales.
* Rúbrica de evaluación: énfasis en la documentación del proceso con el agente, trazabilidad de decisiones y registro de 3 episodios reales de delegación.
* Lineamientos de arquitectura: uso de Python estándar, persistencia local en JSON sin bases de datos externas pesadas y enfoque de diseño guiado por pruebas (*Test-Driven Development*).

### 2.2. Contexto Excluido (Saneamiento)
* No se suministraron credenciales, tokens de API ni variables de entorno sensibles.
* Se excluyeron intencionalmente bibliotecas o componentes ajenos a la consigna (frameworks de autenticación, microservicios, bases de datos remotas, librerías de UI complejas o servicios de pago).
* Se restringió el alcance a una aplicación local autónoma, reproducible en cualquier máquina sin necesidad de cuentas de modelo externas.

### 2.3. Directivas de Calidad Operativa
* **Tipado estricto:** Uso de `dataclasses`, `datetime` y type hints de Python.
* **Manejo explícito de excepciones:** Creación de excepciones de dominio específicas (`UnidadNoEncontradaError`, `SuperposicionHorariaError`, `IntervaloInvalidoError`, `SolicitanteInvalidoError`, `ReservaYaCanceladaError`).
* **Inmutabilidad y persistencia atómica:** Las lecturas y escrituras en disco deben mantener la integridad de los datos ante cierres inesperados.

---

## 3. Herramientas y Acciones Permitidas

| Herramienta | Acción Permitida | Control y Supervisión Humana |
| :--- | :--- | :--- |
| `read_file` | Lectura de especificaciones, código y archivos de datos. | Verificación de que el agente analice la documentación oficial sin inventar requisitos. |
| `write_file` / `edit_file` | Creación y actualización de código fuente, tests y documentación. | El usuario humano revisa la estructura propuesta y los diffs antes de proceder con la ejecución. |
| `run_command` | Ejecución en terminal PowerShell (`python`, `pytest`, `git`). | Ejecución controlada de pruebas locales y comandos de Git; el humano revisa el log de salida real. |

**Criterios de Aprobación Humana:**
* Ningún cambio de arquitectura se da por definitivo sin la previa aprobación del usuario.
* Cada suite de pruebas debe ejecutarse en la terminal y reportar resultados verificables (0 fallas) antes de realizar el commit correspondiente.

---

## 4. Adaptaciones Específicas Comprobables

Durante la preparación del agente se definieron dos adaptaciones comprobables para evitar errores comunes de modelado:

### Adaptación 1: Tratamiento de Límites Consecutivos (Intervalos Semiabiertos)
* **Problema:** En muchos algoritmos de calendario tradicionales se emplean comparaciones inclusivas $\le$ o $\ge$, lo cual ocasiona que dos turnos contiguos (ej. 10:00 a 11:00 y 11:00 a 12:00) sean catalogados falsamente como superpuestos.
* **Instrucción de Adaptación:** Se indicó al agente modelar las reservas como intervalos matemáticos semiabiertos a derecha: $[inicio, fin)$.
  $$\text{Existe colisión} \iff \max(inicio_1, inicio_2) < \min(fin_1, fin_2)$$
  Si una reserva finaliza a las 11:00 y la siguiente inicia a las 11:00, $\max(10, 11) = 11$ y $\min(11, 12) = 11$. Dado que $11 < 11$ es **falso**, el algoritmo concluye correctamente que **no hay superposición**.
* **Evidencia de Uso:** Verificable en la función de detección de colisiones de `src/servicio.py` y en la prueba unitaria `test_limites_consecutivos_permitidos` en `tests/test_reservas.py`.

### Adaptación 2: Inyección de Dependencias para Persistencia Aislada en Tests
* **Problema:** Si el repositorio persiste rígidamente en `data/reservas.json`, las pruebas automáticas alterarían los datos reales de la aplicación o requerirían reinicializaciones destructivas continuas.
* **Instrucción de Adaptación:** Se instruyó al agente a desacoplar el origen de persistencia mediante un parámetro configurable `ruta_archivo: Path` en el constructor del repositorio (`JsonReservaRepositorio`).
* **Evidencia de Uso:** En `tests/conftest.py` y los tests unitarios, cada ejecución utiliza fixtures con `tmp_path` de `pytest`, garantizando aislamiento absoluto, pruebas concurrentemente seguras y 100% reproducibles sin afectar los datos productivos.
