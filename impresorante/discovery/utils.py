"""Utilidades de deduplicación de impresoras."""

import re
import urllib.parse

from impresorante.discovery.ink_levels import ink_is_useful


def _usb_identity(printer):
    """Identidad estable para la misma impresora USB física."""

    uri = printer.get("uri") or ""

    if not uri and "usb://" in str(printer.get("ip", "")).lower():
        uri = printer.get("ip", "")

    if not uri.lower().startswith("usb://"):
        return None

    try:
        parsed = urllib.parse.urlparse(
            urllib.parse.unquote(uri)
        )
        query = urllib.parse.parse_qs(parsed.query)
        serial = (
            query.get("serial", [None])[0]
            or query.get("Serial", [None])[0]
        )

        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").strip("/").lower()

        if serial:
            return (
                "usb",
                host,
                path,
                serial.lower(),
            )

        if host or path:
            return (
                "usb",
                host,
                path,
            )

    except Exception:
        pass

    return (
        "usb",
        uri.lower(),
    )


def printer_key(printer):
    name = printer.get(
        "model",
        ""
    ).lower()

    connection = printer.get(
        "ip",
        ""
    ).lower()

    # Para impresoras de red la IP es una
    # identificación especialmente buena.

    if printer.get("type") == "Red":

        return (
            "network",
            connection
        )

    usb_key = _usb_identity(printer)

    if usb_key:
        return usb_key

    # Para impresoras instaladas/USB usamos nombre.

    clean_name = re.sub(
        r"\s+",
        " ",
        name
    ).strip()

    # Normalizar "MG4200-series" ~ "canon mg4200 series"
    clean_name = clean_name.replace("-", " ")
    clean_name = re.sub(
        r"^canon\s+",
        "",
        clean_name
    ).strip()

    return (
        "local",
        clean_name,
    )


def _score(printer):
    score = 0

    if printer.get("type") == "Sistema":
        score += 3

    if printer.get("printer_name"):
        score += 2

    if ink_is_useful(printer.get("ink")):
        score += 2

    if printer.get("uri"):
        score += 1

    return score


def deduplicate_printers(printers):

    result = {}

    for printer in printers:

        key = printer_key(
            printer
        )

        if key not in result:

            result[key] = printer

        else:

            old = result[key]

            # Conservamos la entrada más completa
            # (cola del sistema + tinta útil).

            if _score(printer) > _score(old):
                merged = dict(printer)
            else:
                merged = dict(old)
                printer, old = old, printer

            # Recuperar tinta útil de la otra si falta
            if (
                not ink_is_useful(merged.get("ink"))
                and ink_is_useful(old.get("ink"))
            ):
                merged["ink"] = old["ink"]

            if (
                not merged.get("printer_name")
                and old.get("printer_name")
            ):
                merged["printer_name"] = old[
                    "printer_name"
                ]

            if not merged.get("uri") and old.get("uri"):
                merged["uri"] = old["uri"]

            result[key] = merged

    return list(result.values())
