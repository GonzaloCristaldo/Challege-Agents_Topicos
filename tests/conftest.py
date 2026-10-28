import json
from pathlib import Path
import pytest

from src.repositorio import JsonReservaRepositorio
from src.servicio import ReservaServicio


@pytest.fixture
def repo_aislado(tmp_path: Path) -> JsonReservaRepositorio:
    """
    Provee una instancia del repositorio con persistencia aislada en tmp_path.
    Copia el inventario base para asegurar pruebas reproducibles sin tocar data/.
    """
    base_dir = Path(__file__).resolve().parent.parent
    ruta_inventario_original = base_dir / "data" / "inventario.json"
    
    ruta_inventario_test = tmp_path / "inventario_test.json"
    ruta_inventario_test.write_text(
        ruta_inventario_original.read_text(encoding="utf-8"), encoding="utf-8"
    )
    
    ruta_reservas_test = tmp_path / "reservas_test.json"
    return JsonReservaRepositorio(
        ruta_reservas=ruta_reservas_test,
        ruta_inventario=ruta_inventario_test,
    )


@pytest.fixture
def servicio(repo_aislado: JsonReservaRepositorio) -> ReservaServicio:
    """Provee una instancia de ReservaServicio con el repositorio aislado."""
    return ReservaServicio(repositorio=repo_aislado)
