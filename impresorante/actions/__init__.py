"""Acciones sobre impresoras (instalar, página de prueba)."""

from impresorante.actions.install import install_printer
from impresorante.actions.test_page import send_test_page

__all__ = [
    "install_printer",
    "send_test_page",
]
