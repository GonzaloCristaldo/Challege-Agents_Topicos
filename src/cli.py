import argparse
import sys
from datetime import datetime

from src.modelos import (
    ErrorDominio,
    EstadoReserva,
)
from src.repositorio import JsonReservaRepositorio
from src.servicio import ReservaServicio


def parse_datetime(dt_str: str) -> datetime:
    """Parsea una cadena ISO 8601 a datetime."""
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Formato de fecha/hora inválido: '{dt_str}'. Use ISO 8601 (ej. 2026-11-01T10:00)."
        )


def comando_inventario(servicio: ReservaServicio, args: argparse.Namespace) -> int:
    """Muestra el catálogo de unidades físicas precargadas."""
    equipos = servicio.obtener_inventario()
    print("\n--- INVENTARIO DE EQUIPOS DE LABORATORIO ---")
    print(f"{'ID':<10} | {'DESCRIPCIÓN'}")
    print("-" * 45)
    for eq in equipos:
        print(f"{eq.id:<10} | {eq.nombre}")
    print(f"\nTotal: {len(equipos)} unidades precargadas.\n")
    return 0


def comando_disponibilidad(servicio: ReservaServicio, args: argparse.Namespace) -> int:
    """Consulta la disponibilidad de una unidad en un intervalo."""
    try:
        disponible, conflicto = servicio.consultar_disponibilidad(
            id_unidad=args.id_unidad,
            inicio=args.inicio,
            fin=args.fin,
        )
        if disponible:
            print(
                f"\n[DISPONIBLE] La unidad '{args.id_unidad}' está LIBRE "
                f"entre {args.inicio.isoformat()} y {args.fin.isoformat()}.\n"
            )
            return 0
        else:
            print(
                f"\n[NO DISPONIBLE] La unidad '{args.id_unidad}' está OCUPADA "
                f"por la reserva '{conflicto.id}' ({conflicto.solicitante}) "
                f"entre {conflicto.inicio.isoformat()} y {conflicto.fin.isoformat()}.\n"
            )
            return 1
    except ErrorDominio as e:
        print(f"\n[ERROR DE NEGOCIO] {e}\n", file=sys.stderr)
        return 2


def comando_reservar(servicio: ReservaServicio, args: argparse.Namespace) -> int:
    """Crea una nueva reserva."""
    try:
        reserva = servicio.crear_reserva(
            id_unidad=args.id_unidad,
            solicitante=args.solicitante,
            inicio=args.inicio,
            fin=args.fin,
        )
        print("\n=== RESERVA CONFIRMADA EXITOSAMENTE ===")
        print(f"ID Reserva  : {reserva.id}")
        print(f"Unidad      : {reserva.id_unidad}")
        print(f"Solicitante : {reserva.solicitante}")
        print(f"Inicio      : {reserva.inicio.isoformat()}")
        print(f"Fin         : {reserva.fin.isoformat()}")
        print(f"Estado      : {reserva.estado.value}\n")
        return 0
    except ErrorDominio as e:
        print(f"\n[ERROR DE RESERVA] {e}\n", file=sys.stderr)
        return 2


def comando_cancelar(servicio: ReservaServicio, args: argparse.Namespace) -> int:
    """Cancela una reserva existente."""
    try:
        reserva = servicio.cancelar_reserva(id_reserva=args.id_reserva)
        print("\n=== RESERVA CANCELADA ===")
        print(f"ID Reserva  : {reserva.id}")
        print(f"Unidad      : {reserva.id_unidad}")
        print(f"Solicitante : {reserva.solicitante}")
        print(f"Horario     : {reserva.inicio.isoformat()} a {reserva.fin.isoformat()}")
        print(f"Nuevo Estado: {reserva.estado.value} (Horario liberado)\n")
        return 0
    except ErrorDominio as e:
        print(f"\n[ERROR AL CANCELAR] {e}\n", file=sys.stderr)
        return 2


def comando_listar(servicio: ReservaServicio, args: argparse.Namespace) -> int:
    """Lista las reservas registradas."""
    reservas = servicio.listar_reservas(id_unidad=args.id_unidad)
    if not reservas:
        print("\nNo hay reservas registradas en el sistema.\n")
        return 0

    print("\n--- HISTORIAL DE RESERVAS ---")
    header = f"{'ID':<14} | {'UNIDAD':<8} | {'SOLICITANTE':<20} | {'INICIO':<16} | {'FIN':<16} | {'ESTADO'}"
    print(header)
    print("-" * len(header))
    for r in reservas:
        print(
            f"{r.id:<14} | {r.id_unidad:<8} | {r.solicitante[:20]:<20} | "
            f"{r.inicio.strftime('%Y-%m-%d %H:%M'):<16} | {r.fin.strftime('%Y-%m-%d %H:%M'):<16} | {r.estado.value}"
        )
    print(f"\nTotal: {len(reservas)} reservas registradas.\n")
    return 0


def crear_parser() -> argparse.ArgumentParser:
    """Construye y configura el parser de argumentos de la CLI."""
    parser = argparse.ArgumentParser(
        prog="sistema_reservas",
        description="Sistema de Gestión de Reservas de Instrumental de Laboratorio.",
    )
    subparsers = parser.add_subparsers(dest="subcomando", help="Operación a realizar")

    # Subcomando: inventario
    subparsers.add_parser("inventario", help="Listar unidades del inventario")

    # Subcomando: disponibilidad
    p_disp = subparsers.add_parser("disponibilidad", help="Consultar disponibilidad horaria")
    p_disp.add_argument("id_unidad", help="Identificador de la unidad (ej. MIC-01)")
    p_disp.add_argument("inicio", type=parse_datetime, help="Inicio ISO (YYYY-MM-DDTHH:MM)")
    p_disp.add_argument("fin", type=parse_datetime, help="Fin ISO (YYYY-MM-DDTHH:MM)")

    # Subcomando: reservar
    p_res = subparsers.add_parser("reservar", help="Registrar una nueva reserva")
    p_res.add_argument("id_unidad", help="Identificador de la unidad (ej. MIC-01)")
    p_res.add_argument("solicitante", help="Nombre o entidad solicitante")
    p_res.add_argument("inicio", type=parse_datetime, help="Inicio ISO (YYYY-MM-DDTHH:MM)")
    p_res.add_argument("fin", type=parse_datetime, help="Fin ISO (YYYY-MM-DDTHH:MM)")

    # Subcomando: cancelar
    p_canc = subparsers.add_parser("cancelar", help="Cancelar una reserva activa")
    p_canc.add_argument("id_reserva", help="Identificador de la reserva (ej. RES-A1B2C3D4)")

    # Subcomando: listar
    p_list = subparsers.add_parser("listar", help="Listar reservas e historial")
    p_list.add_argument("--id-unidad", help="Filtrar por unidad (opcional)", default=None)

    return parser


def main(argv=None) -> int:
    """Punto de entrada principal de la CLI."""
    if sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    parser = crear_parser()
    args = parser.parse_args(argv)

    if not args.subcomando:
        parser.print_help()
        return 0

    repositorio = JsonReservaRepositorio()
    servicio = ReservaServicio(repositorio=repositorio)

    comandos = {
        "inventario": comando_inventario,
        "disponibilidad": comando_disponibilidad,
        "reservar": comando_reservar,
        "cancelar": comando_cancelar,
        "listar": comando_listar,
    }

    return comandos[args.subcomando](servicio, args)


if __name__ == "__main__":
    sys.exit(main())
