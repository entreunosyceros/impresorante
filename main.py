import socket
import platform
import subprocess
import threading
import webbrowser
import os
import tkinter as tk
from tkinter import Menu
import customtkinter as ctk
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

# Configuración de apariencia de la GUI
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class AboutWindow(ctk.CTkToplevel):
    """Ventana emergente 'About' con información del proyecto."""
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Acerca de Impresorante")
        self.geometry("450x480")
        self.resizable(False, False)

        # Hacer la ventana modal (bloquea la ventana principal hasta cerrarse)
        self.transient(parent)
        self.grab_set()

        # Logo de la aplicación
        logo_path = os.path.join("img", "logo.jpeg")
        if os.path.exists(logo_path):
            try:
                pil_img = Image.open(logo_path)
                logo_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(120, 120))
                lbl_logo = ctk.CTkLabel(self, image=logo_image, text="")
                lbl_logo.pack(pady=(20, 10))
            except Exception:
                pass

        # Título
        lbl_title = ctk.CTkLabel(self, text="Impresorante", font=("Arial", 20, "bold"))
        lbl_title.pack(pady=5)

        # Versión
        lbl_version = ctk.CTkLabel(self, text="Versión 1.0.0", text_color="gray")
        lbl_version.pack(pady=2)

        # Descripción
        desc_text = (
            "Detector y conector automático de impresoras en red.\n\n"
            "Permite escanear la red local (Wi-Fi / Ethernet), "
            "identificar modelos mediante SNMP/IPP y agregarlas "
            "automáticamente al sistema operativo (Windows y Linux)."
        )
        lbl_desc = ctk.CTkLabel(self, text=desc_text, wraplength=380, justify="center")
        lbl_desc.pack(pady=15, padx=20)

        # Botón a GitHub
        btn_github = ctk.CTkButton(
            self, 
            text="Ver en GitHub", 
            fg_color="#24292e", 
            hover_color="#1b1f23",
            command=self.open_github
        )
        btn_github.pack(pady=10)

        # Botón para cerrar
        btn_close = ctk.CTkButton(self, text="Cerrar", fg_color="gray", command=self.destroy)
        btn_close.pack(pady=(0, 20))

    def open_github(self):
        webbrowser.open("https://github.com/entreunosyceros/impresorante")


class PrinterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Impresorante - Detector y conector de impresoras")
        self.geometry("650x520")
        self.resizable(False, False)

        # --- Menú Superior (Tkinter Nativo) ---
        self.menu_bar = Menu(self)
        self.configure(menu=self.menu_bar)

        # Menú Archivo
        self.file_menu = Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="Salir", command=self.quit)
        self.menu_bar.add_cascade(label="Archivo", menu=self.file_menu)

        # Menú Ayuda / About
        self.help_menu = Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(label="About", command=self.open_about_window)
        self.menu_bar.add_cascade(label="Ayuda", menu=self.help_menu)

        # --- Panel Superior: Configuración de Red ---
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.pack(pady=10, padx=20, fill="x")

        self.lbl_subnet = ctk.CTkLabel(self.frame_top, text="Prefijo subred (ej. 192.168.1):")
        self.lbl_subnet.pack(side="left", padx=10, pady=10)

        self.txt_subnet = ctk.CTkEntry(self.frame_top, placeholder_text="192.168.1")
        self.txt_subnet.insert(0, "192.168.1")
        self.txt_subnet.pack(side="left", padx=10, pady=10)

        self.btn_scan = ctk.CTkButton(self.frame_top, text="Buscar impresoras", command=self.start_scan_thread)
        self.btn_scan.pack(side="right", padx=10, pady=10)

        # --- Barra de Progreso ---
        self.progress = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progress.pack(pady=5, padx=20, fill="x")
        self.progress.pack_forget()

        # --- Lista de Resultados ---
        self.lbl_results = ctk.CTkLabel(self, text="Impresoras detectadas:", font=("Arial", 14, "bold"))
        self.lbl_results.pack(pady=(10, 0), padx=20, anchor="w")

        self.scroll_frame = ctk.CTkScrollableFrame(self, height=220)
        self.scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # --- Consola de Estado ---
        self.lbl_status = ctk.CTkLabel(self, text="Estado: listo", anchor="w", text_color="gray")
        self.lbl_status.pack(pady=10, padx=20, fill="x")

        self.found_printers = []

    def open_about_window(self):
        """Abre la ventana modal 'About'."""
        AboutWindow(self)

    # -------------------------------------------------------------------------
    # LÓGICA DE RED Y SISTEMA
    # -------------------------------------------------------------------------
    def check_port(self, ip, port, timeout=0.6):
        """Comprueba si un puerto TCP está abierto."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        res = sock.connect_ex((ip, port))
        sock.close()
        return res == 0

    def get_snmp_model(self, ip):
        """Consulta el modelo de impresora mediante un paquete SNMP RAW sobre UDP."""
        snmp_request = bytes([
            0x30, 0x29, 0x02, 0x01, 0x00, 0x04, 0x06, 0x70,
            0x75, 0x62, 0x6c, 0x69, 0x63, 0xa0, 0x1c, 0x02,
            0x04, 0x00, 0x00, 0x00, 0x01, 0x02, 0x01, 0x00,
            0x02, 0x01, 0x00, 0x30, 0x0e, 0x30, 0x0c, 0x06,
            0x08, 0x2b, 0x06, 0x01, 0x02, 0x01, 0x19, 0x03,
            0x02, 0x05, 0x00
        ])
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            sock.sendto(snmp_request, (ip, 161))
            data, _ = sock.recvfrom(1024)
            sock.close()
            
            printable = "".join([chr(b) for b in data if 32 <= b <= 126])
            if "public" in printable:
                model_str = printable.split("public")[-1].strip()
                model_str = ''.join(c for c in model_str if c.isalnum() or c in ' -_/')
                if len(model_str) > 3:
                    return model_str
        except Exception:
            pass

        return "Impresora genérica / IPP"

    def scan_network(self, subnet):
        self.found_printers = []

        def check_ip(i):
            ip = f"{subnet}.{i}"
            if self.check_port(ip, 9100) or self.check_port(ip, 631):
                model = self.get_snmp_model(ip)
                return {"ip": ip, "model": model}
            return None

        with ThreadPoolExecutor(max_workers=60) as executor:
            results = executor.map(check_ip, range(1, 255))
            for res in results:
                if res:
                    self.found_printers.append(res)

        self.after(0, self.update_gui_after_scan)

    # -------------------------------------------------------------------------
    # GESTIÓN DE HILOS Y EVENTOS
    # -------------------------------------------------------------------------
    def start_scan_thread(self):
        subnet = self.txt_subnet.get().strip()
        if not subnet:
            self.lbl_status.configure(text="Error: Ingresa una subred válida.", text_color="red")
            return

        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        self.btn_scan.configure(state="disabled")
        self.progress.pack(pady=5, padx=20, fill="x")
        self.progress.start()
        self.lbl_status.configure(text=f"Escaneando {subnet}.1 - {subnet}.254...", text_color="cyan")

        threading.Thread(target=self.scan_network, args=(subnet,), daemon=True).start()

    def update_gui_after_scan(self):
        self.progress.stop()
        self.progress.pack_forget()
        self.btn_scan.configure(state="normal")

        if not self.found_printers:
            self.lbl_status.configure(text="No se encontraron impresoras en la red.", text_color="orange")
            return

        self.lbl_status.configure(text=f"Se encontraron {len(self.found_printers)} impresora(s).", text_color="green")

        for p in self.found_printers:
            item_frame = ctk.CTkFrame(self.scroll_frame)
            item_frame.pack(fill="x", pady=5, padx=5)

            info_text = f"IP: {p['ip']}  |  Modelo: {p['model']}"
            lbl_info = ctk.CTkLabel(item_frame, text=info_text, anchor="w")
            lbl_info.pack(side="left", padx=10, expand=True, fill="x")

            btn_install = ctk.CTkButton(
                item_frame, 
                text="Conectar / Instalar", 
                width=120,
                command=lambda target=p: self.install_selected_printer(target)
            )
            btn_install.pack(side="right", padx=10, pady=5)

    def install_selected_printer(self, printer):
        ip = printer['ip']
        model = printer['model']
        os_type = platform.system()

        self.lbl_status.configure(text=f"Instalando {model} ({ip})...", text_color="cyan")

        def run_installation():
            success = False
            if os_type == "Windows":
                ps_cmd = f"""
                $p = 'IP_{ip}'
                if (-not (Get-PrinterPort -Name $p -ErrorAction SilentlyContinue)) {{ Add-PrinterPort -Name $p -PrinterHostAddress '{ip}' }}
                Add-Printer -Name '{model}' -DriverName 'Generic / Text Only' -PortName $p -ErrorAction SilentlyContinue
                """
                res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
                success = (res.returncode == 0)
            elif os_type == "Linux":
                safe_name = model.replace(" ", "_")
                cmd = ["lpadmin", "-p", safe_name, "-v", f"ipp://{ip}/ipp/print", "-E", "-m", "everywhere"]
                res = subprocess.run(cmd, capture_output=True)
                success = (res.returncode == 0)

            if success:
                self.after(0, lambda: self.lbl_status.configure(
                    text=f"¡Éxito! {model} agregada al sistema.", text_color="green"
                ))
            else:
                self.after(0, lambda: self.lbl_status.configure(
                    text=f"Error al instalar {model} en el sistema.", text_color="red"
                ))

        threading.Thread(target=run_installation, daemon=True).start()

if __name__ == "__main__":
    app = PrinterApp()
    app.mainloop()