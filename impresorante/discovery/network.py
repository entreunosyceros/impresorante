"""Escaneo de red, puertos de impresión y mDNS."""

import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from impresorante.deps import ServiceBrowser, Zeroconf
from impresorante.discovery.enrich import enrich_printer
from impresorante.discovery.ink_levels import (
    enrich_printer_ink,
    ink_is_useful,
)
from impresorante.snmp import SNMPPrinter


def get_default_subnet():

    try:

        s = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        s.connect(
            ("8.8.8.8", 80)
        )

        ip = s.getsockname()[0]

        s.close()

        parts = ip.split(".")

        return ".".join(parts[:3])

    except Exception:

        return "192.168.1"


def check_port(ip, port, timeout=0.35):

    try:

        with socket.create_connection(
            (ip, port),
            timeout=timeout
        ):

            return True

    except Exception:

        return False


def check_ipp(ip):

    ports = [
        631,
        9100,
        515
    ]

    for port in ports:

        if check_port(
            ip,
            port
        ):

            return port

    return None


def detect_http_name(ip):

    # No se utiliza para descubrir dispositivos.
    # Solamente para intentar identificar una
    # impresora que ya sabemos que tiene un puerto
    # de impresión abierto.

    try:

        import urllib.request

        request = urllib.request.Request(
            f"http://{ip}/",
            headers={
                "User-Agent": "Impresorante/2.0"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=1
        ) as response:

            data = response.read(
                8192
            ).decode(
                "utf-8",
                errors="ignore"
            )

            title = re.search(
                r"<title[^>]*>(.*?)</title>",
                data,
                re.IGNORECASE |
                re.DOTALL
            )

            if title:

                text = re.sub(
                    r"\s+",
                    " ",
                    title.group(1)
                ).strip()

                if text:
                    return text

    except Exception:
        pass

    return "Impresora de red"


def inspect_network_printer(ip, port):

    model = SNMPPrinter.get_model(
        ip
    )

    ink = SNMPPrinter.get_ink(
        ip
    )

    if model == "Impresora de red":

        model = detect_http_name(
            ip
        )

    printer = {
        "ip": ip,
        "model": model,
        "type": "Red",
        "ink": ink,
        "port": port
    }

    if not ink_is_useful(ink):
        enrich_printer_ink(printer)

    enrich_printer(printer)

    return printer


def scan_network(subnet, start=1, end=254):

    printers = []

    try:
        start = max(1, min(254, int(start)))
        end = max(1, min(254, int(end)))
    except Exception:
        start, end = 1, 254

    if start > end:
        start, end = end, start

    router_keywords = [
        "router",
        "gateway",
        "openwrt",
        "tp-link",
        "netgear",
        "asus",
        "mikrotik",
        "huawei",
        "zte"
    ]

    def inspect(i):

        ip = f"{subnet}.{i}"

        port = check_ipp(
            ip
        )

        if not port:
            return None

        printer = inspect_network_printer(
            ip,
            port
        )

        model_lower = printer[
            "model"
        ].lower()

        if any(
            keyword in model_lower
            for keyword in router_keywords
        ):

            return None

        return printer

    with ThreadPoolExecutor(
        max_workers=64
    ) as executor:

        futures = [
            executor.submit(
                inspect,
                i
            )
            for i in range(start, end + 1)
        ]

        for future in as_completed(
            futures
        ):

            try:

                result = future.result()

                if result:
                    printers.append(
                        result
                    )

            except Exception:
                pass

    return printers


def scan_mdns():

    printers = []

    if not Zeroconf:
        return printers

    found = []

    class Listener:

        def add_service(
            self,
            zeroconf,
            service_type,
            name
        ):

            found.append(
                (
                    service_type,
                    name
                )
            )

        def remove_service(
            self,
            zeroconf,
            service_type,
            name
        ):
            pass

        def update_service(
            self,
            zeroconf,
            service_type,
            name
        ):
            pass

    zc = Zeroconf()

    listener = Listener()

    service_types = [
        "_ipp._tcp.local.",
        "_ipps._tcp.local.",
        "_printer._tcp.local."
    ]

    browsers = []

    try:

        for service_type in service_types:

            browsers.append(
                ServiceBrowser(
                    zc,
                    service_type,
                    listener
                )
            )

        # Esperamos brevemente por anuncios.

        time.sleep(2)

        for service_type, name in found:

            try:

                info = zc.get_service_info(
                    service_type,
                    name
                )

                if not info:
                    continue

                addresses = (
                    info.parsed_addresses()
                )

                if not addresses:
                    continue

                ip = addresses[0]

                port = info.port

                model = (
                    info.properties.get(
                        b"ty",
                        b"Impresora de red"
                    )
                )

                if isinstance(
                    model,
                    bytes
                ):

                    model = model.decode(
                        "utf-8",
                        errors="ignore"
                    )

                printer = {
                    "ip": ip,
                    "model": model,
                    "type": "Red",
                    "ink": SNMPPrinter.get_ink(
                        ip
                    ),
                    "port": port
                }

                enrich_printer(printer)
                printers.append(printer)

            except Exception:
                pass

    finally:

        zc.close()

    return printers
