"""Lectura de tinta Canon vía USB (protocolo BJL / status).

La I/O USB se ejecuta en un subproceso para que un fallo
nativo de libusb no tumbe la aplicación principal.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import json
import os
import re
import subprocess
import sys
import threading
import time
from typing import Optional


CANON_VID = 0x04A9

# PIXMA MG4200 series (confirmado: 04a9:1763)
CANON_USB_PRODUCTS = {
    0x1763: "MG4200 series",
}

_CACHE_TTL_SEC = 8.0
_cache_lock = threading.Lock()
_cache_value = None
_cache_time = 0.0


class _UsbError(RuntimeError):
    pass


def _libusb():
    path = ctypes.util.find_library("usb-1.0")

    if not path:
        raise _UsbError("libusb-1.0 no disponible")

    lib = ctypes.CDLL(path)

    lib.libusb_init.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    lib.libusb_init.restype = ctypes.c_int

    lib.libusb_exit.argtypes = [ctypes.c_void_p]
    lib.libusb_exit.restype = None

    lib.libusb_open_device_with_vid_pid.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint16,
        ctypes.c_uint16,
    ]
    lib.libusb_open_device_with_vid_pid.restype = ctypes.c_void_p

    lib.libusb_close.argtypes = [ctypes.c_void_p]
    lib.libusb_close.restype = None

    lib.libusb_kernel_driver_active.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    lib.libusb_kernel_driver_active.restype = ctypes.c_int

    lib.libusb_detach_kernel_driver.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    lib.libusb_detach_kernel_driver.restype = ctypes.c_int

    lib.libusb_attach_kernel_driver.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    lib.libusb_attach_kernel_driver.restype = ctypes.c_int

    lib.libusb_claim_interface.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    lib.libusb_claim_interface.restype = ctypes.c_int

    lib.libusb_release_interface.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    lib.libusb_release_interface.restype = ctypes.c_int

    lib.libusb_bulk_transfer.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint8,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_uint,
    ]
    lib.libusb_bulk_transfer.restype = ctypes.c_int

    lib.libusb_set_auto_detach_kernel_driver.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    lib.libusb_set_auto_detach_kernel_driver.restype = ctypes.c_int

    return lib


def _make_bjl_command(payload: bytes) -> bytes:
    header = b"\x1b[K"
    body_len = len(payload) + 4
    sep = b"\x00\x1e"
    data_len = len(payload) + 2

    return (
        header
        + bytes([body_len & 0xFF, (body_len >> 8) & 0xFF])
        + sep
        + bytes([(data_len >> 8) & 0xFF, data_len & 0xFF])
        + payload
    )


def _color_name(code: str) -> str:
    mapping = {
        "K": "Negro",
        "BK": "Negro",
        "PGBK": "Negro",
        "PBK": "Negro foto",
        "C": "Cian",
        "M": "Magenta",
        "Y": "Amarillo",
        "CL": "Color",
        "CLH": "Color",
        "BKX": "Negro",
        "GY": "Gris",
    }

    key = code.strip().upper()

    return mapping.get(key, code.strip())


def _parse_cir(response: str) -> Optional[str]:
    match = re.search(
        r"CIR:([^;]+)",
        response,
        re.IGNORECASE
    )

    if not match:
        return None

    body = match.group(1).strip()
    parts = []

    if "=" in body:
        for token in body.split(","):
            token = token.strip()

            if "=" not in token:
                continue

            name, value = token.split("=", 1)

            try:
                level = int(re.sub(r"[^\d-]", "", value))
            except Exception:
                continue

            parts.append(
                (
                    _color_name(name),
                    max(0, min(100, level)),
                    name.strip().upper(),
                )
            )

    if not parts:
        return None

    priority = {
        "BK": 0,
        "BKX": 0,
        "K": 0,
        "PGBK": 0,
        "PBK": 1,
        "CL": 2,
        "CLH": 2,
        "C": 3,
        "M": 4,
        "Y": 5,
    }

    parts.sort(
        key=lambda item: priority.get(item[2], 50)
    )

    return " | ".join(
        f"{name}: {level}%"
        for name, level, _ in parts
    )


def _parse_chd_dws_doc(response: str) -> Optional[str]:
    chd = re.search(
        r"CHD:([^;]+)",
        response,
        re.IGNORECASE
    )

    if not chd:
        cartridges = ["Negro", "Color"]
    else:
        codes = [
            c.strip()
            for c in chd.group(1).split(",")
            if c.strip()
        ]
        cartridges = [
            _color_name(c)
            for c in codes
        ] or ["Negro", "Color"]

    low = set()

    for tag in ("DWS", "DOC", "CTK"):
        match = re.search(
            rf"{tag}:([^;]+)",
            response,
            re.IGNORECASE
        )

        if not match:
            continue

        body = match.group(1).upper()

        if "LLOW" in body or "BK" in body:
            low.add("Negro")

        if "CL" in body and (
            "LLOW" in body or "EMPTY" in body
        ):
            low.add("Color")

    parts = []

    for name in cartridges:
        level = 20 if name in low else 100
        parts.append(f"{name}: {level}%")

    if parts:
        return " | ".join(parts)

    return None


def _parse_status(raw: bytes) -> Optional[str]:
    text = raw.decode("latin-1", errors="ignore")

    state_m = re.search(
        r"<ivec:status>([^<]+)</ivec:status>",
        text,
        re.IGNORECASE,
    )
    detail_m = re.search(
        r"<ivec:status_detail>([^<]*)</ivec:status_detail>",
        text,
        re.IGNORECASE,
    )

    state = (state_m.group(1).strip() if state_m else "").lower()
    detail = (detail_m.group(1).strip() if detail_m else "")

    state_map = {
        "idle": "En reposo",
        "processing": "Imprimiendo",
        "printing": "Imprimiendo",
        "stopped": "Detenida",
    }

    detail_map = {
        "MarkerSupplyAttention": "Atención consumibles",
        "MarkerSupplyEmpty": "Consumible vacío",
        "MediaEmpty": "Sin papel",
        "MediaJam": "Atasco de papel",
        "CoverOpen": "Cubierta abierta",
        "DoorOpen": "Tapa abierta",
    }

    parts = []

    if state in state_map:
        parts.append(state_map[state])
    elif state:
        parts.append(state.capitalize())

    if detail:
        parts.append(
            detail_map.get(detail, detail)
        )

    # Señales en ReadData
    if re.search(r"CTK:[^;]*LLOW", text, re.IGNORECASE):
        if "Atención consumibles" not in parts:
            parts.append("Tinta baja")

    if parts:
        return " · ".join(parts)

    return None


def _parse_response(raw: bytes) -> Optional[str]:
    text = raw.decode("latin-1", errors="ignore")

    cir = _parse_cir(text)

    if cir:
        return cir

    if "<?xml" in text.lower():
        # Preferir ReadData embebido (CIR/CHD)
        read_data = re.search(
            r"<cijn:ReadData>([^<]+)</cijn:ReadData>",
            text,
            re.IGNORECASE
        )

        if read_data:
            nested = _parse_cir(read_data.group(1))

            if nested:
                return nested

            nested = _parse_chd_dws_doc(read_data.group(1))

            if nested:
                return nested

    if any(
        tag in text.upper()
        for tag in ("CHD:", "DWS:", "DOC:", "CIL:")
    ):
        return _parse_chd_dws_doc(text)

    return None


def _bulk_io(handle, lib, write_ep, read_ep, payload, timeout_ms=2500):
    cmd = _make_bjl_command(payload)
    transferred = ctypes.c_int(0)
    buf = (ctypes.c_ubyte * len(cmd)).from_buffer_copy(cmd)

    rc = lib.libusb_bulk_transfer(
        handle,
        write_ep,
        ctypes.cast(buf, ctypes.c_void_p),
        len(cmd),
        ctypes.byref(transferred),
        timeout_ms,
    )

    if rc != 0:
        raise _UsbError(f"write failed ({rc})")

    out = bytearray()
    chunk = (ctypes.c_ubyte * 4096)()

    for _ in range(6):
        transferred = ctypes.c_int(0)

        rc = lib.libusb_bulk_transfer(
            handle,
            read_ep,
            ctypes.cast(chunk, ctypes.c_void_p),
            4096,
            ctypes.byref(transferred),
            timeout_ms,
        )

        if rc != 0 or transferred.value <= 0:
            break

        out.extend(chunk[: transferred.value])

        if _parse_response(bytes(out)):
            break

    return bytes(out)


def query_canon_usb_info_direct(
    product_id: Optional[int] = None,
) -> dict:
    """Consulta USB en el proceso actual. Devuelve {ink, status}."""

    result = {"ink": None, "status": None}

    try:
        lib = _libusb()
    except _UsbError:
        return result

    ctx = ctypes.c_void_p()

    if lib.libusb_init(ctypes.byref(ctx)) != 0:
        return result

    handle = None
    claimed = None
    detached = False

    try:
        products = (
            [product_id]
            if product_id is not None
            else list(
                dict.fromkeys(
                    list(CANON_USB_PRODUCTS)
                    + [0x1763]
                )
            )
        )

        for pid in products:
            handle = lib.libusb_open_device_with_vid_pid(
                ctx,
                CANON_VID,
                pid,
            )

            if handle:
                break

        if not handle:
            return result

        iface = 1

        try:
            lib.libusb_set_auto_detach_kernel_driver(
                handle,
                1
            )
        except Exception:
            pass

        active = lib.libusb_kernel_driver_active(
            handle,
            iface
        )

        if active == 1:
            if lib.libusb_detach_kernel_driver(handle, iface) == 0:
                detached = True

        if lib.libusb_claim_interface(handle, iface) != 0:
            return result

        claimed = iface

        payload = (
            b"SSR=BST,SFA,CHD,CIL,CIR,HRI,DBS,"
            b"DWS,DOC,DSC,DJS,CTK,HCF;"
        )

        for write_ep, read_ep in ((0x01, 0x82),):
            try:
                raw = _bulk_io(
                    handle,
                    lib,
                    write_ep,
                    read_ep,
                    payload,
                )
                result["ink"] = _parse_response(raw)
                result["status"] = _parse_status(raw)

                if result["ink"] or result["status"]:
                    return result

            except _UsbError:
                continue

        return result

    except Exception:
        return result

    finally:
        if handle and claimed is not None:
            try:
                lib.libusb_release_interface(handle, claimed)
            except Exception:
                pass

        if handle and detached:
            try:
                lib.libusb_attach_kernel_driver(handle, 1)
            except Exception:
                pass

        if handle:
            try:
                lib.libusb_close(handle)
            except Exception:
                pass

        try:
            lib.libusb_exit(ctx)
        except Exception:
            pass


def query_canon_usb_ink_direct(
    product_id: Optional[int] = None,
) -> Optional[str]:
    return query_canon_usb_info_direct(product_id).get("ink")


def query_canon_usb_info(
    product_id: Optional[int] = None,
) -> dict:
    """Consulta segura: cache breve + subproceso aislado."""

    global _cache_value, _cache_time

    now = time.monotonic()

    with _cache_lock:
        if (
            isinstance(_cache_value, dict)
            and (now - _cache_time) < _CACHE_TTL_SEC
        ):
            return dict(_cache_value)

    env = os.environ.copy()
    env["IMPRESOANTE_CANON_USB_WORKER"] = "1"

    cmd = [
        sys.executable,
        "-m",
        "impresorante.discovery.canon_usb",
    ]

    if product_id is not None:
        cmd.append(str(product_id))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=12,
            env=env,
            cwd=os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.abspath(__file__)
                    )
                )
            ),
        )

        if result.returncode != 0:
            return {"ink": None, "status": None}

        line = (result.stdout or "").strip().splitlines()

        if not line:
            return {"ink": None, "status": None}

        payload = json.loads(line[-1])
        info = {
            "ink": payload.get("ink"),
            "status": payload.get("status"),
        }

        with _cache_lock:
            _cache_value = info
            _cache_time = time.monotonic()

        return dict(info)

    except Exception:
        return {"ink": None, "status": None}


def query_canon_usb_ink(
    product_id: Optional[int] = None,
) -> Optional[str]:
    return query_canon_usb_info(product_id).get("ink")


def _looks_like_canon_usb(printer) -> bool:
    model = (printer.get("model") or "").lower()
    uri = (printer.get("uri") or printer.get("ip") or "").lower()

    looks_canon = (
        "canon" in model
        or "canon" in uri
        or "mg4200" in model
    )

    looks_usb = (
        printer.get("type") == "USB"
        or uri.startswith("usb://")
        or "usb" in str(printer.get("ip", "")).lower()
    )

    if not looks_usb and not looks_canon:
        return False

    if looks_canon and not looks_usb and "usb://" not in uri:
        if printer.get("type") == "Red":
            return False

    return True


def query_canon_usb_ink_for_printer(printer) -> Optional[str]:
    if not _looks_like_canon_usb(printer):
        return None

    return query_canon_usb_ink()


def query_canon_usb_info_for_printer(printer) -> dict:
    if not _looks_like_canon_usb(printer):
        return {"ink": None, "status": None}

    return query_canon_usb_info()


def main():
    product_id = None

    if len(sys.argv) > 1:
        try:
            product_id = int(sys.argv[1], 0)
        except Exception:
            product_id = None

    info = query_canon_usb_info_direct(product_id)
    print(json.dumps(info))


if __name__ == "__main__":
    main()
