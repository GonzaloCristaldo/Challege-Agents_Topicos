import importlib


def test_app_streamlit_importable():
    """Verifica que el módulo de la aplicación Streamlit se importe sin errores sintácticos ni de importación."""
    modulo = importlib.import_module("app")
    assert hasattr(modulo, "main")
    assert hasattr(modulo, "get_servicio")
