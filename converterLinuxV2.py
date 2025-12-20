import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import requests
from io import BytesIO
import yt_dlp
import threading
import os
import sys
import json
import re
import time
import subprocess

# --- CONFIGURACIÓN VISUAL ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# --- DETECCIÓN DE SISTEMA OPERATIVO ---
ES_WINDOWS = os.name == 'nt'

# --- FIX: ESCALADO DE WINDOWS (DPI AWARENESS) ---
if ES_WINDOWS:
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

ctk.set_widget_scaling(1.0)
ctk.set_window_scaling(1.0)

# PALETA DE COLORES
COLOR_FONDO = "#080808"
COLOR_FRAME = "#1c1c1c"
COLOR_INPUT = "#2b2b2b"
COLOR_MORADO = "#7c4dff"
COLOR_MORADO_HOVER = "#651fff"
COLOR_TEXTO = "#e0e0e0"
COLOR_EXITO = "#00e676"
COLOR_ERROR = "#ff1744"
COLOR_ROJO = "#d50000"
COLOR_ROJO_HOVER = "#ff1744"

ARCHIVO_CONFIG = "config.json"

# HEADER "ANTI-BOT"
HEADERS_NAVEGADOR = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def obtener_configuracion_ffmpeg():
    if not ES_WINDOWS:
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return None
        except FileNotFoundError:
            pass

    nombre_archivo = "ffmpeg.exe" if ES_WINDOWS else "ffmpeg"
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    ruta_completa = os.path.join(base_path, nombre_archivo)
    return ruta_completa if os.path.exists(ruta_completa) else None

