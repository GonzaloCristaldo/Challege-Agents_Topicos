from datetime import datetime
import pytest

from src.modelos import (
    EstadoReserva,
    IntervaloInvalidoError,
    ReservaYaCanceladaError,
    SolicitanteInvalidoError,
    SuperposicionHorariaError,
    UnidadNoEncontradaError,
)
from src.repositorio import JsonReservaRepositorio
from src.servicio import ReservaServicio


def dt(hora_str: str) -> datetime:
    """Helper para crear datetimes a partir de 'YYYY-MM-DDTHH:MM'."""
    return datetime.fromisoformat(hora_str)


# ==============================================================================
# 1. Creación Válida de Reservas
# ==============================================================================

def test_creacion_reserva_valida(servicio: ReservaServicio):
    """Verifica la creación exitosa de una reserva con todos los campos válidos."""
    reserva = servicio.crear_reserva(
        id_unidad="MIC-01",
        solicitante="Dra. Juana Manso",
        inicio=dt("2026-11-01T10:00"),
        fin=dt("2026-11-01T11:00"),
    )

    assert reserva.id.startswith("RES-")
    assert reserva.id_unidad == "MIC-01"
    assert reserva.solicitante == "Dra. Juana Manso"
    assert reserva.inicio == dt("2026-11-01T10:00")
    assert reserva.fin == dt("2026-11-01T11:00")
    assert reserva.estado == EstadoReserva.ACTIVA

    # Comprueba que figure en el listado del repositorio
    todas = servicio.listar_reservas()
    assert len(todas) == 1
    assert todas[0].id == reserva.id


# ==============================================================================
# 2. Rechazo de Superposiciones (Misma Unidad)
# ==============================================================================

@pytest.mark.parametrize(
    "inicio_solapado, fin_solapado",
    [
        ("2026-11-01T10:30", "2026-11-01T11:30"),  # Solapamiento parcial posterior
        ("2026-11-01T09:30", "2026-11-01T10:30"),  # Solapamiento parcial anterior
        ("2026-11-01T10:15", "2026-11-01T10:45"),  # Contenido completamente dentro
        ("2026-11-01T09:00", "2026-11-01T12:00"),  # Envuelve completamente
        ("2026-11-01T10:00", "2026-11-01T11:00"),  # Solapamiento idéntico exacto
    ],
)
def test_rechazo_superposicion_misma_unidad(
    servicio: ReservaServicio, inicio_solapado: str, fin_solapado: str
):
    """Rechaza intentos de superposición con una reserva activa previa en la misma unidad."""
    servicio.crear_reserva(
        id_unidad="MIC-01",
        solicitante="Investigador A",
        inicio=dt("2026-11-01T10:00"),
        fin=dt("2026-11-01T11:00"),
    )

    # Debe arrojar SuperposicionHorariaError
    with pytest.raises(SuperposicionHorariaError) as exc_info:
        servicio.crear_reserva(
            id_unidad="MIC-01",
            solicitante="Investigador B",
            inicio=dt(inicio_solapado),
            fin=dt(fin_solapado),
        )

    assert "MIC-01" in str(exc_info.value)

    # También la consulta de disponibilidad debe reflejarlo
    disponible, conflicto = servicio.consultar_disponibilidad(
        id_unidad="MIC-01",
        inicio=dt(inicio_solapado),
        fin=dt(fin_solapado),
    )
    assert disponible is False
    assert conflicto is not None


# ==============================================================================
# 3. Límites Consecutivos Permitidos
# ==============================================================================

def test_limites_consecutivos_permitidos(servicio: ReservaServicio):
    """
    Verifica que dos reservas contiguas (donde fin1 == inicio2 o fin2 == inicio1)
    se acepten sin considerarse superposición.
    Ejemplo de consigna: MIC-01 de 10:00 a 11:00 permite 11:00 a 12:00.
    """
    r1 = servicio.crear_reserva(
        id_unidad="MIC-01",
        solicitante="Turno Mañana",
        inicio=dt("2026-11-01T10:00"),
        fin=dt("2026-11-01T11:00"),
    )
    r2 = servicio.crear_reserva(
        id_unidad="MIC-01",
        solicitante="Turno Siguiente",
        inicio=dt("2026-11-01T11:00"),
        fin=dt("2026-11-01T12:00"),
    )
    r3 = servicio.crear_reserva(
        id_unidad="MIC-01",
        solicitante="Turno Previo",
        inicio=dt("2026-11-01T09:00"),
        fin=dt("2026-11-01T10:00"),
    )

    assert r1.id != r2.id != r3.id
    reservas_mic = servicio.listar_reservas(id_unidad="MIC-01")
    assert len(reservas_mic) == 3


