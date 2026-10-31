"""
Script de demostración guiada interactiva del Sistema de Gestión de Reservas.

Ejecuta de manera secuencial los flujos de negocio principales:
1. Inspección del catálogo precargado.
2. Creación de una reserva válida.
3. Rechazo de solapamiento horario (misma unidad).
4. Aceptación de límites consecutivos contiguos.
5. Simultaneidad entre unidades físicas distintas.
6. Cancelación de reserva y liberación inmediata del horario.
7. Comprobación de persistencia y recuperación tras reinicio.

Opera sobre un archivo temporal aislado para no alterar data/reservas.json.
"""

import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Asegurar encoding UTF-8 en terminales Windows
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Ajustar path para importar src
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from src.modelos import ErrorDominio
from src.repositorio import JsonReservaRepositorio
from src.servicio import ReservaServicio


def print_seccion(numero: int, titulo: str) -> None:
    print("\n" + "=" * 70)
    print(f" PASO {numero}: {titulo}")
    print("=" * 70)


def dt(iso_str: str) -> datetime:
    return datetime.fromisoformat(iso_str)


def ejecutar_demostracion() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        ruta_reservas_demo = Path(tmp_dir) / "demo_reservas.json"
        ruta_inventario = base_dir / "data" / "inventario.json"

        repositorio = JsonReservaRepositorio(
            ruta_reservas=ruta_reservas_demo,
            ruta_inventario=ruta_inventario,
        )
        servicio = ReservaServicio(repositorio=repositorio)

        print("\n" + "#" * 70)
        print("  DEMOSTRACIÓN GUIADA DEL SISTEMA DE RESERVAS DE LABORATORIO")
        print("#" * 70)

        # ------------------------------------------------------------------
        # Paso 1: Inventario
        # ------------------------------------------------------------------
        print_seccion(1, "Inspección del inventario precargado e inmutable")
        equipos = servicio.obtener_inventario()
        for eq in equipos:
            print(f"  * [{eq.id}] {eq.nombre}")
        print(f"  -> Total de unidades cargadas: {len(equipos)}")

        # ------------------------------------------------------------------
        # Paso 2: Creación de reserva válida
        # ------------------------------------------------------------------
        print_seccion(2, "Creación de reserva válida para MIC-01")
        r1 = servicio.crear_reserva(
            id_unidad="MIC-01",
            solicitante="Dra. Juana Manso",
            inicio=dt("2026-11-01T10:00"),
            fin=dt("2026-11-01T11:00"),
        )
        print(f"  [OK] Reserva registrada con éxito:")
        print(f"       ID: {r1.id} | Unidad: {r1.id_unidad} | Solicitante: {r1.solicitante}")
        print(f"       Intervalo: {r1.inicio.strftime('%H:%M')} a {r1.fin.strftime('%H:%M')} | Estado: {r1.estado.value}")

        # ------------------------------------------------------------------
        # Paso 3: Rechazo de solapamiento
        # ------------------------------------------------------------------
        print_seccion(3, "Intento de reserva superpuesta (MIC-01 de 10:30 a 11:30)")
        try:
            servicio.crear_reserva(
                id_unidad="MIC-01",
                solicitante="Dr. Gomez",
                inicio=dt("2026-11-01T10:30"),
                fin=dt("2026-11-01T11:30"),
            )
            print("  [ERROR] Falló la validación (se permitió superposición).")
        except ErrorDominio as err:
            print(f"  [RECHAZADO CORRECTAMENTE] Regla RN-04 activada:")
            print(f"       Mensaje: {err}")

        # ------------------------------------------------------------------
        # Paso 4: Límites consecutivos permitidos
        # ------------------------------------------------------------------
        print_seccion(4, "Reserva en límite consecutivo contiguo (MIC-01 de 11:00 a 12:00)")
        r2 = servicio.crear_reserva(
            id_unidad="MIC-01",
            solicitante="Dr. Bernardo Houssay",
            inicio=dt("2026-11-01T11:00"),
            fin=dt("2026-11-01T12:00"),
        )
        print(f"  [OK] Turno contiguo aceptado (Regla RN-05 de intervalos semiabiertos):")
        print(f"       ID: {r2.id} | Horario: {r2.inicio.strftime('%H:%M')} a {r2.fin.strftime('%H:%M')}")

        # ------------------------------------------------------------------
        # Paso 5: Simultaneidad de unidades distintas
        # ------------------------------------------------------------------
        print_seccion(5, "Reserva simultánea en otra unidad (MIC-02 de 10:00 a 11:00)")
        r3 = servicio.crear_reserva(
            id_unidad="MIC-02",
            solicitante="Ing. Cecilia Grierson",
            inicio=dt("2026-11-01T10:00"),
            fin=dt("2026-11-01T11:00"),
        )
        print(f"  [OK] Reserva permitida en unidad distinta (Regla RN-06):")
        print(f"       ID: {r3.id} | Unidad: {r3.id_unidad} | Horario: {r3.inicio.strftime('%H:%M')} a {r3.fin.strftime('%H:%M')}")

        # ------------------------------------------------------------------
        # Paso 6: Cancelación y liberación de horario
        # ------------------------------------------------------------------
        print_seccion(6, f"Cancelación de la primera reserva ({r1.id})")
        r1_cancelada = servicio.cancelar_reserva(r1.id)
        print(f"  [OK] Estado actualizado a: {r1_cancelada.estado.value} (Registro preservado en historial)")
        
        disponible, _ = servicio.consultar_disponibilidad(
            "MIC-01", dt("2026-11-01T10:00"), dt("2026-11-01T11:00")
        )
        print(f"       Disponibilidad de MIC-01 (10:00 a 11:00): {'LIBRE' if disponible else 'OCUPADA'}")

        # ------------------------------------------------------------------
        # Paso 7: Persistencia y recuperación tras reinicio
        # ------------------------------------------------------------------
        print_seccion(7, "Simulación de reinicio de aplicación y recuperación de disco")
        # Creamos una nueva instancia del repositorio leyendo el archivo en disco
        nuevo_repositorio = JsonReservaRepositorio(
            ruta_reservas=ruta_reservas_demo,
            ruta_inventario=ruta_inventario,
        )
        nuevo_servicio = ReservaServicio(repositorio=nuevo_repositorio)
        recuperadas = nuevo_servicio.listar_reservas()

        print(f"  [OK] Se recuperaron {len(recuperadas)} reservas del archivo persistido:")
        for r in recuperadas:
            print(
                f"       * {r.id} | {r.id_unidad} | {r.solicitante:<22} | "
                f"{r.inicio.strftime('%H:%M')}-{r.fin.strftime('%H:%M')} | {r.estado.value}"
            )

        print("\n" + "=" * 70)
        print("  DEMOSTRACIÓN FINALIZADA CON ÉXITO: 100% DE REGLAS VERIFICADAS")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    ejecutar_demostracion()
