"""Ventana Acerca de."""

import os
import webbrowser

import customtkinter as ctk
from PIL import Image


class AboutWindow(ctk.CTkToplevel):

    def __init__(self, parent):

        super().__init__(parent)

        self.title("Acerca de Impresorante")
        self.geometry("480x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        logo_path = os.path.join(
            "img",
            "logo.jpeg"
        )

        if os.path.exists(logo_path):

            try:

                pil_img = Image.open(
                    logo_path
                )

                # Logo panorámico: mantener proporción
                max_width = 360
                src_w, src_h = pil_img.size
                disp_w = max_width
                disp_h = max(
                    1,
                    int(src_h * (disp_w / src_w))
                )

                logo_image = ctk.CTkImage(
                    light_image=pil_img,
                    dark_image=pil_img,
                    size=(disp_w, disp_h)
                )

                lbl_logo = ctk.CTkLabel(
                    self,
                    image=logo_image,
                    text=""
                )

                lbl_logo.pack(
                    pady=(20, 10)
                )

            except Exception:
                pass

        lbl_title = ctk.CTkLabel(
            self,
            text="Impresorante",
            font=("Arial", 20, "bold")
        )

        lbl_title.pack(pady=5)

        lbl_version = ctk.CTkLabel(
            self,
            text="Versión 2.0.0 — Detección multiplataforma",
            text_color="gray"
        )

        lbl_version.pack(pady=2)

        desc_text = (
            "Detector y conector automático de impresoras.\n\n"
            "Detecta impresoras instaladas, USB y de red "
            "en Windows y Linux.\n\n"
            "También intenta consultar los niveles de "
            "tinta o tóner mediante CUPS, IPP y SNMP."
        )

        lbl_desc = ctk.CTkLabel(
            self,
            text=desc_text,
            wraplength=380,
            justify="center"
        )

        lbl_desc.pack(
            pady=15,
            padx=20
        )

        btn_github = ctk.CTkButton(
            self,
            text="Ver en GitHub",
            fg_color="#24292e",
            hover_color="#1b1f23",
            command=self.open_github
        )

        btn_github.pack(pady=10)

        btn_close = ctk.CTkButton(
            self,
            text="Cerrar",
            fg_color="gray",
            command=self.destroy
        )

        btn_close.pack(
            pady=(0, 20)
        )

    def open_github(self):

        webbrowser.open(
            "https://github.com/entreunosyceros/impresorante"
        )
