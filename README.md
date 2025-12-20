# 🟣 Chimo Converter 

Convertidor de YouTube a MP3 y MP4 con carátulas automáticas y soporte para playlists.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Estado](https://img.shields.io/badge/Estado-Terminado-success)

## Instalacion en Windows

Sigue estos pasos:

1. **Instalar Python:** Asegúrate de marcar la casilla **"Add Python to PATH"** al instalarlo.
2. **Descargar el código:** Clona este repositorio o descarga el ZIP.
3. **Instalar dependencias:** Abre la terminal en la carpeta del proyecto y ejecuta:

```bash
pip install -r requirements.txt

Hacer ejecutable en linux
python3 -m PyInstaller --noconfirm --onefile --windowed \
--add-data "icon.png:." \
--collect-all customtkinter \
--hidden-import "PIL._tkinter_finder" \
--copy-metadata "pillow" \
converterV2.py

Hacer ejecutable en windows
pyinstaller --noconsole --onefile --icon=icon.ico --add-data "icon.ico;." --add-data "icon.png;." --add-binary "ffmpeg.exe;." --add-binary "ffprobe.exe;." --collect-all customtkinter ChimoConverter.py
