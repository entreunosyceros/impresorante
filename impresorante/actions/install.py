"""Instalación de impresoras en Windows y Linux."""

import platform
import re
import subprocess

from impresorante.deps import win32print


def install_printer(printer):
    """
    Intenta configurar la impresora en el sistema.

    Devuelve (success: bool, message: str).
    """

    model = printer.get(
        "model",
        "Impresora"
    )

    success = False
    os_type = platform.system()

    # ------------------------------------------------
    # WINDOWS
    # ------------------------------------------------

    if os_type == "Windows":

        if not win32print:
            return False, "Falta pywin32."

        if printer["type"] == "Red":

            ip = printer.get(
                "ip"
            )

            port_name = (
                f"IP_{ip}"
            )

            try:

                powershell = f"""
$ErrorActionPreference = "Stop"

if (-not (Get-PrinterPort -Name "{port_name}" -ErrorAction SilentlyContinue)) {{
    Add-PrinterPort -Name "{port_name}" -PrinterHostAddress "{ip}"
}}

"""

                # Se crea el puerto, pero NO se instala
                # falsamente un driver específico.
                #
                # Windows necesita un driver compatible.

                result = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        powershell
                    ],
                    capture_output=True,
                    text=True
                )

                success = (
                    result.returncode == 0
                )

            except Exception:
                success = False

        elif printer["type"] == "USB":

            # Si ya existe en Windows, no hay que
            # crear manualmente un puerto USB.
            success = True

    # ------------------------------------------------
    # LINUX
    # ------------------------------------------------

    elif os_type == "Linux":

        safe_name = re.sub(
            r"[^a-zA-Z0-9_-]",
            "_",
            model
        )

        uri = printer.get(
            "uri"
        )

        if printer["type"] == "Red":

            ip = printer.get(
                "ip"
            )

            uri = (
                f"ipp://{ip}/ipp/print"
            )

        if printer["type"] == "USB":

            if not uri:

                success = False

            else:

                cmd = [
                    "lpadmin",
                    "-p",
                    safe_name,
                    "-v",
                    uri,
                    "-E",
                    "-m",
                    "everywhere"
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True
                )

                success = (
                    result.returncode == 0
                )

        elif printer["type"] == "Red":

            cmd = [
                "lpadmin",
                "-p",
                safe_name,
                "-v",
                uri,
                "-E",
                "-m",
                "everywhere"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            success = (
                result.returncode == 0
            )

    if success:
        return True, f"¡Éxito! {model} configurada."

    return False, f"No se pudo configurar {model}."
