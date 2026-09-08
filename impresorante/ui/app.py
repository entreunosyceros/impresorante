"""Aplicación principal CustomTkinter."""

import queue
import re
import threading
import urllib.parse
import webbrowser
from tkinter import Menu

import customtkinter as ctk

from impresorante.actions import install_printer, send_test_page
from impresorante.discovery import (
    deduplicate_printers,
    format_ink_with_warnings,
    get_default_subnet,
    low_ink_warnings,
    refresh_printer,
    scan_installed_printers,
    scan_mdns,
    scan_network,
    scan_usb_printers,
)
from impresorante.ui.about import AboutWindow
from impresorante.ui.docs import DocsWindow

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Intervalo de refresco de consumibles (ms)
INK_REFRESH_MS = 30000
INK_REFRESH_AFTER_PRINT_MS = 8000


class PrinterApp(ctk.CTk):

    def __init__(self):

        super().__init__()

        self.title(
            "Impresorante - Detector y conector de impresoras"
        )

        self.geometry(
            "980x700"
        )

        self.resizable(
            False,
            False
        )

        # ----------------------------------------------------
        # MENU
        # ----------------------------------------------------

        self.menu_bar = Menu(self)

        self.configure(
            menu=self.menu_bar
        )

        self.file_menu = Menu(
            self.menu_bar,
            tearoff=0
        )

        self.file_menu.add_command(
            label="Salir",
            command=self.quit
        )

        self.menu_bar.add_cascade(
            label="Archivo",
            menu=self.file_menu
        )

        self.help_menu = Menu(
            self.menu_bar,
            tearoff=0
        )

        self.help_menu.add_command(
            label="Documentación",
            command=self.open_docs_window
        )

        self.help_menu.add_command(
            label="Acerca de",
            command=self.open_about_window
        )

        self.menu_bar.add_cascade(
            label="Ayuda",
            menu=self.help_menu
        )

        # ----------------------------------------------------
        # PARTE SUPERIOR
        # ----------------------------------------------------

        self.frame_top = ctk.CTkFrame(
            self
        )

        self.frame_top.pack(
            pady=10,
            padx=20,
            fill="x"
        )

        self.lbl_subnet = ctk.CTkLabel(
            self.frame_top,
            text="Subred:"
        )

        self.lbl_subnet.pack(
            side="left",
            padx=(10, 2),
            pady=10
        )

        self.txt_subnet = ctk.CTkEntry(
            self.frame_top,
            width=110,
            placeholder_text="192.168.1"
        )

        self.txt_subnet.insert(
            0,
            get_default_subnet()
        )

        self.txt_subnet.pack(
            side="left",
            padx=5,
            pady=10
        )

        self.lbl_range = ctk.CTkLabel(
            self.frame_top,
            text="Hosts:"
        )

        self.lbl_range.pack(
            side="left",
            padx=(12, 2),
            pady=10
        )

        self.txt_host_from = ctk.CTkEntry(
            self.frame_top,
            width=48,
            placeholder_text="1"
        )

        self.txt_host_from.insert(0, "1")

        self.txt_host_from.pack(
            side="left",
            padx=2,
            pady=10
        )

        self.lbl_range_sep = ctk.CTkLabel(
            self.frame_top,
            text="-"
        )

        self.lbl_range_sep.pack(
            side="left",
            padx=2,
            pady=10
        )

        self.txt_host_to = ctk.CTkEntry(
            self.frame_top,
            width=48,
            placeholder_text="254"
        )

        self.txt_host_to.insert(0, "254")

        self.txt_host_to.pack(
            side="left",
            padx=2,
            pady=10
        )

        self.btn_scan = ctk.CTkButton(
            self.frame_top,
            text="Buscar",
            width=120,
            command=self.start_scan_thread
        )

        self.btn_scan.pack(
            side="left",
            padx=10,
            pady=10
        )

        # ----------------------------------------------------
        # PROGRESO
        # ----------------------------------------------------

        self.progress = ctk.CTkProgressBar(
            self,
            mode="indeterminate"
        )

        self.progress.pack(
            pady=5,
            padx=20,
            fill="x"
        )

        self.progress.pack_forget()

        # ----------------------------------------------------
        # RESULTADOS
        # ----------------------------------------------------

        self.lbl_results = ctk.CTkLabel(
            self,
            text="Impresoras detectadas:",
            font=("Arial", 14, "bold")
        )

        self.lbl_results.pack(
            pady=(10, 0),
            padx=20,
            anchor="w"
        )

        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            height=420
        )

        self.scroll_frame.pack(
            pady=10,
            padx=20,
            fill="both",
            expand=True
        )

        self.lbl_status = ctk.CTkLabel(
            self,
            text="Estado: listo",
            anchor="w",
            text_color="gray"
        )

        self.lbl_status.pack(
            pady=10,
            padx=20,
            fill="x"
        )

        self.found_printers = []
        self.printer_rows = []
        self._ink_refresh_job = None
        self._ink_refresh_running = False
        self._scanning = False
        self._ui_queue = queue.Queue()
        self.after(50, self._process_ui_queue)

    def call_in_ui(self, callback):
        """Encola trabajo de UI desde hilos secundarios (thread-safe)."""

        self._ui_queue.put(callback)

    def _process_ui_queue(self):

        try:
            while True:
                callback = self._ui_queue.get_nowait()

                try:
                    callback()
                except Exception:
                    pass

        except queue.Empty:
            pass

        self.after(50, self._process_ui_queue)

    # ========================================================
    # ABOUT / DOCS
    # ========================================================

    def open_about_window(self):

        AboutWindow(self)

    def open_docs_window(self):

        DocsWindow(self)

    # ========================================================
    # DRIVER
    # ========================================================

    def open_driver_url(self, model_name):

        query = urllib.parse.quote(
            model_name
        )

        model_upper = model_name.upper()

        if "HP" in model_upper or "HEWLETT" in model_upper:

            url = (
                f"https://support.hp.com/search?q={query}"
            )

        elif "EPSON" in model_upper:

            url = (
                f"https://epson.com/Support/Search?text={query}"
            )

        elif "CANON" in model_upper:

            url = (
                f"https://www.canon.com/support/search/?q={query}"
            )

        elif "BROTHER" in model_upper:

            url = (
                f"https://support.brother.com/g/b/productsearch.aspx?q={query}"
            )

        elif "KYOCERA" in model_upper:

            url = (
                f"https://www.kyoceradocumentsolutions.com/search/#gsc.q={query}"
            )

        elif "XEROX" in model_upper:

            url = (
                f"https://www.support.xerox.com/en-us/search?query={query}"
            )

        elif "RICOH" in model_upper:

            url = (
                f"https://www.ricoh.com/search?q={query}"
            )

        else:

            url = (
                f"https://www.google.com/search?q="
                f"driver+controlador+{query}"
            )

        webbrowser.open(url)

    # ========================================================
    # BÚSQUEDA TODAS
    # ========================================================

    def scan_everything(
        self,
        subnet=None,
        host_from=1,
        host_to=254,
    ):

        all_printers = []

        # ----------------------------------------------------
        # INSTALADAS
        # ----------------------------------------------------

        self.call_in_ui(
            lambda: self.lbl_status.configure(
                text="Buscando impresoras instaladas..."
            )
        )

        all_printers.extend(
            scan_installed_printers()
        )

        # ----------------------------------------------------
        # USB
        # ----------------------------------------------------

        self.call_in_ui(
            lambda: self.lbl_status.configure(
                text="Buscando impresoras USB..."
            )
        )

        all_printers.extend(
            scan_usb_printers()
        )

        # ----------------------------------------------------
        # RED
        # ----------------------------------------------------

        if subnet is None:
            subnet = ""

        subnet = subnet.strip()

        if subnet:

            self.call_in_ui(
                lambda: self.lbl_status.configure(
                    text=(
                        f"Escaneando red {subnet}."
                        f"{host_from} - {subnet}.{host_to}..."
                    )
                )
            )

            all_printers.extend(
                scan_network(
                    subnet,
                    start=host_from,
                    end=host_to,
                )
            )

        # ----------------------------------------------------
        # mDNS
        # ----------------------------------------------------

        self.call_in_ui(
            lambda: self.lbl_status.configure(
                text="Buscando anuncios mDNS/IPP..."
            )
        )

        all_printers.extend(
            scan_mdns()
        )

        self.found_printers = (
            deduplicate_printers(
                all_printers
            )
        )

        self.call_in_ui(
            self.update_gui_after_scan
        )

    # ========================================================
    # HILOS
    # ========================================================

    def start_scan_thread(self):

        subnet = self.txt_subnet.get().strip()

        try:
            host_from = int(
                self.txt_host_from.get().strip() or "1"
            )
            host_to = int(
                self.txt_host_to.get().strip() or "254"
            )
        except Exception:
            self.lbl_status.configure(
                text="Rango de hosts no válido (usa 1-254).",
                text_color="red"
            )
            return

        if not (1 <= host_from <= 254 and 1 <= host_to <= 254):
            self.lbl_status.configure(
                text="Rango de hosts fuera de 1-254.",
                text_color="red"
            )
            return

        if host_from > host_to:
            host_from, host_to = host_to, host_from
            self.txt_host_from.delete(0, "end")
            self.txt_host_from.insert(0, str(host_from))
            self.txt_host_to.delete(0, "end")
            self.txt_host_to.insert(0, str(host_to))

        if subnet and not re.match(
            r"^\d{1,3}\.\d{1,3}\.\d{1,3}$",
            subnet
        ):

            self.lbl_status.configure(
                text=(
                    "Subred no válida; se buscará "
                    "solo en sistema y USB."
                ),
                text_color="orange"
            )

            subnet = ""

        self.prepare_scan(
            "Buscando impresoras..."
        )

        threading.Thread(
            target=self.scan_everything,
            args=(subnet, host_from, host_to),
            daemon=True
        ).start()

    # ========================================================
    # GUI
    # ========================================================

    def prepare_scan(
        self,
        status_msg
    ):

        self._scanning = True
        self.stop_ink_refresh()

        for widget in (
            self.scroll_frame.winfo_children()
        ):

            widget.destroy()

        self.printer_rows = []

        self.toggle_buttons(
            False
        )

        self.progress.pack(
            pady=5,
            padx=20,
            fill="x"
        )

        self.progress.start()

        self.lbl_status.configure(
            text=status_msg,
            text_color="cyan"
        )

    def toggle_buttons(
        self,
        state
    ):

        self.btn_scan.configure(
            state=(
                "normal"
                if state
                else "disabled"
            )
        )

    def update_gui_after_scan(self):

        self.progress.stop()

        self.progress.pack_forget()

        self.toggle_buttons(
            True
        )

        self._scanning = False
        self.printer_rows = []

        if not self.found_printers:

            self.lbl_status.configure(
                text="No se encontraron impresoras.",
                text_color="orange"
            )

            self.stop_ink_refresh()
            return

        self.lbl_status.configure(
            text=(
                f"Se encontraron "
                f"{len(self.found_printers)} impresora(s)."
            ),
            text_color="green"
        )

        for printer in self.found_printers:

            item_frame = ctk.CTkFrame(
                self.scroll_frame
            )

            item_frame.pack(
                fill="x",
                pady=5,
                padx=5
            )

            printer_type = printer.get(
                "type",
                "Desconocido"
            )

            model = printer.get(
                "model",
                "Impresora"
            )

            info_text = self._printer_info_text(
                printer
            )

            lbl_info = ctk.CTkLabel(
                item_frame,
                text=info_text,
                anchor="w",
                justify="left"
            )

            lbl_info.pack(
                side="left",
                padx=10,
                pady=7,
                expand=True,
                fill="x"
            )

            self.printer_rows.append({
                "printer": printer,
                "label": lbl_info,
            })

            btn_driver = ctk.CTkButton(
                item_frame,
                text="Driver Oficial",
                width=100,
                fg_color="#d9480f",
                hover_color="#c2255c",
                command=lambda m=model:
                    self.open_driver_url(m)
            )

            btn_driver.pack(
                side="right",
                padx=5,
                pady=5
            )

            if printer_type != "Sistema":

                btn_install = ctk.CTkButton(
                    item_frame,
                    text="Instalar",
                    width=90,
                    command=lambda target=printer:
                        self.install_selected_printer(
                            target
                        )
                )

                btn_install.pack(
                    side="right",
                    padx=5,
                    pady=5
                )

            btn_test = ctk.CTkButton(
                item_frame,
                text="Pág. Prueba",
                width=90,
                fg_color="#2b8a3e",
                hover_color="#216a30",
                command=lambda target=printer:
                    self.print_test_page(
                        target
                    )
            )

            btn_test.pack(
                side="right",
                padx=5,
                pady=5
            )

        self._update_status_summary()

        self.schedule_ink_refresh(
            INK_REFRESH_MS
        )

    def _printer_info_text(self, printer):

        connection = printer.get(
            "ip",
            "Desconocida"
        )

        printer_type = printer.get(
            "type",
            "Desconocido"
        )

        model = printer.get(
            "model",
            "Impresora"
        )

        status = printer.get(
            "status",
            "Desconocido"
        )

        ink = format_ink_with_warnings(
            printer.get(
                "ink",
                "No disponible"
            )
        )

        return (
            f"Conexión: {connection} "
            f"({printer_type})\n"
            f"Modelo: {model}\n"
            f"Estado: {status}\n"
            f"Consumibles: {ink}"
        )

    def _update_status_summary(self):

        if not self.found_printers:
            return

        all_warnings = []

        for printer in self.found_printers:
            name = printer.get(
                "printer_name"
            ) or printer.get(
                "model",
                "Impresora"
            )

            for warn in low_ink_warnings(
                printer.get("ink")
            ):
                all_warnings.append(
                    f"{name}: {warn}"
                )

        count = len(self.found_printers)

        if all_warnings:
            summary = (
                f"{count} impresora(s). "
                f"⚠ Tinta baja: "
                + "; ".join(all_warnings[:3])
            )

            if len(all_warnings) > 3:
                summary += "…"

            self.lbl_status.configure(
                text=summary,
                text_color="#e67700"
            )
        else:
            self.lbl_status.configure(
                text=(
                    f"Se encontraron "
                    f"{count} impresora(s)."
                ),
                text_color="green"
            )

    def stop_ink_refresh(self):

        if self._ink_refresh_job is not None:

            try:
                self.after_cancel(
                    self._ink_refresh_job
                )
            except Exception:
                pass

            self._ink_refresh_job = None

    def schedule_ink_refresh(self, delay_ms):

        self.stop_ink_refresh()

        if not self.found_printers or self._scanning:
            return

        self._ink_refresh_job = self.after(
            delay_ms,
            self.start_ink_refresh_thread
        )

    def start_ink_refresh_thread(self):

        if (
            self._ink_refresh_running
            or self._scanning
            or not self.found_printers
        ):
            self.schedule_ink_refresh(
                INK_REFRESH_MS
            )
            return

        self._ink_refresh_running = True

        printers = list(
            self.found_printers
        )

        def task():

            for printer in printers:

                try:
                    refresh_printer(
                        printer
                    )
                except Exception:
                    pass

            self.call_in_ui(
                self.apply_ink_refresh
            )

        threading.Thread(
            target=task,
            daemon=True
        ).start()

    def apply_ink_refresh(self):

        self._ink_refresh_running = False

        if self._scanning:
            return

        for row in self.printer_rows:

            try:
                row["label"].configure(
                    text=self._printer_info_text(
                        row["printer"]
                    )
                )
            except Exception:
                pass

        self._update_status_summary()

        self.schedule_ink_refresh(
            INK_REFRESH_MS
        )

    # ========================================================
    # INSTALACIÓN
    # ========================================================

    def install_selected_printer(
        self,
        printer
    ):

        model = printer.get(
            "model",
            "Impresora"
        )

        self.lbl_status.configure(
            text=f"Instalando {model}...",
            text_color="cyan"
        )

        def run_installation():

            success, message = install_printer(
                printer
            )

            color = "green" if success else "red"

            self.call_in_ui(
                lambda: self.lbl_status.configure(
                    text=message,
                    text_color=color
                )
            )

        threading.Thread(
            target=run_installation,
            daemon=True
        ).start()

    # ========================================================
    # PÁGINA DE PRUEBA
    # ========================================================

    def print_test_page(
        self,
        printer
    ):

        p_name = printer.get(
            "printer_name",
            printer.get(
                "model",
                "Impresora"
            )
        )

        self.lbl_status.configure(
            text=(
                f"Enviando página de prueba "
                f"a {p_name}..."
            ),
            text_color="cyan"
        )

        def send_job():

            success = send_test_page(
                printer
            )

            if success:

                self.call_in_ui(
                    lambda: self.lbl_status.configure(
                        text=(
                            "Página de prueba "
                            "enviada con éxito."
                        ),
                        text_color="green"
                    )
                )

                # La tinta puede cambiar tras imprimir
                self.call_in_ui(
                    lambda: self.schedule_ink_refresh(
                        INK_REFRESH_AFTER_PRINT_MS
                    )
                )

            else:

                self.call_in_ui(
                    lambda: self.lbl_status.configure(
                        text=(
                            "No se pudo enviar "
                            "la página de prueba."
                        ),
                        text_color="red"
                    )
                )

        threading.Thread(
            target=send_job,
            daemon=True
        ).start()
