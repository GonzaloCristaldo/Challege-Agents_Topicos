import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from src.modelos import (
    Equipo,
    EstadoReserva,
    IntervaloInvalidoError,
    Reserva,
    ReservaNoEncontradaError,
    ReservaYaCanceladaError,
    SolicitanteInvalidoError,
    SuperposicionHorariaError,
    UnidadNoEncontradaError,
    hay_superposicion,
)
from src.repositorio import JsonReservaRepositorio


class ReservaServicio:
    """
    Servicio de aplicación que orquesta las reglas de negocio e invariantes
    del sistema de reservas de instrumental de laboratorio.
    """

    def __init__(self, repositorio: JsonReservaRepositorio):
        self.repositorio = repositorio

    def obtener_inventario(self) -> List[Equipo]:
        """Retorna el catálogo completo de equipos precargados."""
        return self.repositorio.obtener_inventario()

    def _validar_unidad_conocida(self, id_unidad: str) -> Equipo:
        """Verifica que el ID de unidad exista en el inventario precargado."""
        equipo = self.repositorio.obtener_equipo(id_unidad)
        if not equipo:
            raise UnidadNoEncontradaError(id_unidad)
        return equipo

    def _validar_intervalo(self, inicio: datetime, fin: datetime) -> None:
        """Verifica que las fechas sean coherentes y que inicio < fin."""
        if inicio >= fin:
            raise IntervaloInvalidoError(
                f"La fecha de inicio ({inicio.isoformat()}) debe ser estrictamente anterior "
                f"a la fecha de fin ({fin.isoformat()})."
            )

    def _validar_solicitante(self, solicitante: str) -> str:
        """Verifica que el solicitante no sea nulo ni compuesto solo de espacios."""
        if not solicitante or not solicitante.strip():
            raise SolicitanteInvalidoError()
        return solicitante.strip()

    def consultar_disponibilidad(
        self, id_unidad: str, inicio: datetime, fin: datetime
    ) -> Tuple[bool, Optional[Reserva]]:
        """
        Consulta si una unidad física está disponible en un intervalo [inicio, fin).
        
        Retorna:
            (True, None) si el horario está disponible.
            (False, reserva_en_conflicto) si existe colisión con una reserva ACTIVA.
        """
        self._validar_unidad_conocida(id_unidad)
        self._validar_intervalo(inicio, fin)

        # Solo las reservas ACTIVAS de la misma unidad bloquean disponibilidad
        reservas_activas = [
            r
            for r in self.repositorio.listar_reservas(id_unidad=id_unidad)
            if r.estado == EstadoReserva.ACTIVA
        ]

        for r in reservas_activas:
            if hay_superposicion(inicio, fin, r.inicio, r.fin):
                return False, r

        return True, None

    def crear_reserva(
        self, id_unidad: str, solicitante: str, inicio: datetime, fin: datetime
    ) -> Reserva:
        """
        Registra una nueva reserva validando unidad, solicitante y no superposición.
        """
        self._validar_unidad_conocida(id_unidad)
        solicitante_saneado = self._validar_solicitante(solicitante)
        self._validar_intervalo(inicio, fin)

        disponible, conflicto = self.consultar_disponibilidad(id_unidad, inicio, fin)
        if not disponible and conflicto:
            raise SuperposicionHorariaError(
                id_unidad=id_unidad,
                id_conflicto=conflicto.id,
                inicio=conflicto.inicio,
                fin=conflicto.fin,
            )

        # Generación de identificador único de reserva
        reserva_id = f"RES-{uuid.uuid4().hex[:8].upper()}"
        nueva_reserva = Reserva(
            id=reserva_id,
            id_unidad=id_unidad,
            solicitante=solicitante_saneado,
            inicio=inicio,
            fin=fin,
            estado=EstadoReserva.ACTIVA,
        )

        self.repositorio.guardar_reserva(nueva_reserva)
        return nueva_reserva

    def cancelar_reserva(self, id_reserva: str) -> Reserva:
        """
        Cancela una reserva activa liberando el intervalo sin borrar el registro.
        """
        reserva = self.repositorio.obtener_reserva(id_reserva)
        if not reserva:
            raise ReservaNoEncontradaError(id_reserva)

        if reserva.estado == EstadoReserva.CANCELADA:
            raise ReservaYaCanceladaError(id_reserva)

        reserva.estado = EstadoReserva.CANCELADA
        self.repositorio.guardar_reserva(reserva)
        return reserva

    def listar_reservas(self, id_unidad: Optional[str] = None) -> List[Reserva]:
        """Lista el historial de reservas registradas (activas y canceladas)."""
        return self.repositorio.listar_reservas(id_unidad=id_unidad)
