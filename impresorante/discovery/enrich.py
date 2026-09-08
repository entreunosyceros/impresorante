"""Enriquece un dict de impresora con tinta y estado."""

from impresorante.discovery.ink_levels import (
    enrich_printer_ink,
    refresh_printer_ink,
)
from impresorante.discovery.status import (
    enrich_printer_status,
    refresh_printer_status,
)


def enrich_printer(printer):
    enrich_printer_ink(printer)
    enrich_printer_status(printer)
    return printer


def refresh_printer(printer):
    refresh_printer_ink(printer)
    refresh_printer_status(printer)
    return printer
