from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class EstadoReserva(str, Enum):
    """Estados posibles de una reserva."""
    ACTIVA = "ACTIVA"
    CANCELADA = "CANCELADA"


@dataclass(frozen=True)
class Equipo:
    """Representa una unidad física del inventario del laboratorio."""
    id: str
    nombre: str


@dataclass
class Reserva:
    """Representa una reserva de una unidad de equipo en un intervalo temporal."""
    id: str
    id_unidad: str
    solicitante: str
    inicio: datetime
    fin: datetime
    estado: EstadoReserva = EstadoReserva.ACTIVA

    def to_dict(self) -> dict:
        """Serializa la entidad a un diccionario para persistencia en JSON."""
        return {
            "id": self.id,
            "id_unidad": self.id_unidad,
            "solicitante": self.solicitante,
            "inicio": self.inicio.isoformat(),
            "fin": self.fin.isoformat(),
            "estado": self.estado.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Reserva":
        """Reconstruye una instancia de Reserva a partir de un diccionario."""
        return cls(
            id=data["id"],
            id_unidad=data["id_unidad"],
            solicitante=data["solicitante"],
            inicio=datetime.fromisoformat(data["inicio"]),
            fin=datetime.fromisoformat(data["fin"]),
            estado=EstadoReserva(data.get("estado", EstadoReserva.ACTIVA.value)),
        )


def hay_superposicion(
    inicio1: datetime, fin1: datetime, inicio2: datetime, fin2: datetime
) -> bool:
    """
    Determina si dos intervalos temporales semiabiertos [inicio, fin) se solapan.
    
    Regla: Dos intervalos [I1, F1) e [I2, F2) se intersectan si y solo si:
           max(I1, I2) < min(F1, F2)
    
    Límites consecutivos: Si F1 == I2 o F2 == I1, la desigualdad estricta es falsa,
    garantizando que turnos consecutivos contiguos NO se consideren superpuestos.
    """
    return max(inicio1, inicio2) < min(fin1, fin2)


# ==============================================================================
# Excepciones de Dominio
# ==============================================================================

class ErrorDominio(Exception):
    """Excepción base para errores de reglas de negocio."""
    pass


class UnidadNoEncontradaError(ErrorDominio):
    """Arrojada cuando se consulta o reserva una unidad que no existe en el catálogo."""
    def __init__(self, id_unidad: str):
        super().__init__(f"La unidad '{id_unidad}' no existe en el inventario.")
        self.id_unidad = id_unidad


class SolicitanteInvalidoError(ErrorDominio):
    """Arrojada cuando el solicitante está vacío o compuesto solo por espacios."""
    def __init__(self):
        super().__init__("El nombre del solicitante no puede estar vacío ni contener solo espacios.")


class IntervaloInvalidoError(ErrorDominio):
    """Arrojada cuando las fechas son inválidas o inicio >= fin."""
    def __init__(self, mensaje: str = "La fecha y hora de inicio debe ser estrictamente anterior al fin."):
        super().__init__(mensaje)


class SuperposicionHorariaError(ErrorDominio):
    """Arrojada cuando existe un conflicto de horario con una reserva activa previa."""
    def __init__(self, id_unidad: str, id_conflicto: str, inicio: datetime, fin: datetime):
        super().__init__(
            f"La unidad '{id_unidad}' ya cuenta con una reserva activa ({id_conflicto}) "
            f"en el intervalo {inicio.isoformat()} a {fin.isoformat()}."
        )
        self.id_unidad = id_unidad
        self.id_conflicto = id_conflicto
        self.inicio = inicio
        self.fin = fin


class ReservaNoEncontradaError(ErrorDominio):
    """Arrojada cuando se intenta operar sobre una reserva inexistente."""
    def __init__(self, id_reserva: str):
        super().__init__(f"No se encontró ninguna reserva con el identificador '{id_reserva}'.")
        self.id_reserva = id_reserva


class ReservaYaCanceladaError(ErrorDominio):
    """Arrojada cuando se intenta cancelar una reserva que ya se encuentra cancelada."""
    def __init__(self, id_reserva: str):
        super().__init__(f"La reserva '{id_reserva}' ya se encuentra cancelada.")
        self.id_reserva = id_reserva
