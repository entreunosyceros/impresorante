"""Estado operativo de impresoras (CUPS / IPP / red / USB)."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import urllib.parse

from impresorante.discovery.ink_levels import extract_ip
from impresorante.snmp import snmp_query, SNMPPrinter

try:
    from impresorante.discovery.canon_usb import (
        query_canon_usb_info_for_printer,
    )
except Exception:  # pragma: no cover
    query_canon_usb_info_for_printer = None


_STATE_MAP = {
    "3": "Inactiva",
    "4": "Imprimiendo",
    "5": "Detenida",
    "idle": "En reposo",
    "processing": "Imprimiendo",
    "stopped": "Detenida",
}


_REASON_MAP = {
    "none": None,
    "marker-supply-low": "Tinta/tóner bajo",
    "marker-supply-empty": "Tinta/tóner vacío",
    "marker-supply-almost-empty": "Tinta/tóner casi vacío",
    "media-empty": "Sin papel",
    "media-jam": "Atasco de papel",
    "media-needed": "Cargar papel",
    "door-open": "Tapa abierta",
    "cover-open": "Cubierta abierta",
    "offline": "Fuera de línea",
    "paused": "En pausa",
    "toner-low": "Tóner bajo",
    "toner-empty": "Tóner vacío",
}


def _translate_reasons(reasons):
    if not reasons:
        return []

    notes = []

    for raw in re.split(r"[,\s]+", reasons):
        key = raw.strip().lower()

        if not key or key == "none":
            continue

        # Quitar prefijos tipo "printer-state-reasons="
        key = key.split("=")[-1]
        mapped = _REASON_MAP.get(key)

        if mapped:
            notes.append(mapped)
        elif key not in {"none"}:
            notes.append(key.replace("-", " "))

    return notes


def query_cups_status(printer_name):
    if not printer_name:
        return None

    # IPP local
    if shutil.which("ipptool"):
        safe = urllib.parse.quote(printer_name, safe="")
        uri = f"ipp://localhost/printers/{safe}"
        body = (
            "{\n"
            '  NAME "Get status"\n'
            "  OPERATION Get-Printer-Attributes\n"
            "  GROUP operation-attributes-tag\n"
            "  ATTR charset attributes-charset utf-8\n"
            "  ATTR language attributes-natural-language en\n"
            "  ATTR uri printer-uri $uri\n"
            "  ATTR keyword requested-attributes "
            "printer-state,printer-state-reasons,"
            "printer-is-accepting-jobs\n"
            "}\n"
        )
        path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".test",
                delete=False,
                encoding="utf-8",
            ) as handle:
                handle.write(body)
                path = handle.name

            result = subprocess.run(
                ["ipptool", "-t", uri, path],
                capture_output=True,
                text=True,
                timeout=6,
            )
            output = result.stdout + "\n" + result.stderr

            state_m = re.search(
                r"printer-state\s*\([^)]*\)\s*=\s*(\S+)",
                output,
                re.IGNORECASE,
            )
            reasons_m = re.search(
                r"printer-state-reasons\s*\([^)]*\)\s*=\s*(.+)",
                output,
                re.IGNORECASE,
            )

            state_raw = state_m.group(1).strip().lower() if state_m else ""
            # state can be keyword idle or integer 3
            state = _STATE_MAP.get(
                state_raw,
                _STATE_MAP.get(state_raw.strip("'\"")),
            )

            if not state and state_raw.isdigit():
                state = _STATE_MAP.get(state_raw, f"Estado {state_raw}")

            if not state and state_raw:
                state = state_raw

            reasons = ""

            if reasons_m:
                reasons = reasons_m.group(1).strip()

            notes = _translate_reasons(reasons)
            parts = [p for p in [state, *notes] if p]

            if parts:
                return " · ".join(parts)

        except Exception:
            pass

        finally:
            if path:
                try:
                    import os
                    os.unlink(path)
                except Exception:
                    pass

    # Fallback lpstat
    try:
        result = subprocess.run(
            ["lpstat", "-p", printer_name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        text = (result.stdout or "").lower()

        if "idle" in text or "inactiva" in text or "reposo" in text:
            return "En reposo"

        if "printing" in text or "imprimiendo" in text:
            return "Imprimiendo"

        if "disabled" in text or "desactivada" in text:
            return "Desactivada"

        if "paused" in text or "pausada" in text:
            return "En pausa"

        if result.returncode == 0 and result.stdout.strip():
            return "Disponible"

    except Exception:
        pass

    return None


def query_network_status(ip):
    if not ip:
        return None

    # hrPrinterStatus
    value, tag = snmp_query(
        ip,
        "1.3.6.1.2.1.25.3.5.1.1.1",
        timeout=0.6,
    )

    if value is not None:
        decoded = SNMPPrinter.decode_value(tag, value)

        try:
            code = int(decoded)
        except Exception:
            code = None

        mapping = {
            1: "Otro",
            2: "Desconocido",
            3: "En reposo",
            4: "Imprimiendo",
            5: "Calentando",
        }

        if code in mapping:
            return mapping[code]

    # Si responde al puerto de impresión, al menos está alcanzable
    from impresorante.discovery.network import check_ipp

    if check_ipp(ip):
        return "Alcanzable"

    return "No responde"


def refresh_printer_status(printer):
    """Actualiza printer['status'] con la mejor fuente disponible."""

    uri = (printer.get("uri") or "").lower()
    model = (printer.get("model") or "").lower()
    printer_type = printer.get("type", "")
    name = printer.get("printer_name") or printer.get("model")

    # Canon USB: estado del XML de estado
    if query_canon_usb_info_for_printer and (
        printer_type == "USB"
        or uri.startswith("usb://")
        or ("canon" in model and "usb" in str(printer.get("ip", "")).lower())
        or ("canon" in model and uri.startswith("usb://"))
    ):
        info = query_canon_usb_info_for_printer(printer)

        if info and info.get("status"):
            printer["status"] = info["status"]
            return printer

    if printer_type == "Sistema" or printer.get("printer_name"):
        cups = query_cups_status(name)

        if cups:
            printer["status"] = cups
            return printer

    ip = extract_ip(printer)

    if ip and printer_type == "Red":
        net = query_network_status(ip)

        if net:
            printer["status"] = net
            return printer

    if printer_type == "USB":
        printer["status"] = printer.get("status") or "USB detectada"
        return printer

    if not printer.get("status"):
        printer["status"] = "Desconocido"

    return printer


def enrich_printer_status(printer):
    if printer.get("status") and printer["status"] not in {
        "",
        "Desconocido",
        "Consultando...",
    }:
        return printer

    return refresh_printer_status(printer)
