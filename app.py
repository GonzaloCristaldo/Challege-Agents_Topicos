"""
Interfaz gráfica interactiva para el Sistema de Gestión de Reservas de Laboratorio
desarrollada con Streamlit.
"""

from datetime import datetime, time
from pathlib import Path
import streamlit as st

from src.modelos import ErrorDominio, EstadoReserva
from src.repositorio import JsonReservaRepositorio
from src.servicio import ReservaServicio

# Configuración inicial de la página y menú de los 3 puntos verticales (Ayuda / About)
st.set_page_config(
    page_title="Sistema de Reservas - Laboratorio",
    layout="wide",
    menu_items={
        "About": """
        ### Sistema de Gestión de Reservas de Laboratorio

        **Condiciones y Criterios Operativos:**
        * **Límites consecutivos:** Si una reserva finaliza a las 11:00, otra puede comenzar exactamente a las 11:00.
        * **Simultaneidad entre equipos:** Dos unidades distintas pueden estar reservadas en el mismo horario sin conflicto.
        * **Cancelaciones:** Una reserva cancelada libera inmediatamente su intervalo y conserva su trazabilidad histórica.
        * **Consistencia temporal:** El horario de inicio debe ser estrictamente anterior al horario de fin.
        """
    },
)


@st.cache_resource
def get_servicio() -> ReservaServicio:
    """Instancia y mantiene en caché el servicio de aplicación."""
    repo = JsonReservaRepositorio()
    return ReservaServicio(repositorio=repo)


