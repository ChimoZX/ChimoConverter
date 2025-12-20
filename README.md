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

pyinstaller --onefile --noconsole --name="chimo converter" --icon=ico.ico converter.py

pyinstaller --noconsole --onefile --icon=ico.ico --add-binary "ffmpeg.exe;." --collect-all customtkinter converter.py
