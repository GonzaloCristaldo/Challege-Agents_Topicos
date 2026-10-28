import json
from pathlib import Path
from typing import Dict, List, Optional

from src.modelos import Equipo, Reserva


class JsonReservaRepositorio:
    """
    Repositorio de persistencia en disco basado en archivos JSON.
    Permite inyectar las rutas de inventario y reservas para aislar pruebas unitarias.
    """

    def __init__(
        self,
        ruta_reservas: Optional[Path] = None,
        ruta_inventario: Optional[Path] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent
        self.ruta_inventario = (
            ruta_inventario or (base_dir / "data" / "inventario.json")
        )
        self.ruta_reservas = (
            ruta_reservas or (base_dir / "data" / "reservas.json")
        )

        self._inventario: Dict[str, Equipo] = {}
        self._reservas: Dict[str, Reserva] = {}

        self._cargar_inventario()
        self._cargar_reservas()

    def _cargar_inventario(self) -> None:
        """Carga el inventario precargado e inmutable desde el archivo JSON."""
        if not self.ruta_inventario.exists():
            raise FileNotFoundError(
                f"No se encontró el archivo de inventario en {self.ruta_inventario}"
            )
        with open(self.ruta_inventario, "r", encoding="utf-8") as f:
            datos = json.load(f)
            self._inventario = {
                item["id"]: Equipo(id=item["id"], nombre=item["nombre"])
                for item in datos
            }

    def _cargar_reservas(self) -> None:
        """Recupera las reservas persistidas en disco. Si no existe el archivo, inicializa vacío."""
        if not self.ruta_reservas.exists():
            self._reservas = {}
            return

        with open(self.ruta_reservas, "r", encoding="utf-8") as f:
            try:
                datos = json.load(f)
                self._reservas = {
                    item["id"]: Reserva.from_dict(item) for item in datos
                }
            except json.JSONDecodeError:
                self._reservas = {}

    def _guardar_en_disco(self) -> None:
        """Persiste atómicamente el estado actual de las reservas en disco."""
        self.ruta_reservas.parent.mkdir(parents=True, exist_ok=True)
        datos = [reserva.to_dict() for reserva in self._reservas.values()]
        
        # Escritura atómica mediante archivo temporal para evitar corrupción
        temp_file = self.ruta_reservas.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        temp_file.replace(self.ruta_reservas)

    def obtener_inventario(self) -> List[Equipo]:
        """Retorna la lista completa de unidades del catálogo."""
        return list(self._inventario.values())

    def obtener_equipo(self, id_unidad: str) -> Optional[Equipo]:
        """Obtiene un equipo por su ID o None si no existe."""
        return self._inventario.get(id_unidad)

    def guardar_reserva(self, reserva: Reserva) -> None:
        """Guarda o actualiza una reserva y sincroniza con disco."""
        self._reservas[reserva.id] = reserva
        self._guardar_en_disco()

    def obtener_reserva(self, id_reserva: str) -> Optional[Reserva]:
        """Recupera una reserva por su ID único."""
        return self._reservas.get(id_reserva)

    def listar_reservas(self, id_unidad: Optional[str] = None) -> List[Reserva]:
        """Lista todas las reservas, opcionalmente filtradas por id_unidad."""
        if id_unidad:
            return [r for r in self._reservas.values() if r.id_unidad == id_unidad]
        return list(self._reservas.values())

    def reiniciar_reservas(self) -> None:
        """Limpia todas las reservas y borra el archivo de persistencia."""
        self._reservas.clear()
        if self.ruta_reservas.exists():
            self.ruta_reservas.unlink()
