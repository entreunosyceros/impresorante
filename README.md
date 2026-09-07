# ImpresoraNTE 🖨️

**ImpresoraNTE** es una aplicación multiplataforma de escritorio desarrollada en Python que automatiza la búsqueda, conexión y configuración de impresoras en redes locales (Wi-Fi y Ethernet) para sistemas **Linux** y **Windows**.

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)

---

>Este programa está en fase pruebas ...

## Características

* **Escaneo rápido:** Detecta impresoras en toda la subred local mediante procesamiento concurrente en pocos segundos.
* **Consulta de información:** Identifica el modelo exacto de la impresora consultando el puerto **161 (SNMP)** y comprobando los servicios de impresión **9100 (RAW)** y **631 (IPP)**.
* **Instalación automática multiplataforma:**
  * **Windows:** Añade el puerto TCP/IP y registra la impresora usando PowerShell.
  * **Linux:** Registra la impresora directamente en **CUPS** haciendo uso del estándar universal *IPP Everywhere* (impresión sin necesidad de controladores adicionales).
* **Sin dependencias complejas de red:** Implementación nativa sobre *Sockets* para el envío de paquetes SNMP sin librerías propensas a errores de versión.
* **Interfaz gráfica:** Desarrollada con `CustomTkinter`, compatible con modo claro y oscuro del sistema operativo.

---

## Requisitos previos

* **Python 3.8** o superior.
* Para la interfaz gráfica e imágenes: `customtkinter` y `pillow`.

---

## 📦 Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/entreunosyceros/impresorante.git](https://github.com/entreunosyceros/impresorante.git)
   cd impresorante
   ```
2. **Inicio rápido:**
    Se puede iniciar de forma rápida este programa ejecutando el script run_app:
    ```bash
    python3 run_app.py
    ```
    En Windows sería algo así:
    ```bash
    python run_app.py
    ```

    Esta ejecución debería crear y activar el entorno virtual e instalar en el todas las dependencias necesario que vienen definidas en el archivo requirements.txt. 

    **Inicio manual:**
    Si prefieres realizar el inicio manual basta con seguir las siguientes instrucciones:
    ```bash
    # Linux
    python3 -m venv .venv
    source .venv/bin/activate

    # Windows
    python -m venv .venv
    .venv\Scripts\activate
    ```

    Después basta con instalar las dependencias:

    ```bash
    pip install -r requirements.txt
    ```

## 🖥️ Uso

Para iniciar la aplicación, no hay más que escribir:

```Bash
python main.py
```
Pasos dentro de la aplicación:

    Introduce el prefijo de tu subred local (ej. 192.168.1).

    Haz clic en Buscar impresoras.

    Selecciona la impresora detectada en la lista y pulsa Conectar / Instalar.


## 📂 Estructura del Proyecto
```Plaintext

impresorante/
├── img/
│   └── logo.jpeg          # Logo de la aplicación
├── main.py                # Código fuente principal de la aplicación
├── requirements.txt       # Lista de dependencias
└── README.md              # Documentación del proyecto
```

## 📄 Contenido de requirements.txt
```Plaintext
customtkinter
pillow
zeroconf
```

## Contribuciones

Las contribuciones, issues y solicitudes de funciones son bienvenidas. Siéntete libre de revisar la página de issues si deseas colaborar.

## Licencia

Este proyecto está bajo la Licencia MIT.