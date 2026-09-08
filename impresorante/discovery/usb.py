"""Detección de impresoras USB."""

import platform
import re
import subprocess
import urllib.parse

from impresorante.deps import win32com
from impresorante.discovery.enrich import enrich_printer


def scan_windows_usb():

    printers = []

    if not win32com:
        return printers

    try:

        wmi = win32com.client.GetObject(
            "winmgmts:"
        )

        query = """
            SELECT Name, Caption, DeviceID,
                   PNPClass, Service
            FROM Win32_PnPEntity
            WHERE PNPClass = 'Printer'
               OR Service = 'usbprint'
        """

        for dev in wmi.ExecQuery(query):

            caption = getattr(
                dev,
                "Caption",
                ""
            )

            device_id = getattr(
                dev,
                "DeviceID",
                ""
            )

            if not caption:
                continue

            printers.append({
                "ip": "USB Local",
                "model": caption,
                "type": "USB",
                "ink": "Consultando...",
                "device_id": device_id
            })

    except Exception:
        pass

    return printers


def scan_linux_usb():

    printers = []

    try:

        result = subprocess.run(
            ["lpinfo", "-v"],
            capture_output=True,
            text=True,
            timeout=10
        )

        for line in result.stdout.splitlines():

            lower = line.lower()

            if (
                "usb://" not in lower
                and
                "direct usb" not in lower
            ):
                continue

            uri_match = re.search(
                r"(usb://\S+)",
                line,
                re.IGNORECASE
            )

            uri = (
                uri_match.group(1)
                if uri_match
                else ""
            )

            model = usb_uri_model(
                uri
            )

            printers.append({
                "ip": "USB Local",
                "model": model,
                "type": "USB",
                "ink": "Dispositivo USB detectado",
                "uri": uri
            })

    except Exception:
        pass

    return printers


def usb_uri_model(uri):

    if not uri:
        return "Impresora USB"

    try:

        decoded = urllib.parse.unquote(
            uri
        )

        parsed = urllib.parse.urlparse(
            decoded
        )

        # usb://Canon/MG4200 series?serial=...
        host = (parsed.netloc or "").strip()
        path = (parsed.path or "").strip("/")

        if host and path:
            return f"{host} {path}".strip()

        if host:
            return host

        if path:
            return path

        parts = [
            p for p in decoded.replace(
                "usb://",
                ""
            ).split("/")
            if p.strip()
        ]

        if parts:
            return parts[-1].split(
                "?",
                1
            )[0].strip()

    except Exception:
        pass

    return "Impresora USB"


def scan_usb_printers():

    if platform.system() == "Windows":
        printers = scan_windows_usb()
    elif platform.system() == "Linux":
        printers = scan_linux_usb()
    else:
        printers = []

    for printer in printers:
        enrich_printer(printer)

    return printers
