import pytest
from src.cli import main


def test_cli_inventario(capsys):
    """Comprueba que el subcomando inventario lista las 5 unidades."""
    codigo = main(["inventario"])
    assert codigo == 0
    captura = capsys.readouterr()
    assert "MIC-01" in captura.out
    assert "MIC-02" in captura.out
    assert "OSC-01" in captura.out
    assert "MUL-01" in captura.out
    assert "FUE-01" in captura.out


def test_cli_ayuda_sin_argumentos(capsys):
    """Comprueba que invocar sin argumentos muestra la ayuda."""
    codigo = main([])
    assert codigo == 0
    captura = capsys.readouterr()
    assert "Sistema de Gestión de Reservas" in captura.out
