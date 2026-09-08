"""Dependencias opcionales según plataforma."""

import platform

if platform.system() == "Windows":
    try:
        import win32com.client  # noqa: F401
        import win32com
    except ImportError:
        win32com = None

    try:
        import win32print
    except ImportError:
        win32print = None
else:
    win32com = None
    win32print = None


try:
    import cups
except ImportError:
    cups = None


try:
    from zeroconf import Zeroconf, ServiceBrowser
except ImportError:
    Zeroconf = None
    ServiceBrowser = None
