"""Impresoras instaladas en el sistema (Windows / Linux CUPS)."""

import platform
import re
import subprocess
import urllib.parse

from impresorante.deps import cups, win32com, win32print
from impresorante.discovery.enrich import enrich_printer
from impresorante.discovery.ink_levels import (
    get_lpstat_uris,
    ink_is_useful,
    query_ipp_markers,
)
from impresorante.snmp import SNMPPrinter


def scan_windows_installed():

    printers = []

    if not win32print:
        return printers

    try:

        flags = (
            win32print.PRINTER_ENUM_LOCAL |
            win32print.PRINTER_ENUM_CONNECTIONS
        )

        data = win32print.EnumPrinters(
            flags,
            None,
            2
        )

        for item in data:

            name = item.get(
                "pPrinterName",
                ""
            )

            port = item.get(
                "pPortName",
                ""
            )

            if not name:
                continue

            printers.append({
                "ip": f"Puerto: {port}",
                "model": name,
                "type": "Sistema",
                "ink": "Consultando...",
                "printer_name": name,
                "port": port
            })

    except Exception:
        pass

    return printers


def get_windows_wmi_printers():

    printers = []

    if not win32com:
        return printers

    try:

        wmi = win32com.client.GetObject(
            "winmgmts:"
        )

        query = (
            "SELECT Name, PortName, Default, "
            "PrinterStatus, WorkOffline "
            "FROM Win32_Printer"
        )

        for printer in wmi.ExecQuery(query):

            name = getattr(
                printer,
                "Name",
                ""
            )

            port = getattr(
                printer,
                "PortName",
                ""
            )

            if not name:
                continue

            status = getattr(
                printer,
                "PrinterStatus",
                None
            )

            default = getattr(
                printer,
                "Default",
                False
            )

            status_text = {
                1: "Otro",
                2: "Desconocido",
                3: "En reposo",
                4: "Imprimiendo",
                5: "Calentando",
                6: "Detenido",
                7: "Offline"
            }.get(
                status,
                "Desconocido"
            )

            if default:
                status_text += " | Predeterminada"

            printers.append({
                "ip": f"Puerto: {port}",
                "model": name,
                "type": "Sistema",
                "ink": status_text,
                "printer_name": name,
                "port": port
            })

    except Exception:
        pass

    return printers


def get_cups_ink(connection, printer_name):

    try:

        attrs = connection.getPrinterAttributes(
            printer_name
        )

        levels = attrs.get(
            "marker-levels"
        )

        names = attrs.get(
            "marker-names"
        )

        if levels is not None:

            if not isinstance(
                levels,
                (list, tuple)
            ):

                levels = [levels]

            if not isinstance(
                names,
                (list, tuple)
            ):

                names = (
                    [names]
                    if names is not None
                    else []
                )

            result = []

            for i, level in enumerate(levels):

                name = (
                    names[i]
                    if i < len(names)
                    else f"Consumible {i + 1}"
                )

                try:

                    level = int(level)

                    if level < 0:

                        result.append(
                            f"{name}: No disponible"
                        )

                    else:

                        result.append(
                            f"{name}: {level}%"
                        )

                except Exception:

                    result.append(
                        f"{name}: {level}"
                    )

            if result:
                return " | ".join(result)

    except Exception:
        pass

    ipp_ink = query_ipp_markers(
        printer_name
    )

    if ink_is_useful(ipp_ink):
        return ipp_ink

    return "No disponible"


def get_linux_cups_ink_command(printer_name):

    try:

        result = subprocess.run(
            [
                "lpstat",
                "-l",
                "-p",
                printer_name
            ],
            capture_output=True,
            text=True,
            timeout=5
        )

        output = result.stdout

        # Algunos backends imprimen directamente
        # información de consumibles.

        if "marker-levels" in output:

            match = re.search(
                r"marker-levels[=:]\s*([^\s]+)",
                output
            )

            if match:
                return match.group(1)

    except Exception:
        pass

    return "No disponible"


def describe_uri(uri):

    if not uri:
        return "CUPS"

    if uri.startswith("usb://"):
        return "USB"

    if uri.startswith(
        ("ipp://", "ipps://")
    ):

        try:

            parsed = urllib.parse.urlparse(
                uri
            )

            return (
                f"IP: {parsed.hostname}"
                if parsed.hostname
                else "IPP"
            )

        except Exception:
            return "IPP"

    if uri.startswith(
        ("socket://", "lpd://")
    ):

        try:

            parsed = urllib.parse.urlparse(
                uri
            )

            return (
                f"IP: {parsed.hostname}"
                if parsed.hostname
                else "Red"
            )

        except Exception:
            return "Red"

    return uri


def scan_linux_installed():

    printers = []

    # ----------------------------------------------------
    # Primera opción: pycups
    # ----------------------------------------------------

    if cups:

        try:

            connection = cups.Connection()

            printer_dict = (
                connection.getPrinters()
            )

            for name, data in printer_dict.items():

                uri = data.get(
                    "device-uri",
                    ""
                )

                printers.append({
                    "ip": describe_uri(uri),
                    "model": name,
                    "type": "Sistema",
                    "ink": get_cups_ink(
                        connection,
                        name
                    ),
                    "printer_name": name,
                    "uri": uri
                })

            if printers:
                for printer in printers:
                    enrich_printer(printer)

                return printers

        except Exception:
            pass

    # ----------------------------------------------------
    # Fallback: lpstat
    # ----------------------------------------------------

    try:

        uris = get_lpstat_uris()

        result = subprocess.run(
            ["lpstat", "-e"],
            capture_output=True,
            text=True,
            timeout=5
        )

        for line in result.stdout.splitlines():

            name = line.strip()

            if not name:
                continue

            uri = uris.get(
                name,
                ""
            )

            ink = get_linux_cups_ink_command(
                name
            )

            if not ink_is_useful(ink):
                ink = query_ipp_markers(
                    name
                ) or "No disponible"

            printers.append({
                "ip": describe_uri(uri) if uri else "CUPS Local",
                "model": name,
                "type": "Sistema",
                "ink": ink,
                "printer_name": name,
                "uri": uri or None
            })

    except Exception:
        pass

    for printer in printers:
        enrich_printer(printer)

    return printers


def scan_installed_printers():

    if platform.system() == "Windows":

        printers = (
            scan_windows_installed()
        )

        # Intentamos consultar tinta por SNMP
        # si el puerto corresponde a una IP.

        for printer in printers:

            port = printer.get(
                "port",
                ""
            )

            ip_match = re.search(
                r"(\d+\.\d+\.\d+\.\d+)",
                port
            )

            if ip_match:

                ip = ip_match.group(1)

                printer["ink"] = (
                    SNMPPrinter.get_ink(
                        ip
                    )
                )

            enrich_printer(printer)

        # WMI no da tinta directamente.

        return printers

    elif platform.system() == "Linux":

        return scan_linux_installed()

    return []
