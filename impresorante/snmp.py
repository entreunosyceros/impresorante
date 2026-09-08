"""Utilidades SNMP y consulta de Printer-MIB."""

import os
import socket


def ber_length(length):
    if length < 128:
        return bytes([length])

    data = length.to_bytes(
        (length.bit_length() + 7) // 8,
        "big"
    )

    return bytes([0x80 | len(data)]) + data


def ber_encode_integer(value):
    if value == 0:
        return b"\x02\x01\x00"

    negative = value < 0

    if negative:
        value = (1 << 32) + value

    data = value.to_bytes(
        max(1, (value.bit_length() + 7) // 8),
        "big"
    )

    if not negative and data[0] & 0x80:
        data = b"\x00" + data

    return b"\x02" + ber_length(len(data)) + data


def ber_encode_oid(oid):
    parts = [int(x) for x in oid.split(".")]

    if len(parts) < 2:
        raise ValueError("OID inválido")

    encoded = bytes([
        40 * parts[0] + parts[1]
    ])

    for value in parts[2:]:
        chunks = [value & 0x7F]
        value >>= 7

        while value:
            chunks.insert(0, 0x80 | (value & 0x7F))
            value >>= 7

        for i in range(len(chunks) - 1):
            chunks[i] |= 0x80

        encoded += bytes(chunks)

    return b"\x06" + ber_length(len(encoded)) + encoded


def ber_encode_null():
    return b"\x05\x00"


def ber_encode_octet_string(value):
    if isinstance(value, str):
        value = value.encode("utf-8")

    return b"\x04" + ber_length(len(value)) + value


def build_snmp_get_request(request_id, oid):
    variable = (
        ber_encode_oid(oid) +
        ber_encode_null()
    )

    varbind = (
        b"\x30" +
        ber_length(len(variable)) +
        variable
    )

    varbind_list = (
        b"\x30" +
        ber_length(len(varbind)) +
        varbind
    )

    pdu_body = (
        ber_encode_integer(request_id) +
        ber_encode_integer(0) +
        ber_encode_integer(0) +
        varbind_list
    )

    pdu = (
        b"\xa0" +
        ber_length(len(pdu_body)) +
        pdu_body
    )

    community = ber_encode_octet_string("public")

    message_body = (
        ber_encode_integer(0) +
        community +
        pdu
    )

    return (
        b"\x30" +
        ber_length(len(message_body)) +
        message_body
    )


def ber_read_length(data, pos):
    first = data[pos]
    pos += 1

    if first < 128:
        return first, pos

    count = first & 0x7F

    if count == 0:
        raise ValueError("BER indefinido no soportado")

    length = int.from_bytes(
        data[pos:pos + count],
        "big"
    )

    return length, pos + count


def ber_read_tlv(data, pos=0):
    tag = data[pos]
    pos += 1

    length, pos = ber_read_length(data, pos)

    value = data[pos:pos + length]
    pos += length

    return tag, value, pos


def ber_decode_oid(data):
    if not data:
        return ""

    first = data[0]

    if first >= 80:
        first_part = 2
        second_part = first - 80
    else:
        first_part = first // 40
        second_part = first % 40

    parts = [first_part, second_part]
    value = 0

    for byte in data[1:]:
        value = (value << 7) | (byte & 0x7F)

        if not byte & 0x80:
            parts.append(value)
            value = 0

    return ".".join(map(str, parts))


def parse_snmp_response(data):
    """
    Devuelve una lista de:
        (oid, tag, value)
    """

    results = []

    try:
        tag, message, _ = ber_read_tlv(data, 0)

        if tag != 0x30:
            return results

        pos = 0

        # versión
        _, _, pos = ber_read_tlv(message, pos)

        # comunidad
        _, _, pos = ber_read_tlv(message, pos)

        # PDU
        _, pdu, pos = ber_read_tlv(message, pos)

        p = 0

        # request-id
        _, _, p = ber_read_tlv(pdu, p)

        # error-status
        _, _, p = ber_read_tlv(pdu, p)

        # error-index
        _, _, p = ber_read_tlv(pdu, p)

        # lista de variables
        _, varbinds, p = ber_read_tlv(pdu, p)

        vp = 0

        while vp < len(varbinds):
            _, varbind, vp = ber_read_tlv(varbinds, vp)

            bp = 0

            oid_tag, oid_data, bp = ber_read_tlv(varbind, bp)

            if oid_tag != 0x06:
                continue

            oid = ber_decode_oid(oid_data)

            value_tag, value_data, bp = ber_read_tlv(
                varbind,
                bp
            )

            results.append(
                (
                    oid,
                    value_tag,
                    value_data
                )
            )

    except Exception:
        return []

    return results


def snmp_query(ip, oid, timeout=0.8):
    """
    Consulta SNMP v1 usando comunidad 'public'.
    """

    request_id = os.getpid() & 0x7FFFFFFF

    packet = build_snmp_get_request(
        request_id,
        oid
    )

    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    sock.settimeout(timeout)

    try:
        sock.sendto(
            packet,
            (ip, 161)
        )

        data, _ = sock.recvfrom(8192)

        results = parse_snmp_response(data)

        if results:
            return results[0][2], results[0][1]

    except Exception:
        pass

    finally:
        sock.close()

    return None, None


# ============================================================
# CONSULTA DE PRINTER-MIB
# ============================================================

class SNMPPrinter:

    # Printer-MIB
    MARKER_SUPPLIES_DESCRIPTION = "1.3.6.1.2.1.43.11.1.1.6"
    MARKER_SUPPLIES_CLASS = "1.3.6.1.2.1.43.11.1.1.5"
    MARKER_SUPPLIES_TYPE = "1.3.6.1.2.1.43.11.1.1.3"
    MARKER_SUPPLIES_MAX = "1.3.6.1.2.1.43.11.1.1.8"
    MARKER_SUPPLIES_LEVEL = "1.3.6.1.2.1.43.11.1.1.9"

    # HOST-RESOURCES-MIB
    DEVICE_DESCRIPTION = "1.3.6.1.2.1.25.3.2.1.3"

    @staticmethod
    def decode_value(tag, data):

        # INTEGER
        if tag == 0x02:
            if not data:
                return 0

            return int.from_bytes(
                data,
                "big",
                signed=True
            )

        # OCTET STRING
        if tag == 0x04:
            try:
                return data.decode(
                    "utf-8",
                    errors="ignore"
                ).strip()
            except Exception:
                return ""

        # OBJECT IDENTIFIER
        if tag == 0x06:
            return ber_decode_oid(data)

        return data

    @classmethod
    def get_model(cls, ip):

        value, tag = snmp_query(
            ip,
            cls.DEVICE_DESCRIPTION
        )

        if value is not None:

            decoded = cls.decode_value(
                tag,
                value
            )

            if isinstance(decoded, str):
                decoded = decoded.strip()

                if len(decoded) > 2:
                    return decoded

        return "Impresora de red"

    @classmethod
    def _supply_indexes(cls):
        """
        Índices habituales de Printer-MIB.

        Muchas impresoras (Canon incluidas) usan
        hrDeviceIndex.prtMarkerSuppliesIndex → 1.1, 1.2...
        en lugar de un único entero.
        """

        indexes = [
            str(i)
            for i in range(1, 20)
        ]

        for device in (1, 0):
            for supply in range(1, 16):
                indexes.append(
                    f"{device}.{supply}"
                )

        return indexes

    @classmethod
    def get_ink(cls, ip):

        descriptions = []
        levels = []
        maximums = []

        # ----------------------------------------------------
        # Intentamos consultar varios índices.
        # ----------------------------------------------------

        for index in cls._supply_indexes():

            oid_desc = (
                f"{cls.MARKER_SUPPLIES_DESCRIPTION}.{index}"
            )
            oid_level = (
                f"{cls.MARKER_SUPPLIES_LEVEL}.{index}"
            )
            oid_max = (
                f"{cls.MARKER_SUPPLIES_MAX}.{index}"
            )

            desc_value, desc_tag = snmp_query(
                ip,
                oid_desc,
                timeout=0.35
            )

            level_value, level_tag = snmp_query(
                ip,
                oid_level,
                timeout=0.35
            )

            max_value, max_tag = snmp_query(
                ip,
                oid_max,
                timeout=0.35
            )

            if desc_value is None and level_value is None:
                continue

            description = ""

            if desc_value is not None:
                description = cls.decode_value(
                    desc_tag,
                    desc_value
                )

            level = None
            maximum = None

            if level_value is not None:
                level = cls.decode_value(
                    level_tag,
                    level_value
                )

            if max_value is not None:
                maximum = cls.decode_value(
                    max_tag,
                    max_value
                )

            descriptions.append(
                description or f"Consumible {index}"
            )

            levels.append(level)
            maximums.append(maximum)

        result = []

        for i, level in enumerate(levels):

            name = descriptions[i]

            maximum = maximums[i]

            try:

                level = int(level)

                # Valores especiales RFC 3805:
                # -1 other, -2 unknown, -3 some remaining
                if level < 0:
                    continue

                if maximum and int(maximum) > 0:

                    maximum = int(maximum)

                    percent = int(
                        (level / maximum) * 100
                    )

                    percent = max(
                        0,
                        min(100, percent)
                    )

                    result.append(
                        f"{name}: {percent}%"
                    )

                elif level >= 0:

                    # Algunas impresoras ya devuelven
                    # directamente el porcentaje.

                    if level <= 100:

                        result.append(
                            f"{name}: {level}%"
                        )

                    else:

                        result.append(
                            f"{name}: {level}"
                        )

            except Exception:
                pass

        if result:
            return " | ".join(result)

        return "No disponible"