# ==============================================================================
# 4. Simultaneidad entre Unidades Distintas Permitida
# ==============================================================================

def test_simultaneidad_unidades_distintas(servicio: ReservaServicio):
    """
    Verifica que dos unidades distintas puedan reservarse exactamente en el mismo horario.
    Ejemplo de consigna: MIC-02 puede reservarse de 10:00 a 11:00 aunque MIC-01 esté ocupado.
    """
    r1 = servicio.crear_reserva(
        id_unidad="MIC-01",
        solicitante="Laboratorio Bioquímica",
        inicio=dt("2026-11-01T10:00"),
        fin=dt("2026-11-01T11:00"),
    )
    r2 = servicio.crear_reserva(
        id_unidad="MIC-02",
        solicitante="Laboratorio Genética",
        inicio=dt("2026-11-01T10:00"),
        fin=dt("2026-11-01T11:00"),
    )
    r3 = servicio.crear_reserva(
        id_unidad="OSC-01",
        solicitante="Laboratorio Física",
        inicio=dt("2026-11-01T10:00"),
        fin=dt("2026-11-01T11:00"),
    )

    assert r1.estado == EstadoReserva.ACTIVA
    assert r2.estado == EstadoReserva.ACTIVA
    assert r3.estado == EstadoReserva.ACTIVA


# ==============================================================================
# 5. Validación de Entradas Inválidas
# ==============================================================================

@pytest.mark.parametrize("solicitante_invalido", ["", "   ", "\t\n  "])
def test_solicitante_vacio_rechazado(servicio: ReservaServicio, solicitante_invalido: str):
    """Rechaza solicitantes vacíos o con solo espacios en blanco."""
    with pytest.raises(SolicitanteInvalidoError):
        servicio.crear_reserva(
            id_unidad="MIC-01",
            solicitante=solicitante_invalido,
            inicio=dt("2026-11-01T10:00"),
            fin=dt("2026-11-01T11:00"),
        )


def test_inicio_mayor_o_igual_a_fin_rechazado(servicio: ReservaServicio):
    """Rechaza reservas donde inicio >= fin."""
    # Mismo instante
    with pytest.raises(IntervaloInvalidoError):
        servicio.crear_reserva(
            id_unidad="MIC-01",
            solicitante="Investigador C",
            inicio=dt("2026-11-01T10:00"),
            fin=dt("2026-11-01T10:00"),
        )

    # Fin anterior a inicio
    with pytest.raises(IntervaloInvalidoError):
        servicio.crear_reserva(
            id_unidad="MIC-01",
            solicitante="Investigador C",
            inicio=dt("2026-11-01T11:00"),
            fin=dt("2026-11-01T10:00"),
        )


def test_unidad_inexistente_rechazada(servicio: ReservaServicio):
    """Rechaza reservas y consultas para IDs de equipos no presentes en el catálogo."""
    with pytest.raises(UnidadNoEncontradaError):
        servicio.crear_reserva(
            id_unidad="EQUIPO-FANTASMA-99",
            solicitante="Investigador D",
            inicio=dt("2026-11-01T10:00"),
            fin=dt("2026-11-01T11:00"),
        )

    with pytest.raises(UnidadNoEncontradaError):
        servicio.consultar_disponibilidad(
            id_unidad="EQUIPO-FANTASMA-99",
            inicio=dt("2026-11-01T10:00"),
            fin=dt("2026-11-01T11:00"),
        )


# ==============================================================================
# 6. Cancelación que Conserva Historial y Libera Horario
# ==============================================================================

