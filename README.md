# Impresorante

**Impresorante** es una aplicación multiplataforma de escritorio en Python que busca, identifica y ayuda a conectar impresoras locales (USB), instaladas en el sistema y de red (Wi‑Fi / Ethernet) en **Linux** y **Windows**.

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)

---

> Este programa está en fase de pruebas.

## Características

* **Un solo botón Buscar:** localiza impresoras instaladas, USB, de red y anuncios mDNS/IPP en un único escaneo.
* **Subred y rango de hosts:** sugiere el prefijo de red y permite limitar el escaneo (por ejemplo `1`–`50` en lugar de toda la subred).
* **Escaneo de red concurrente:** comprueba hosts en paralelo (puertos 9100 RAW, 631 IPP, 515 LPD).
* **Identificación SNMP:** consulta modelo y consumibles con SNMP v1 (comunidad `public`).
* **Estado de la impresora:** en reposo, imprimiendo, detenida, avisos de papel/tapa/consumibles (CUPS/IPP, SNMP o USB Canon).
* **Niveles de tinta / tóner:**
  * CUPS / IPP cuando el driver los publica.
  * SNMP en impresoras de red.
  * Lectura USB directa en Canon PIXMA compatibles (p. ej. MG4200), con refresco periódico en vivo.
* **Avisos de tinta baja:** destaca consumibles ≤ 15 % (o vacíos) en la ficha y en la barra de estado.
* **Página de prueba:** envía un trabajo de prueba a la impresora seleccionada.
* **Instalación asistida:**
  * **Windows:** crea puerto TCP/IP con PowerShell cuando aplica.
  * **Linux:** registra la impresora en **CUPS** con *IPP Everywhere* (`lpadmin`).
* **Interfaz gráfica:** `CustomTkinter` (tema claro/oscuro del sistema).

---

## Requisitos previos

* **Python 3.8** o superior.
* Dependencias de Python: `customtkinter`, `pillow`, `zeroconf` (y `pywin32` en Windows).
* En Linux, para imprimir/instalar: CUPS (`lpadmin`, `lpr`, etc.).
* En Linux, lectura de tinta Canon USB: `libusb-1.0` (habitualmente ya instalado).

---

## Instalación

1. **Clonar el repositorio:**

   ```bash
   git clone https://github.com/entreunosyceros/impresorante.git
   cd impresorante
   ```

2. **Inicio rápido** (crea el entorno virtual e instala dependencias):

   ```bash
   # Linux
   python3 run_app.py

   # Windows
   python run_app.py
   ```

3. **Inicio manual** (alternativa):

   ```bash
   # Linux
   python3 -m venv .venv
   source .venv/bin/activate

   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   pip install -r requirements.txt
   python main.py
   ```

---

## Uso

```bash
python main.py
```

Dentro de la aplicación:

1. Revisa o ajusta el prefijo de subred (ej. `192.168.1`).
2. Opcional: limita el rango de hosts (ej. `1`–`50`) para un escaneo más rápido.
3. Pulsa **Buscar**.
4. En cada ficha verás conexión, modelo, **estado** y **consumibles** (con aviso si la tinta está baja).
5. Usa **Instalar**, **Pág. Prueba** o **Driver Oficial** según necesites.
6. Estado y tinta se refrescan solos mientras haya resultados visibles.

Más detalle (qué se puede y qué no): menú **Ayuda → Documentación**.

---

## Estructura del proyecto

```text
ImpresorANTE/
├── img/
│   └── logo.jpeg
├── impresorante/
│   ├── deps.py              # Dependencias opcionales (win32, cups, zeroconf)
│   ├── snmp.py              # SNMP / Printer-MIB
│   ├── discovery/           # Escaneo, tinta, estado, rango de red
│   ├── actions/             # Instalar / página de prueba
│   └── ui/                  # CustomTkinter (app + About)
├── main.py                  # Punto de entrada
├── run_app.py               # Lanzador (venv + dependencias)
├── requirements.txt
└── README.md
```

---

## Dependencias (`requirements.txt`)

```text
customtkinter
zeroconf
pillow
pywin32; sys_platform == 'win32'
```

---

## Contribuciones

Las contribuciones, issues y solicitudes de funciones son bienvenidas. Siéntete libre de revisar la página de issues si deseas colaborar.

## Licencia

Este proyecto está bajo la Licencia MIT.
