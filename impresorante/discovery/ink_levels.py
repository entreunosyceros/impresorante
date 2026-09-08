"""Consultas alternativas de niveles de tinta / tóner."""

import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse

from impresorante.snmp import SNMPPrinter

try:
    from impresorante.discovery.canon_usb import (
        query_canon_usb_ink_for_printer,
    )
except Exception:  # pragma: no cover
    query_canon_usb_ink_for_printer = None


_USELESS_INK = {
    "",
    "No disponible",
    "Consultando...",
    "Dispositivo USB detectado",
}

LOW_INK_THRESHOLD = 15


def ink_is_useful(value):
    if value is None:
        return False

    text = str(value).strip()

    if not text:
        return False

    if text in _USELESS_INK:
        return False

    return True


def parse_ink_levels(ink_text):
    """
    Extrae [(nombre, porcentaje), ...] de un texto de consumibles.
    """

    if not ink_text:
        return []

    levels = []

    for match in re.finditer(
        r"([^|:]+?)\s*:\s*(\d+)\s*%",
        str(ink_text),
    ):
        name = match.group(1).strip()
        percent = int(match.group(2))
        levels.append((name, percent))

    return levels


def low_ink_warnings(
    ink_text,
    threshold=LOW_INK_THRESHOLD,
):
    """
    Avisos de tinta baja / vacía.
    Devuelve lista de strings legibles.
    """

    warnings = []

    for name, percent in parse_ink_levels(ink_text):
        if percent <= 0:
            warnings.append(f"{name} vacío ({percent}%)")
        elif percent <= threshold:
            warnings.append(f"{name} bajo ({percent}%)")

    return warnings


def format_ink_with_warnings(
    ink_text,
    threshold=LOW_INK_THRESHOLD,
):
    """Texto de consumibles + sufijo de aviso si aplica."""

    base = ink_text or "No disponible"
    warns = low_ink_warnings(base, threshold)

    if not warns:
        return base

    return f"{base}  ⚠ {' · '.join(warns)}"


def extract_ip(printer):
    for key in ("ip", "port", "uri"):
        value = printer.get(key) or ""

        match = re.search(
            r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})",
            str(value)
        )

        if match:
            return match.group(1)

    return None


def get_lpstat_uris():
    """Mapa nombre CUPS -> device-uri vía lpstat -v."""

    uris = {}

    try:

        result = subprocess.run(
            ["lpstat", "-v"],
            capture_output=True,
            text=True,
            timeout=5
        )

        for line in result.stdout.splitlines():

            match = re.match(
                r"(?:dispositivo para|device for)\s+(.+?):\s+(\S+)",
                line,
                re.IGNORECASE
            )

            if match:
                uris[match.group(1).strip()] = match.group(2).strip()

    except Exception:
        pass

    return uris


def query_ipp_markers(printer_name):
    """
    Consulta marker-* en el cola local de CUPS con ipptool.
    """

    if not printer_name:
        return None

    if not shutil.which("ipptool"):
        return None

    safe_name = urllib.parse.quote(
        printer_name,
        safe=""
    )

    uri = f"ipp://localhost/printers/{safe_name}"

    test_body = (
        "{\n"
        '  NAME "Get marker attrs"\n'
        "  OPERATION Get-Printer-Attributes\n"
        "  GROUP operation-attributes-tag\n"
        "  ATTR charset attributes-charset utf-8\n"
        "  ATTR language attributes-natural-language en\n"
        "  ATTR uri printer-uri $uri\n"
        "  ATTR keyword requested-attributes "
        "marker-levels,marker-names,marker-colors,"
        "marker-types,marker-high-levels\n"
        "}\n"
    )

    path = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".test",
            delete=False,
            encoding="utf-8"
        ) as handle:

            handle.write(test_body)
            path = handle.name

        result = subprocess.run(
            [
                "ipptool",
                "-t",
                uri,
                path
            ],
            capture_output=True,
            text=True,
            timeout=8
        )

        output = (
            result.stdout
            + "\n"
            + result.stderr
        )

        levels_match = re.search(
            r"marker-levels\s*\([^)]*\)\s*=\s*(.+)",
            output,
            re.IGNORECASE
        )

        if not levels_match:
            return None

        levels_raw = levels_match.group(1).strip()

        levels = [
            part.strip()
            for part in re.split(r"[, ]+", levels_raw)
            if part.strip() and part.strip() != "="
        ]

        # A veces viene como "80,70,60,50"
        if len(levels) == 1 and "," in levels[0]:
            levels = [
                part.strip()
                for part in levels[0].split(",")
                if part.strip()
            ]

        names_match = re.search(
            r"marker-names\s*\([^)]*\)\s*=\s*(.+)",
            output,
            re.IGNORECASE
        )

        names = []

        if names_match:
            names = [
                part.strip().strip("'\"")
                for part in re.split(
                    r",(?=(?:[^']*'[^']*')*[^']*$)",
                    names_match.group(1)
                )
                if part.strip()
            ]

        result_parts = []

        for index, level in enumerate(levels):

            try:
                value = int(level)
            except Exception:
                continue

            name = (
                names[index]
                if index < len(names)
                else f"Consumible {index + 1}"
            )

            if value < 0:
                result_parts.append(
                    f"{name}: No disponible"
                )
            else:
                result_parts.append(
                    f"{name}: {value}%"
                )

        if result_parts:
            return " | ".join(result_parts)

    except Exception:
        pass

    finally:

        if path:

            try:
                os.unlink(path)
            except Exception:
                pass

    return None


