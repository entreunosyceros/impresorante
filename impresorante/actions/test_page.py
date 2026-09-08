"""Envío de página de prueba a una impresora."""

import os
import platform
import socket
import subprocess
import tempfile


def send_test_page(printer):
    """
    Envía una página de prueba.

    Devuelve True si el envío parece correcto.
    """

    os_type = platform.system()

    p_name = printer.get(
        "printer_name",
        printer.get(
            "model",
            "Impresora"
        )
    )

    success = False

    test_content = (
        "==========================================\n"
        "         PÁGINA DE PRUEBA IMPRESORANTE    \n"
        "==========================================\n"
        f"Dispositivo: {p_name}\n"
        f"Tipo de conexión: "
        f"{printer.get('type', '')}\n"
        "==========================================\n"
    )

    # ------------------------------------------------
    # RED RAW 9100
    # ------------------------------------------------

    if (
        printer.get("type") == "Red"
        and
        printer.get("port") == 9100
    ):

        try:

            with socket.create_connection(
                (
                    printer["ip"],
                    9100
                ),
                timeout=3
            ) as sock:

                sock.sendall(
                    test_content.encode(
                        "utf-8"
                    ) +
                    b"\x0c"
                )

            success = True

        except Exception:
            pass

    # ------------------------------------------------
    # CUPS
    # ------------------------------------------------

    if (
        not success
        and
        os_type == "Linux"
    ):

        try:

            result = subprocess.run(
                [
                    "lpr",
                    "-P",
                    p_name
                ],
                input=test_content,
                text=True,
                capture_output=True
            )

            success = (
                result.returncode == 0
            )

        except Exception:
            pass

    # ------------------------------------------------
    # WINDOWS
    # ------------------------------------------------

    if (
        not success
        and
        os_type == "Windows"
    ):

        try:

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".txt",
                mode="w",
                encoding="utf-8"
            ) as f:

                f.write(
                    test_content
                )

                temp_file = f.name

            ps = f"""
Get-Content -Raw -LiteralPath "{temp_file}" |
Out-Printer -Name "{p_name}"
"""

            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    ps
                ],
                capture_output=True
            )

            try:
                os.unlink(
                    temp_file
                )
            except Exception:
                pass

            success = (
                result.returncode == 0
            )

        except Exception:
            pass

    return success
