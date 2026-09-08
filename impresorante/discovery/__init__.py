"""API pública de descubrimiento de impresoras."""

from impresorante.discovery.enrich import enrich_printer, refresh_printer
from impresorante.discovery.ink_levels import (
    LOW_INK_THRESHOLD,
    enrich_printer_ink,
    format_ink_with_warnings,
    low_ink_warnings,
    parse_ink_levels,
    query_ink_cli_bjnp,
    query_ink_cli_usb,
    query_ipp_markers,
    refresh_printer_ink,
)
from impresorante.discovery.installed import (
    describe_uri,
    get_cups_ink,
    get_linux_cups_ink_command,
    get_windows_wmi_printers,
    scan_installed_printers,
    scan_linux_installed,
    scan_windows_installed,
)
from impresorante.discovery.network import (
    check_ipp,
    check_port,
    detect_http_name,
    get_default_subnet,
    inspect_network_printer,
    scan_mdns,
    scan_network,
)
from impresorante.discovery.status import (
    enrich_printer_status,
    refresh_printer_status,
)
from impresorante.discovery.usb import (
    scan_linux_usb,
    scan_usb_printers,
    scan_windows_usb,
    usb_uri_model,
)
from impresorante.discovery.utils import (
    deduplicate_printers,
    printer_key,
)

__all__ = [
    "LOW_INK_THRESHOLD",
    "check_ipp",
    "check_port",
    "deduplicate_printers",
    "describe_uri",
    "detect_http_name",
    "enrich_printer",
    "enrich_printer_ink",
    "enrich_printer_status",
    "format_ink_with_warnings",
    "get_cups_ink",
    "get_default_subnet",
    "get_linux_cups_ink_command",
    "get_windows_wmi_printers",
    "inspect_network_printer",
    "low_ink_warnings",
    "parse_ink_levels",
    "printer_key",
    "query_ink_cli_bjnp",
    "query_ink_cli_usb",
    "query_ipp_markers",
    "refresh_printer",
    "refresh_printer_ink",
    "refresh_printer_status",
    "scan_installed_printers",
    "scan_linux_installed",
    "scan_linux_usb",
    "scan_mdns",
    "scan_network",
    "scan_usb_printers",
    "scan_windows_installed",
    "scan_windows_usb",
    "usb_uri_model",
]