def _parse_ink_cli_output(output):
    """Parsea la salida típica del comando `ink`."""

    parts = []

    for line in output.splitlines():

        line = line.strip()

        if not line:
            continue

        # Ejemplos:
        # Black: 80 %
        # Cyan: 45%
        # Photo Black: 100%
        match = re.match(
            r"^(.+?)\s*:\s*(-?\d+)\s*%?\s*$",
            line
        )

        if not match:
            continue

        name = match.group(1).strip()
        level = int(match.group(2))

        lower = name.lower()

        if lower in {
            "printer",
            "model",
            "device",
            "port"
        }:
            continue

        if level < 0:
            parts.append(
                f"{name}: No disponible"
            )
        else:
            parts.append(
                f"{name}: {level}%"
            )

    if parts:
        return " | ".join(parts)

    return None


def query_ink_cli_usb(port_number=None):
    """Usa `ink -p usb` (libinklevel) si está instalado."""

    if not shutil.which("ink"):
        return None

    cmd = ["ink", "-p", "usb"]

    if port_number is not None:
        cmd.extend(
            ["-n", str(port_number)]
        )

    try:

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=12
        )

        parsed = _parse_ink_cli_output(
            result.stdout
            or result.stderr
        )

        if parsed:
            return parsed

    except Exception:
        pass

    return None


def query_ink_cli_bjnp(host=None):
    """Usa `ink` contra impresoras Canon BJNP de red."""

    if not shutil.which("ink"):
        return None

    if host:
        cmd = [
            "ink",
            "-b",
            f"bjnp://{host}"
        ]
    else:
        cmd = [
            "ink",
            "-p",
            "bjnp"
        ]

    try:

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=12
        )

        parsed = _parse_ink_cli_output(
            result.stdout
            or result.stderr
        )

        if parsed:
            return parsed

    except Exception:
        pass

    return None


def enrich_printer_ink(printer):
    """
    Completa printer['ink'] con IPP, SNMP, libinklevel o BJNP
    cuando CUPS/Gutenprint no publican marker-levels.
    """

    if ink_is_useful(
        printer.get("ink")
    ):
        return printer

    return refresh_printer_ink(printer)


def refresh_printer_ink(printer):
    """
    Vuelve a consultar los consumibles (valores en vivo, no cacheados).
    """

    printer_name = printer.get(
        "printer_name"
    ) or printer.get(
        "model"
    )

    uri = (
        printer.get("uri")
        or ""
    ).lower()

    printer_type = printer.get(
        "type",
        ""
    )

    model = (
        printer.get("model")
        or ""
    ).lower()

    # Canon USB primero: es la fuente fiable en MG4200
    if (
        printer_type == "USB"
        or uri.startswith("usb://")
        or "usb" in str(
            printer.get("ip", "")
        ).lower()
        or "canon" in model
    ):

        if query_canon_usb_ink_for_printer:
            try:
                from impresorante.discovery.canon_usb import (
                    query_canon_usb_info_for_printer,
                )

                info = query_canon_usb_info_for_printer(
                    printer
                )
            except Exception:
                info = {
                    "ink": query_canon_usb_ink_for_printer(
                        printer
                    )
                }

            if ink_is_useful(info.get("ink")):
                printer["ink"] = info["ink"]

            if info.get("status"):
                printer["status"] = info["status"]

            if ink_is_useful(printer.get("ink")):
                return printer

        usb_ink = query_ink_cli_usb()

        if ink_is_useful(usb_ink):
            printer["ink"] = usb_ink
            return printer

    ipp_ink = query_ipp_markers(
        printer_name
    )

    if ink_is_useful(ipp_ink):
        printer["ink"] = ipp_ink
        return printer

    ip = extract_ip(printer)

    if ip:

        snmp_ink = SNMPPrinter.get_ink(
            ip
        )

        if ink_is_useful(snmp_ink):
            printer["ink"] = snmp_ink
            return printer

        if "canon" in model:

            bjnp_ink = query_ink_cli_bjnp(
                ip
            )

            if ink_is_useful(bjnp_ink):
                printer["ink"] = bjnp_ink
                return printer

    printer["ink"] = "No disponible"
    return printer
