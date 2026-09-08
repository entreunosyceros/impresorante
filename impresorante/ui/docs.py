"""Ventana de documentación de usuario."""

import customtkinter as ctk


DOCS_TEXT = """\
CÓMO FUNCIONA IMPRESORANTE
══════════════════════════

Impresorante ayuda a encontrar impresoras (instaladas, USB y de red),
ver su estado y niveles de tinta cuando es posible, instalarlas en el
sistema y enviar una página de prueba.


USO BÁSICO
──────────

1. Revisa el prefijo de subred (ej. 192.168.1). Se rellena solo con
   la red local detectada; puedes editarlo.

2. Opcional: limita el rango de hosts (ej. 1–50) para un escaneo de
   red más rápido. Por defecto es 1–254.

3. Pulsa «Buscar». El programa busca, en este orden:
   • Impresoras ya instaladas en el sistema (CUPS / Windows)
   • Dispositivos USB visibles
   • Hosts de la subred con puertos de impresión abiertos
   • Anuncios mDNS / IPP en la red local

4. En cada ficha verás:
   • Conexión y tipo (Sistema, USB o Red)
   • Modelo
   • Estado (en reposo, imprimiendo, avisos…)
   • Consumibles (tinta/tóner), con aviso si está baja o vacía

5. Acciones disponibles en cada resultado:
   • Instalar — añade la impresora al sistema (si no es solo «Sistema»)
   • Pág. Prueba — envía un trabajo de prueba
   • Driver Oficial — abre la web de soporte del fabricante


QUÉ SÍ SE PUEDE HACER
─────────────────────

✓ Detectar impresoras instaladas en Linux (CUPS) y Windows.
✓ Detectar impresoras USB conectadas al equipo.
✓ Descubrir impresoras de red por escaneo de puertos e mDNS/IPP.
✓ Consultar modelo y, en muchos casos, tinta/tóner por SNMP (red).
✓ Leer tinta y estado por USB en algunas Canon PIXMA (p. ej. MG4200).
✓ Mostrar avisos cuando un consumible está bajo (≤ 15 %) o vacío.
✓ Refrescar estado y tinta automáticamente mientras hay resultados.
✓ Instalar colas en Linux con IPP Everywhere (lpadmin).
✓ Crear puerto TCP/IP en Windows para impresoras de red.
✓ Enviar una página de prueba (RAW 9100, CUPS/lpr o Windows).
✓ Limitar el rango de IPs a escanear para ahorrar tiempo.


QUÉ NO SE PUEDE (O TIENE LÍMITES)
─────────────────────────────────

✗ No sustituye el panel oficial del fabricante en todos los modelos.
✗ No todas las impresoras publican niveles de tinta:
    – Depende del driver (Gutenprint a menudo no los expone).
    – SNMP debe estar activo y accesible (comunidad «public»).
    – La lectura USB avanzada está enfocada a Canon compatibles;
      otras marcas pueden verse, pero sin tinta detallada.
✗ «Instalar» en Windows suele crear el puerto; el driver completo
  puede requerir el instalador del fabricante.
✗ En Linux, IPP Everywhere no garantiza la misma calidad que el
  driver propietario en todos los modelos.
✗ Si la impresora está apagada o desconectada, no habrá tinta ni
  estado en vivo.
✗ El escaneo de red completo (1–254) puede tardar y generar tráfico;
  usa un rango más pequeño si puedes.
✗ No configura Wi‑Fi de la impresora ni cambia ajustes internos
  (IP, SNMP, etc.).
✗ No gestiona colas avanzadas de CUPS (prioridad, políticas, etc.).


CONSEJOS
────────

• Para una sola impresora USB ya instalada, «Buscar» basta: verás
  la cola del sistema y el dispositivo USB unificados si es la misma.
• Si la tinta no aparece, prueba con la impresora encendida y el
  cable USB bien conectado; en red, comprueba que responda por IP.
• Tras imprimir una página de prueba, los consumibles se vuelven a
  consultar al cabo de unos segundos.


SOPORTE
───────

Proyecto: https://github.com/entreunosyceros/impresorante
Licencia: MIT — software en fase de pruebas.
"""


class DocsWindow(ctk.CTkToplevel):

    def __init__(self, parent):

        super().__init__(parent)

        self.title("Documentación — Impresorante")
        self.geometry("640x560")
        self.resizable(True, True)
        self.minsize(520, 400)
        self.transient(parent)
        self.grab_set()

        lbl_title = ctk.CTkLabel(
            self,
            text="Documentación",
            font=("Arial", 18, "bold")
        )

        lbl_title.pack(
            pady=(16, 4),
            padx=20,
            anchor="w"
        )

        lbl_sub = ctk.CTkLabel(
            self,
            text=(
                "Cómo funciona el programa, qué puedes hacer "
                "y qué limitaciones tiene."
            ),
            text_color="gray",
            wraplength=580,
            justify="left"
        )

        lbl_sub.pack(
            pady=(0, 10),
            padx=20,
            anchor="w"
        )

        self.txt_docs = ctk.CTkTextbox(
            self,
            wrap="word",
            font=("Consolas", 13),
            activate_scrollbars=True
        )

        self.txt_docs.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 10)
        )

        self.txt_docs.insert("1.0", DOCS_TEXT)
        self.txt_docs.configure(state="disabled")

        btn_close = ctk.CTkButton(
            self,
            text="Cerrar",
            fg_color="gray",
            width=120,
            command=self.destroy
        )

        btn_close.pack(
            pady=(0, 16)
        )