def main():
    servicio = get_servicio()

    # Encabezado sobrio y profesional
    st.title("Sistema de Gestión de Reservas")
    st.caption("Coordinación y administración de instrumental de laboratorio")

    # Métricas superiores
    equipos = servicio.obtener_inventario()
    todas_reservas = servicio.listar_reservas()
    activas = [r for r in todas_reservas if r.estado == EstadoReserva.ACTIVA]
    canceladas = [r for r in todas_reservas if r.estado == EstadoReserva.CANCELADA]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Equipos en Inventario", len(equipos))
    col2.metric("Reservas Totales", len(todas_reservas))
    col3.metric("Reservas Activas", len(activas))
    col4.metric("Canceladas (Historial)", len(canceladas))

    st.divider()

    # Pestañas principales de navegación sin emojis
    tab_reservar, tab_cancelar, tab_historial, tab_inventario = st.tabs(
        [
            "Consultar y Reservar",
            "Cancelar Reserva",
            "Historial Completo",
            "Catálogo de Equipos",
        ]
    )

    # =========================================================================
    # TAB 1: CONSULTAR Y RESERVAR
    # =========================================================================
    with tab_reservar:
        st.subheader("Nueva Solicitud de Reserva")

        # Formulario limpio de ancho cómodo
        col_form, _ = st.columns([3, 1])
        with col_form:
            opciones_equipos = {
                f"{eq.id} - {eq.nombre}": eq.id for eq in equipos
            }
            seleccion_eq_label = st.selectbox(
                "Seleccionar Unidad Física:", list(opciones_equipos.keys())
            )
            id_unidad = opciones_equipos[seleccion_eq_label]

            solicitante = st.text_input(
                "Nombre o Equipo Solicitante (ficticio):",
                placeholder="Ej. Juan Perez",
            )

            col_fecha, col_h_ini, col_h_fin = st.columns(3)
            with col_fecha:
                fecha = st.date_input(
                    "Fecha del turno:", value=datetime.now().date()
                )
            with col_h_ini:
                hora_inicio = st.time_input("Hora Inicio:", value=time(10, 0))
            with col_h_fin:
                hora_fin = st.time_input("Hora Fin:", value=time(11, 0))

            dt_inicio = datetime.combine(fecha, hora_inicio)
            dt_fin = datetime.combine(fecha, hora_fin)

            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                btn_consultar = st.button("Consultar Disponibilidad", use_container_width=True)
            with col_btn2:
                btn_reservar = st.button("Confirmar Reserva", type="primary", use_container_width=True)

            if btn_consultar:
                try:
                    disponible, conflicto = servicio.consultar_disponibilidad(
                        id_unidad, dt_inicio, dt_fin
                    )
                    if disponible:
                        st.success(
                            f"**Disponible:** La unidad `{id_unidad}` está libre de "
                            f"{hora_inicio.strftime('%H:%M')} a {hora_fin.strftime('%H:%M')}."
                        )
                    else:
                        st.error(
                            f"**Unidad ocupada:** Conflicto con la reserva `{conflicto.id}` "
                            f"({conflicto.solicitante}) en el intervalo "
                            f"{conflicto.inicio.strftime('%H:%M')} a {conflicto.fin.strftime('%H:%M')}."
                        )
                except ErrorDominio as err:
                    st.error(f"Error de validación: {err}")

            if btn_reservar:
                try:
                    nueva = servicio.crear_reserva(
                        id_unidad=id_unidad,
                        solicitante=solicitante,
                        inicio=dt_inicio,
                        fin=dt_fin,
                    )
                    st.success(
                        f"**Reserva confirmada con éxito**\n\n"
                        f"- **ID:** `{nueva.id}`\n"
                        f"- **Unidad:** `{nueva.id_unidad}`\n"
                        f"- **Solicitante:** {nueva.solicitante}\n"
                        f"- **Intervalo:** {nueva.inicio.strftime('%Y-%m-%d %H:%M')} a {nueva.fin.strftime('%H:%M')}"
                    )
                    st.rerun()
                except ErrorDominio as err:
                    st.error(f"No se pudo crear la reserva: {err}")

    # =========================================================================
    # TAB 2: CANCELAR RESERVA
    # =========================================================================
    with tab_cancelar:
        st.subheader("Cancelar Reserva Activa")
        if not activas:
            st.write("No hay reservas activas en este momento.")
        else:
            opciones_activas = {
                f"[{r.id}] {r.id_unidad} - {r.solicitante} ({r.inicio.strftime('%Y-%m-%d %H:%M')} a {r.fin.strftime('%H:%M')})": r.id
                for r in activas
            }
            seleccion_cancelar = st.selectbox(
                "Seleccione la reserva a cancelar:", list(opciones_activas.keys())
            )
            id_a_cancelar = opciones_activas[seleccion_cancelar]

            if st.button("Liberar Horario y Cancelar Reserva", type="secondary"):
                try:
                    reserva_canc = servicio.cancelar_reserva(id_a_cancelar)
                    st.warning(
                        f"Reserva `{reserva_canc.id}` cancelada con éxito. "
                        f"El horario `{reserva_canc.inicio.strftime('%H:%M')} a {reserva_canc.fin.strftime('%H:%M')}` "
                        f"para la unidad `{reserva_canc.id_unidad}` ha quedado inmediatamente disponible."
                    )
                    st.rerun()
                except ErrorDominio as err:
                    st.error(f"Error al cancelar: {err}")

    # =========================================================================
    # TAB 3: HISTORIAL COMPLETO
    # =========================================================================
    with tab_historial:
        st.subheader("Historial de Reservas y Estados")
        if not todas_reservas:
            st.write("No hay registros en el sistema.")
        else:
            filtro_unidad = st.selectbox(
                "Filtrar por unidad:",
                ["Todas"] + [eq.id for eq in equipos],
                index=0,
            )
            datos_mostrar = todas_reservas
            if filtro_unidad != "Todas":
                datos_mostrar = [r for r in datos_mostrar if r.id_unidad == filtro_unidad]

            tabla = [
                {
                    "ID": r.id,
                    "Unidad": r.id_unidad,
                    "Solicitante": r.solicitante,
                    "Inicio": r.inicio.strftime("%Y-%m-%d %H:%M"),
                    "Fin": r.fin.strftime("%Y-%m-%d %H:%M"),
                    "Estado": r.estado.value,
                }
                for r in datos_mostrar
            ]
            st.dataframe(tabla, use_container_width=True)

    # =========================================================================
    # TAB 4: CATÁLOGO DE EQUIPOS
    # =========================================================================
    with tab_inventario:
        st.subheader("Unidades Físicas del Laboratorio (Precargadas)")
        tabla_eq = [{"ID Unidad": eq.id, "Descripción": eq.nombre} for eq in equipos]
        st.table(tabla_eq)


if __name__ == "__main__":
    main()