class NeonConverter(ctk.CTk):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.title("Chimo Converter")
        self.geometry("850x800")
        self.resizable(True, True)
        self.configure(fg_color=COLOR_FONDO)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.ruta_var = ctk.StringVar(value=self.cargar_ruta_guardada())
        self.playlist_mode = ctk.BooleanVar(value=False)
        self.imagen_actual = None
        self.cancelar_flag = False
        self.archivos_rastreados = set()

        # FIX ANTI-CRASH IMAGEN
        img_transparente = Image.new("RGBA", (400, 225), (0, 0, 0, 0))
        self.img_vacia = ctk.CTkImage(light_image=img_transparente, dark_image=img_transparente, size=(400, 225))

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                                   scrollbar_button_color=COLOR_FRAME,
                                                   scrollbar_button_hover_color=COLOR_MORADO)
        self.scroll_frame.pack(fill="both", expand=True)

        self.crear_interfaz()

    def on_closing(self):
        self.withdraw()
        self.cancelar_flag = True
        self.limpiar_basura(al_cerrar=True)
        os._exit(0)

    def cargar_ruta_guardada(self):
        if os.path.exists(ARCHIVO_CONFIG):
            try:
                with open(ARCHIVO_CONFIG, "r") as f:
                    data = json.load(f)
                    ruta = data.get("ruta_descarga", "")
                    if os.path.exists(ruta): return ruta
            except: pass
        return os.getcwd()

    def guardar_ruta(self, ruta):
        try:
            with open(ARCHIVO_CONFIG, "w") as f:
                json.dump({"ruta_descarga": ruta}, f)
        except: pass

    def crear_popup(self, titulo, mensaje, es_error=False):
        popup = ctk.CTkToplevel(self)
        popup.title(titulo)
        popup.geometry("400x250")
        popup.resizable(False, False)
        popup.configure(fg_color=COLOR_FRAME)
        popup.transient(self)

        try:
            popup.update_idletasks()
            x = self.winfo_x() + (self.winfo_width() // 2) - (popup.winfo_width() // 2)
            y = self.winfo_y() + (self.winfo_height() // 2) - (popup.winfo_height() // 2)
            popup.geometry(f"+{x}+{y}")
        except: pass

        color_icono = COLOR_ERROR if es_error else COLOR_EXITO
        lbl_icono = ctk.CTkLabel(popup, text="!", font=("Arial Black", 30),
                                 text_color=color_icono, fg_color="transparent")
        lbl_icono.pack(pady=(20, 5))

        ctk.CTkLabel(popup, text=titulo.upper(), font=("Arial Black", 18, "bold"), text_color="white").pack()
        ctk.CTkLabel(popup, text=mensaje, font=("Segoe UI", 12), text_color="gray", wraplength=350).pack(pady=10)

        ctk.CTkButton(popup, text="ENTENDIDO", command=popup.destroy,
                      fg_color=COLOR_MORADO, hover_color=COLOR_MORADO_HOVER,
                      width=150, corner_radius=20).pack(pady=20)

        popup.grab_set()
        popup.focus_force()

    def borrar_url(self):
        self.entry_url.delete(0, 'end')
        self.lbl_imagen.configure(image=self.img_vacia, text="")
        self.lbl_titulo.configure(text="Esperando video...")
        self.combo_calidad.configure(values=["(Analiza primero)"])
        self.combo_calidad.set("(Analiza primero)")
        self.imagen_actual = None

    def accion_cancelar(self):
        self.cancelar_flag = True
        self.lbl_estado.configure(text="🛑 DETENIENDO Y LIMPIANDO...", text_color=COLOR_ERROR)
        self.btn_cancelar.configure(state="disabled")

    def crear_interfaz(self):
        # HEADER
        self.frame_top = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.frame_top.pack(pady=(15, 5))
        fuente_titulo = ("Arial Black", 36, "bold")
        ctk.CTkLabel(self.frame_top, text="CHIMO", font=fuente_titulo, text_color="white").pack(side="left")
        ctk.CTkLabel(self.frame_top, text=" CONVERTER", font=fuente_titulo, text_color=COLOR_MORADO).pack(side="left")

        # INPUT
        self.frame_input = ctk.CTkFrame(self.scroll_frame, fg_color=COLOR_FRAME, corner_radius=20)
        self.frame_input.pack(pady=10, padx=20, fill="x")

        self.entry_url = ctk.CTkEntry(self.frame_input, placeholder_text="Pega el enlace del video aquí...",
                                      height=45, border_width=0, corner_radius=15,
                                      fg_color=COLOR_INPUT, text_color="white", font=("Segoe UI", 13))
        self.entry_url.pack(side="left", fill="x", expand=True, padx=(15, 5), pady=15)

        self.btn_borrar = ctk.CTkButton(self.frame_input, text="✕", command=self.borrar_url,
                                        width=40, height=45, corner_radius=10,
                                        fg_color="#333", hover_color=COLOR_ROJO_HOVER, font=("Arial", 14, "bold"))
        self.btn_borrar.pack(side="left", padx=(0, 10), pady=15)

        self.btn_analizar = ctk.CTkButton(self.frame_input, text="ANALIZAR", command=self.hilo_analizar,
                                          fg_color=COLOR_MORADO, hover_color=COLOR_MORADO_HOVER,
                                          width=100, height=45, corner_radius=15, font=("Arial", 12, "bold"))
        self.btn_analizar.pack(side="right", padx=(0, 15), pady=15)

        # PREVIEW
        self.frame_preview = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.frame_preview.pack(pady=0)
        self.lbl_imagen = ctk.CTkLabel(self.frame_preview, text="", image=self.img_vacia, width=400, height=225, fg_color="#111", corner_radius=15)
        self.lbl_imagen.pack()
        self.lbl_titulo = ctk.CTkLabel(self.frame_preview, text="Esperando video...", font=("Segoe UI", 13), text_color="gray")
        self.lbl_titulo.pack(pady=5)

        # TABS
        self.tabview = ctk.CTkTabview(self.scroll_frame, width=600, height=150,
                                      fg_color=COLOR_FRAME, corner_radius=20,
                                      segmented_button_fg_color=COLOR_INPUT,
                                      segmented_button_selected_color=COLOR_MORADO,
                                      segmented_button_unselected_color=COLOR_INPUT,
                                      text_color="white")
        self.tabview.pack(pady=5)

        self.tab_video = self.tabview.add("Video MP4")
        self.tab_audio = self.tabview.add("Audio MP3")

        self.combo_calidad = ctk.CTkComboBox(self.tab_video, values=["(Analiza primero)"], width=280, height=30, corner_radius=15,
                                             fg_color=COLOR_INPUT, button_color=COLOR_MORADO, border_color=COLOR_INPUT)
        self.combo_calidad.pack(pady=5)
        self.switch_playlist = ctk.CTkSwitch(self.tab_video, text="Descargar Playlist Completa", variable=self.playlist_mode,
                                             progress_color=COLOR_MORADO, button_color="white")
        self.switch_playlist.pack(pady=5)

        ctk.CTkLabel(self.tab_audio, text="Calidad de Audio:", font=("Segoe UI", 11)).pack(pady=2)
        self.combo_audio = ctk.CTkComboBox(self.tab_audio, values=["320 kbps (Alta)", "192 kbps (Media)", "128 kbps (Baja)"],
                                           width=280, height=30, corner_radius=15,
                                           fg_color=COLOR_INPUT, button_color=COLOR_MORADO, border_color=COLOR_INPUT)
        self.combo_audio.set("192 kbps (Media)")
        self.combo_audio.pack(pady=5)
        self.switch_playlist_audio = ctk.CTkSwitch(self.tab_audio, text="Descargar Playlist Completa", variable=self.playlist_mode,
                                                   progress_color=COLOR_MORADO, button_color="white")
        self.switch_playlist_audio.pack(pady=5)

        # CARPETA
        self.frame_ruta = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.frame_ruta.pack(fill="x", padx=60, pady=(5, 5))
        self.entry_ruta = ctk.CTkEntry(self.frame_ruta, textvariable=self.ruta_var, state="disabled",
                                       fg_color=COLOR_FRAME, border_width=0, corner_radius=10, height=35)
        self.entry_ruta.pack(side="left", fill="x", expand=True, padx=(0,10))
        ctk.CTkButton(self.frame_ruta, text="SELECCIONAR CARPETA", width=160, height=35, command=self.seleccionar_carpeta,
                      fg_color=COLOR_INPUT, hover_color="#444", corner_radius=10, font=("Segoe UI", 11, "bold")).pack(side="left")

        # ZONA DESCARGA
        self.progress_bar = ctk.CTkProgressBar(self.scroll_frame, width=500, progress_color=COLOR_MORADO, fg_color=COLOR_INPUT, height=12)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(0, 2))
        self.lbl_estado = ctk.CTkLabel(self.scroll_frame, text="Listo para descargar", text_color="gray", font=("Segoe UI", 11))
        self.lbl_estado.pack(pady=(0, 10))

        # BOTONES
        self.frame_botones = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.frame_botones.pack(pady=(0, 30))
        self.btn_descargar = ctk.CTkButton(self.frame_botones, text="DESCARGAR ARCHIVO", command=self.hilo_descargar,
                                           width=300, height=60, fg_color=COLOR_MORADO, hover_color=COLOR_MORADO_HOVER,
                                           font=("Arial Black", 18, "bold"), corner_radius=30)
        self.btn_descargar.pack(side="left", padx=10)
        self.btn_cancelar = ctk.CTkButton(self.frame_botones, text="CANCELAR", command=self.accion_cancelar,
                                          width=120, height=60, state="disabled", fg_color=COLOR_ROJO, hover_color=COLOR_ROJO_HOVER,
                                          font=("Arial Black", 12, "bold"), corner_radius=30)
        self.btn_cancelar.pack(side="left", padx=10)

    # --- LÓGICA ---
    def seleccionar_carpeta(self):
        ruta = filedialog.askdirectory()
        if ruta:
            self.ruta_var.set(ruta)
            self.guardar_ruta(ruta)

    def hilo_analizar(self):
        url = self.entry_url.get().strip()
        if not url: return
        self.btn_analizar.configure(state="disabled")
        self.lbl_titulo.configure(text="Buscando información...")

        # Limpieza visual segura (imagen invisible)
        try: self.lbl_imagen.configure(image=self.img_vacia, text="")
        except: pass
        self.imagen_actual = None

        threading.Thread(target=self.analizar_video, args=(url,), daemon=True).start()

    def analizar_video(self, url):
        try:
            if not url.startswith("http"):
                url = f"ytsearch1:{url}"
                es_busqueda = True
            else:
                es_busqueda = False

            ydl_opts = {
                'quiet': True, 'noplaylist': True, 'extract_flat': False,
                'http_headers': HEADERS_NAVEGADOR
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info: info = info['entries'][0]

                # Info prioritaria
                titulo = info.get('title', 'Video sin título')
                prefijo = "Resultado: " if es_busqueda else ""
                self.after(0, lambda: self.lbl_titulo.configure(text=f"{prefijo}{titulo[:60]}..."))

                # Calidades
                formatos = set()
                if 'formats' in info:
                    for f in info['formats']:
                        if f.get('height') and f.get('vcodec') != 'none':
                            formatos.add(f['height'])

                lista_c = sorted(list(formatos), reverse=True)
                lista_f = [f"{res}p" for res in lista_c]
                lista_f.insert(0, "Mejor Calidad (Auto)")
                if not lista_f: lista_f = ["Mejor Calidad (Auto)"]

                self.after(0, lambda: self.combo_calidad.configure(values=lista_f))
                self.after(0, lambda: self.combo_calidad.set("Mejor Calidad (Auto)"))

                # Imagen secundaria
                thumb_url = info.get('thumbnail')
                if thumb_url:
                    try:
                        resp = requests.get(thumb_url, headers=HEADERS_NAVEGADOR, timeout=3)
                        if resp.status_code == 200:
                            img_data = Image.open(BytesIO(resp.content))
                            img_data = img_data.resize((400, 225), Image.Resampling.LANCZOS)
                            nueva_img = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(400, 225))
                            self.imagen_actual = nueva_img
                            self.after(0, lambda: self.lbl_imagen.configure(image=self.imagen_actual, text=""))
                    except:
                        self.after(0, lambda: self.lbl_imagen.configure(image=self.img_vacia, text="🎵 Sin vista previa"))

        except Exception as e:
            self.after(0, lambda: self.lbl_titulo.configure(text="❌ Error en enlace"))
        finally:
            self.after(0, lambda: self.btn_analizar.configure(state="normal"))

    def hilo_descargar(self):
        url = self.entry_url.get().strip()
        if not url:
            self.crear_popup("Ups...", "Pega un enlace.", es_error=True)
            return

        self.cancelar_flag = False
        self.archivos_rastreados.clear()
        self.btn_descargar.configure(state="disabled", text="INICIANDO...")
        self.btn_cancelar.configure(state="normal")
        self.progress_bar.set(0)
        threading.Thread(target=self.proceso_descarga, daemon=True).start()

    def filtro_cancelacion(self, info_dict, *, incomplete):
        if self.cancelar_flag: return "Descarga cancelada"
        return None

    def hook_progreso(self, d):
        if self.cancelar_flag: raise Exception("CANCELADO_POR_USUARIO")
        f = d.get('filename')
        if f: self.archivos_rastreados.add(f)

        if d['status'] == 'downloading':
            try:
                p = float(re.sub(r'\x1b\[[0-9;]*m', '', d.get('_percent_str', '0%')).replace('%',''))
                self.progress_bar.set(p / 100)
                msg = f"Bajando: {p:.1f}% | {d.get('_speed_str', '')}"
                self.lbl_estado.configure(text=msg, text_color=COLOR_MORADO)
            except: pass
        elif d['status'] == 'finished':
            self.lbl_estado.configure(text="Convirtiendo...", text_color="white")

    def limpiar_basura(self, al_cerrar=False):
        if not al_cerrar: time.sleep(1.5)

        if ES_WINDOWS:
            try: subprocess.Popen(['taskkill', '/F', '/IM', 'ffmpeg.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except: pass
        else:
            try: subprocess.Popen(['pkill', '-9', 'ffmpeg'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except: pass

        if al_cerrar: return

        extensiones_b = ['.part', '.ytdl', '.webp', '.jpg', '.jpeg', '.png', '.info.json', '.f401', '.f251', '.f137']
        for r in list(self.archivos_rastreados):
            try:
                # Borrado por patrón de título (Modo Exterminador)
                d = os.path.dirname(r)
                p = os.path.splitext(os.path.basename(r))[0]
                if os.path.exists(d):
                    for f in os.listdir(d):
                        if f.startswith(p) and any(f.endswith(ext) for ext in extensiones_b):
                            try: os.remove(os.path.join(d, f))
                            except: pass
            except: pass
        self.archivos_rastreados.clear()

    def proceso_descarga(self):
        url_in = self.entry_url.get().strip()
        ruta = self.ruta_var.get()
        r_ffmpeg = obtener_configuracion_ffmpeg()

        url = f"ytsearch1:{url_in}" if not url_in.startswith("http") else url_in
        u_play = self.playlist_mode.get() if url_in.startswith("http") else False

        opts = {
            'outtmpl': f'{ruta}/%(title)s.%(ext)s',
            'restrictfilenames': True, 'trim_file_name': 200, 'overwrites': True,
            'noplaylist': not u_play, 'ignoreerrors': True,
            'match_filter': self.filtro_cancelacion,
            'progress_hooks': [self.hook_progreso],
            'http_headers': HEADERS_NAVEGADOR
        }
        if r_ffmpeg: opts['ffmpeg_location'] = r_ffmpeg

        if self.tabview.get() == "Audio MP3":
            opts.update({
                'format': 'bestaudio/best', 'writethumbnail': True,
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': self.combo_audio.get().split()[0]},
                    {'key': 'EmbedThumbnail'}, {'key': 'FFmpegMetadata'},
                ],
            })
        else:
            sel = self.combo_calidad.get().replace('p', '')
            fmt = 'bestvideo+bestaudio/best' if 'Auto' in sel else f'bestvideo[height={sel}]+bestaudio/best / best[height={sel}] / bestvideo+bestaudio/best'
            opts.update({'format': fmt, 'merge_output_format': 'mp4'})

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            if self.cancelar_flag:
                self.limpiar_basura()
                self.after(0, lambda: self.finalizar(False, "Cancelado"))
            else:
                self.after(0, lambda: self.finalizar(True))
        except Exception as e:
            if self.cancelar_flag: self.limpiar_basura()
            self.after(0, lambda: self.finalizar(False, str(e)))

    def finalizar(self, exito, error=""):
        self.btn_descargar.configure(state="normal", text="DESCARGAR ARCHIVO")
        self.btn_cancelar.configure(state="disabled")
        if exito:
            self.progress_bar.set(1); self.lbl_estado.configure(text="✅ ¡Completado!", text_color=COLOR_EXITO)
            self.crear_popup("¡Exitoso!", "Archivo descargado.")
        else:
            self.lbl_estado.configure(text="🚫 Cancelado/Error", text_color=COLOR_ROJO)
            if "CANCELADO" not in error.upper(): self.crear_popup("Error", error, es_error=True)

if __name__ == "__main__":
    # 1. EVITA EL ICONO DE PYTHON EN LA BARRA
    if ES_WINDOWS:
        import ctypes
        try:
            # ID único: 'Autor.App.Version'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('chimo.converter.v2')
        except: pass

    app = NeonConverter()

    # 2. CARGA DEL ICO
    nombre_ico = "icon.ico" if ES_WINDOWS else "icon.png"
    if getattr(sys, 'frozen', False):
        ruta_ico = os.path.join(sys._MEIPASS, nombre_ico)
    else:
        ruta_ico = nombre_ico

    if os.path.exists(ruta_ico):
        try:
            if ES_WINDOWS:
                # Esto clava el icono en la esquina de la ventana y en la barra
                app.iconbitmap(ruta_ico)
            else:
                from PIL import Image, ImageTk
                img = ImageTk.PhotoImage(Image.open(ruta_ico))
                app.wm_iconphoto(True, img)
        except: pass

    app.mainloop()