def test_cancelacion_conserva_historial_y_libera_horario(servicio: ReservaServicio):
    """
    Verifica que:
    1. Una reserva cancelada conserve su identificador, solicitante y datos.
    2. Su estado cambie a CANCELADA.
    3. El intervalo quede disponible y permita una nueva reserva en el mismo horario.
    """
    reserva_original = servicio.crear_reserva(
        id_unidad="MUL-01",
        solicitante="Ing. Tesla",
        inicio=dt("2026-11-01T14:00"),
        fin=dt("2026-11-01T16:00"),
    )
    id_reserva = reserva_original.id

    # Cancelamos la reserva
    cancelada = servicio.cancelar_reserva(id_reserva)
    assert cancelada.id == id_reserva
    assert cancelada.solicitante == "Ing. Tesla"
    assert cancelada.estado == EstadoReserva.CANCELADA

    # Intentar cancelarla nuevamente arroja error
    with pytest.raises(ReservaYaCanceladaError):
        servicio.cancelar_reserva(id_reserva)

    # Ahora el intervalo debe figurar libre
    disponible, _ = servicio.consultar_disponibilidad(
        id_unidad="MUL-01",
        inicio=dt("2026-11-01T14:00"),
        fin=dt("2026-11-01T16:00"),
    )
    assert disponible is True

    # Se puede crear una nueva reserva en el mismo horario liberado
    nueva = servicio.crear_reserva(
        id_unidad="MUL-01",
        solicitante="Dr. Ohm",
        inicio=dt("2026-11-01T14:00"),
        fin=dt("2026-11-01T16:00"),
    )
    assert nueva.id != id_reserva
    assert nueva.estado == EstadoReserva.ACTIVA

    # El historial contiene ambas (la cancelada y la nueva)
    todas = servicio.listar_reservas(id_unidad="MUL-01")
    assert len(todas) == 2
    estados = {r.id: r.estado for r in todas}
    assert estados[id_reserva] == EstadoReserva.CANCELADA
    assert estados[nueva.id] == EstadoReserva.ACTIVA


# ==============================================================================
# 7. Persistencia tras Detener y Reiniciar la Aplicación
# ==============================================================================

def test_persistencia_recupera_estado_tras_reinicio(repo_aislado: JsonReservaRepositorio):
    """
    Comprueba que al instanciar un nuevo servicio y repositorio sobre las mismas
    rutas de archivo (simulando reiniciar la aplicación), se conservan todas las
    reservas activas y canceladas con sus datos intactos.
    """
    servicio_instancia_1 = ReservaServicio(repositorio=repo_aislado)

    # 1. Crear una reserva activa
    r1 = servicio_instancia_1.crear_reserva(
        id_unidad="FUE-01",
        solicitante="Dra. Curie",
        inicio=dt("2026-11-02T08:00"),
        fin=dt("2026-11-02T10:00"),
    )

    # 2. Crear una segunda reserva y cancelarla
    r2 = servicio_instancia_1.crear_reserva(
        id_unidad="FUE-01",
        solicitante="Dr. Becquerel",
        inicio=dt("2026-11-02T10:00"),
        fin=dt("2026-11-02T12:00"),
    )
    servicio_instancia_1.cancelar_reserva(r2.id)

    # Simulamos el reinicio de la aplicación instanciando un nuevo repositorio
    # que lee el archivo persistido en disco
    repo_reinicio = JsonReservaRepositorio(
        ruta_reservas=repo_aislado.ruta_reservas,
        ruta_inventario=repo_aislado.ruta_inventario,
    )
    servicio_instancia_2 = ReservaServicio(repositorio=repo_reinicio)

    reservas_recuperadas = servicio_instancia_2.listar_reservas()
    assert len(reservas_recuperadas) == 2

    res1_recuperada = servicio_instancia_2.repositorio.obtener_reserva(r1.id)
    assert res1_recuperada is not None
    assert res1_recuperada.solicitante == "Dra. Curie"
    assert res1_recuperada.estado == EstadoReserva.ACTIVA

    res2_recuperada = servicio_instancia_2.repositorio.obtener_reserva(r2.id)
    assert res2_recuperada is not None
    assert res2_recuperada.solicitante == "Dr. Becquerel"
    assert res2_recuperada.estado == EstadoReserva.CANCELADA

    # La regla de disponibilidad en la nueva instancia reconoce a r1 ocupada y r2 liberada
    disp_r1, _ = servicio_instancia_2.consultar_disponibilidad(
        "FUE-01", dt("2026-11-02T08:30"), dt("2026-11-02T09:30")
    )
    assert disp_r1 is False

    disp_r2, _ = servicio_instancia_2.consultar_disponibilidad(
        "FUE-01", dt("2026-11-02T10:00"), dt("2026-11-02T12:00")
    )
    assert disp_r2 is True
