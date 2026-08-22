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
import traceback
import glob

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


ES_WINDOWS = os.name == 'nt'

if ES_WINDOWS:
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

ctk.set_widget_scaling(1.0)
ctk.set_window_scaling(1.0)

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
COLOR_NARANJA = "#ff9800"
COLOR_AMARILLO = "#ffc107"
COLOR_AZUL = "#2196f3"
COLOR_VERDE = "#4caf50"

ARCHIVO_CONFIG = "config.json"


HEADERS_NAVEGADOR = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def obtener_configuracion_ffmpeg():
    """Obtiene la ruta de ffmpeg y ffprobe"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    # Buscar ffmpeg
    nombre_ffmpeg = "ffmpeg.exe" if ES_WINDOWS else "ffmpeg"
    ruta_ffmpeg = os.path.join(base_path, nombre_ffmpeg)
    
    # Buscar ffprobe
    nombre_ffprobe = "ffprobe.exe" if ES_WINDOWS else "ffprobe"
    ruta_ffprobe = os.path.join(base_path, nombre_ffprobe)
    

    if os.path.exists(ruta_ffmpeg) and os.path.exists(ruta_ffprobe):
        return ruta_ffmpeg, ruta_ffprobe
    
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "ffmpeg", "ffprobe"
    except FileNotFoundError:
        return None, None

def obtener_mejor_thumbnail_url(info_video):
    """Obtiene la mejor URL de thumbnail disponible"""
    try:
        # Intentar obtener la mejor calidad disponible
        thumbnails = info_video.get('thumbnails', [])
        
        calidades_preferidas = ['maxresdefault', 'sddefault', 'hqdefault', 'default']
        
        for calidad in calidades_preferidas:
            for thumb in thumbnails:
                if thumb.get('id') == calidad:
                    url = thumb.get('url')
                    if url:
                        return url

        if thumbnails:
            thumbnails.sort(key=lambda x: x.get('width', 0) * x.get('height', 0), reverse=True)
            return thumbnails[0].get('url')
        
        return info_video.get('thumbnail')
        
    except:
        return info_video.get('thumbnail')

def descargar_caratula_mejorada(url, ruta_destino):
    """Descarga la carátula - VERSIÓN MEJORADA Y CONFIABLE"""
    try:
        print(f"🔍 Intentando descargar carátula...")
        print(f"   URL: {url}")
        
        if not url or url == 'None' or not isinstance(url, str):
            print(f" URL de carátula inválida o vacía")
            return None
        
        # Asegurar que sea una URL completa
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = 'https://i.ytimg.com' + url
        
        print(f"   URL procesada: {url}")
        
    
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.youtube.com/',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            print(f" Imagen descargada exitosamente ({len(response.content)} bytes)")
            

            try:
                img = Image.open(BytesIO(response.content))
                

                if img.mode != 'RGB':
                    img = img.convert('RGB')
                

                if not ruta_destino.endswith('.jpg'):
                    ruta_destino = os.path.splitext(ruta_destino)[0] + '.jpg'
                
                img.save(ruta_destino, 'JPEG', quality=90)
                

                if os.path.exists(ruta_destino) and os.path.getsize(ruta_destino) > 1024:
                    print(f" Carátula guardada: {ruta_destino} ({os.path.getsize(ruta_destino)} bytes)")
                    return ruta_destino
                else:
                    print(f" Carátula guardada pero archivo muy pequeño o no existe")
                    return None
                    
            except Exception as img_error:
                print(f" Error procesando imagen: {img_error}")
                return None
        else:
            print(f" Error HTTP {response.status_code} al descargar carátula")
            return None
            
    except requests.exceptions.Timeout:
        print(f" Timeout al descargar carátula")
        return None
    except requests.exceptions.RequestException as e:
        print(f" Error de red: {e}")
        return None
    except Exception as e:
        print(f" Error inesperado: {e}")
        return None

def verificar_caratula_con_ffprobe(archivo_audio):
    """Verifica si un archivo de audio tiene carátula usando ffprobe"""
    try:
        ffmpeg_path, ffprobe_path = obtener_configuracion_ffmpeg()
        if not ffprobe_path:
            print(" FFprobe no disponible para verificación")
            return False
        
        if not os.path.exists(archivo_audio):
            print(f" Archivo no existe: {archivo_audio}")
            return False
        

        cmd = [
            ffprobe_path,
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_type',
            '-of', 'csv=p=0',
            archivo_audio
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True,
                              creationflags=subprocess.CREATE_NO_WINDOW if ES_WINDOWS else 0)
        

        if result.returncode == 0 and 'video' in result.stdout.lower():
            print(f" FFprobe confirma: El archivo tiene carátula incrustada")
            return True
        else:
            print(f" FFprobe: No se detectó carátula en el archivo")
            return False
            
    except Exception as e:
        print(f" Error verificando carátula con FFprobe: {e}")
        return False

def incrustar_caratula_con_ffprobe(audio_path, imagen_path, titulo=None, artista=None):
    """Incrusta carátula adaptándose al formato (MP3, M4A, FLAC, etc.)"""
    try:
        ffmpeg_path, _ = obtener_configuracion_ffmpeg()
        if not ffmpeg_path or not os.path.exists(audio_path):
            return False
        
        ext = os.path.splitext(audio_path)[1].lower()
        temp_output = audio_path + '.temp_tags' + ext

        cmd = [ffmpeg_path, '-y', '-i', audio_path, '-i', imagen_path]
        

        if ext == '.mp3':
            cmd.extend(['-map', '0:a', '-map', '1', '-c:a', 'copy', '-c:v', 'mjpeg', 
                        '-disposition:v', 'attached_pic', '-id3v2_version', '3'])
        elif ext == '.m4a':

            cmd.extend(['-map', '0:a', '-map', '1', '-c:a', 'copy', '-c:v', 'mjpeg', 
                        '-disposition:v', 'attached_pic'])
        else:

            cmd.extend(['-map', '0:a', '-map', '1', '-c:a', 'copy', '-metadata:s:v', 
                        'title="Album cover"', '-metadata:s:v', 'comment="Cover (Front)"'])

        if titulo: cmd.extend(['-metadata', f'title={titulo}'])
        if artista: cmd.extend(['-metadata', f'artist={artista}'])
        
        cmd.append(temp_output)
        
        result = subprocess.run(cmd, capture_output=True, text=True, 
                              creationflags=subprocess.CREATE_NO_WINDOW if ES_WINDOWS else 0)
        
        if result.returncode == 0 and os.path.exists(temp_output):
            os.replace(temp_output, audio_path)
            return True
        return False
    except Exception as e:
        print(f"Error incrustando: {e}")
        return False

def buscar_archivo_descargado(directorio, titulo_aproximado):
    """Busca archivo descargado admitiendo MKV y MP4"""
    try:
        extensiones = ['.mp4', '.mkv', '.mp3', '.m4a', '.webm', '.opus', '.flac', '.wav']
        
        # Limpiar el título para la búsqueda 
        titulo_limpio = re.sub(r'[^\w\s]', '', titulo_aproximado).lower()
        palabras_clave = titulo_limpio.split()[:3] 

        # 1. Intentar búsqueda por coincidencia de palabras clave
        archivos_en_carpeta = os.listdir(directorio)
        for archivo in archivos_en_carpeta:
            nombre_f = archivo.lower()

            if any(ext in nombre_f for ext in ['.part', '.ytdl', '.temp', '.tmp']):
                continue
                
            if any(nombre_f.endswith(ext) for ext in extensiones):

                if any(p in nombre_f for p in palabras_clave if len(p) > 2):
                    return os.path.join(directorio, archivo)


        archivos_validos = []
        for ext in extensiones:
            archivos_validos.extend(glob.glob(os.path.join(directorio, f'*{ext}')))
        
        # Filtrar archivos temporales
        archivos_validos = [f for f in archivos_validos 
                          if not any(f.endswith(tmp) for tmp in ['.part', '.ytdl', '.temp'])]
        
        if archivos_validos:

            archivos_validos.sort(key=os.path.getmtime, reverse=True)
            return archivos_validos[0]
            
    except Exception as e:
        print(f"Error buscando archivo: {e}")
    
    return None

class NeonConverter(ctk.CTk):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.title("Chimo Converter")
        self.geometry("900x900")
        self.resizable(True, True)
        self.configure(fg_color=COLOR_FONDO)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.cerrando = False

        self.ruta_var = ctk.StringVar(value=self.cargar_ruta_guardada())
        self.playlist_mode = ctk.BooleanVar(value=False)
        self.imagen_actual = None
        self.cancelar_flag = False
        self.archivos_rastreados = set()
        self.calidades_disponibles = []
        self.max_resolucion = 0
        self.hilo_descarga = None
        self.info_video_actual = None

        self.ruta_ffmpeg, self.ruta_ffprobe = obtener_configuracion_ffmpeg()

        # FIX ANTI-CRASH IMAGEN
        img_transparente = Image.new("RGBA", (400, 225), (0, 0, 0, 0))
        self.img_vacia = ctk.CTkImage(light_image=img_transparente, dark_image=img_transparente, size=(400, 225))

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                                   scrollbar_button_color=COLOR_FRAME,
                                                   scrollbar_button_hover_color=COLOR_MORADO)
        self.scroll_frame.pack(fill="both", expand=True)

        self.crear_interfaz()

    def on_closing(self):
        if self.cerrando:
            return

        self.cerrando = True
        self.cancelar_flag = True

        if self.hilo_descarga and self.hilo_descarga.is_alive():
            self.lbl_estado.configure(text=" Deteniendo...", text_color=COLOR_ERROR)
            self.update()
            time.sleep(1)

        self.limpiar_basura(al_cerrar=True)

        if ES_WINDOWS:
            try:
                subprocess.Popen(['taskkill', '/F', '/IM', 'ffmpeg.exe'], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL,
                                creationflags=subprocess.CREATE_NO_WINDOW)
            except:
                pass

        self.destroy()

        if getattr(sys, 'frozen', False):
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
            

            def forzar_icono():
                try:

                    nombre_ico = "icon.ico" if ES_WINDOWS else "icon.png"
                    if getattr(sys, 'frozen', False):
                        ruta_ico = os.path.join(sys._MEIPASS, nombre_ico)
                    else:
                        ruta_ico = nombre_ico
                    
                    if os.path.exists(ruta_ico):
                        if ES_WINDOWS:

                            popup.iconbitmap(ruta_ico)

                            popup.after(100, lambda: popup.iconbitmap(ruta_ico))
                        else:
                            img_ico = ImageTk.PhotoImage(Image.open(ruta_ico))
                            popup.wm_iconphoto(True, img_ico)
                except:
                    pass

            popup.after(200, forzar_icono)


            popup.transient(self)
            popup.grab_set()

            try:
                popup.update_idletasks()
                x = self.winfo_x() + (self.winfo_width() // 2) - (popup.winfo_width() // 2)
                y = self.winfo_y() + (self.winfo_height() // 2) - (popup.winfo_height() // 2)
                popup.geometry(f"+{x}+{y}")
            except: pass

            color_icono = COLOR_ERROR if es_error else COLOR_EXITO
            lbl_icono = ctk.CTkLabel(popup, text="!" if es_error else "✓", font=("Arial Black", 30),
                                    text_color=color_icono, fg_color="transparent")
            lbl_icono.pack(pady=(20, 5))

            ctk.CTkLabel(popup, text=titulo.upper(), font=("Arial Black", 18, "bold"), text_color="white").pack()
            ctk.CTkLabel(popup, text=mensaje, font=("Segoe UI", 12), text_color="gray", wraplength=350).pack(pady=10)

            ctk.CTkButton(popup, text="ENTENDIDO", command=popup.destroy,
                        fg_color=COLOR_MORADO, hover_color=COLOR_MORADO_HOVER,
                        width=150, corner_radius=20).pack(pady=20)

            popup.focus_force()
            popup.wait_window()
            
    def borrar_url(self):
        self.entry_url.delete(0, 'end')
        self.lbl_imagen.configure(image=self.img_vacia, text="")
        self.lbl_titulo.configure(text="Esperando video...")
        self.combo_calidad.configure(values=["(Analiza primero)"])
        self.combo_calidad.set("(Analiza primero)")
        self.imagen_actual = None
        self.calidades_disponibles = []
        self.max_resolucion = 0
        self.info_video_actual = None

    def accion_cancelar(self):
        self.cancelar_flag = True
        self.lbl_estado.configure(text=" DETENIENDO Y LIMPIANDO...", text_color=COLOR_ERROR)
        self.btn_cancelar.configure(state="disabled")

    def crear_interfaz(self):
        # HEADER
        self.frame_top = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.frame_top.pack(pady=(15, 5))
        fuente_titulo = ("Arial Black", 36, "bold")
        ctk.CTkLabel(self.frame_top, text="CHIMO", font=fuente_titulo, text_color="white").pack(side="left")
        ctk.CTkLabel(self.frame_top, text=" CONVERTER", font=fuente_titulo, text_color=COLOR_MORADO).pack(side="left")

        # ESTADO HERRAMIENTAS
        self.frame_herramientas = ctk.CTkFrame(self.scroll_frame, fg_color="transparent", height=30)
        self.frame_herramientas.pack(pady=(0, 5), fill="x", padx=20)

        herramientas_texto = []
        if self.ruta_ffmpeg:
            herramientas_texto.append("✅ FFmpeg")
        else:
            herramientas_texto.append("❌ FFmpeg")
        
        if self.ruta_ffprobe:
            herramientas_texto.append("✅ FFprobe")
        else:
            herramientas_texto.append("❌ FFprobe")
        
        estado_texto = " | ".join(herramientas_texto)
        estado_color = COLOR_EXITO if self.ruta_ffmpeg and self.ruta_ffprobe else COLOR_AMARILLO
        
        self.lbl_estado_herramientas = ctk.CTkLabel(self.frame_herramientas, text=estado_texto, 
                                                   font=("Segoe UI", 10), text_color=estado_color)
        self.lbl_estado_herramientas.pack()

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
        self.tabview = ctk.CTkTabview(self.scroll_frame, width=600, height=220,
                                      fg_color=COLOR_FRAME, corner_radius=20,
                                      segmented_button_fg_color=COLOR_INPUT,
                                      segmented_button_selected_color=COLOR_MORADO,
                                      segmented_button_unselected_color=COLOR_INPUT,
                                      text_color="white")
        self.tabview.pack(pady=5)

        self.tab_video = self.tabview.add("Video MP4")
        self.tab_audio = self.tabview.add("Audio")

        # Para video MP4
        self.combo_calidad = ctk.CTkComboBox(self.tab_video, values=["(Analiza primero)"], width=280, height=30, corner_radius=15,
                                             fg_color=COLOR_INPUT, button_color=COLOR_MORADO, border_color=COLOR_INPUT)
        self.combo_calidad.pack(pady=5)


        ctk.CTkLabel(self.tab_video, text="144p a 1080p: MP4 (Máxima Compatibilidad)", 
                     font=("Segoe UI", 10, "bold"), text_color=COLOR_EXITO).pack(pady=(10, 0))
        ctk.CTkLabel(self.tab_video, text="Audio AAC incluido", 
                     font=("Segoe UI", 9), text_color="gray").pack()

        ctk.CTkLabel(self.tab_video, text="2K a 8K: MKV (Máxima Calidad Original)", 
                     font=("Segoe UI", 10, "bold"), text_color=COLOR_NARANJA).pack(pady=(10, 0))
        ctk.CTkLabel(self.tab_video, text="Video VP9/AV1 + Audio Opus (Sin pérdida)", 
                     font=("Segoe UI", 9), text_color="gray").pack()

        self.switch_playlist = ctk.CTkSwitch(self.tab_video, text="Descargar Playlist Completa", variable=self.playlist_mode,
                                             progress_color=COLOR_MORADO, button_color="white")
        self.switch_playlist.pack(pady=5)

        # Para AUDIO
        self.frame_audio_opciones = ctk.CTkFrame(self.tab_audio, fg_color="transparent")
        self.frame_audio_opciones.pack(pady=5, fill="x", padx=10)

        # Formato de audio simple
        ctk.CTkLabel(self.frame_audio_opciones, text="Formato de Audio:", font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.combo_formato_audio = ctk.CTkComboBox(self.frame_audio_opciones, 
                                                   values=["MP3 con carátula", "MP3 sin carátula", "AAC (m4a)", "OPUS", "FLAC", "WAV"],
                                                   width=200, height=30, corner_radius=15,
                                                   fg_color=COLOR_INPUT, button_color=COLOR_MORADO, border_color=COLOR_INPUT)
        self.combo_formato_audio.set("MP3 con carátula")
        self.combo_formato_audio.grid(row=0, column=1, sticky="w")

        # Calidad
        ctk.CTkLabel(self.frame_audio_opciones, text="Calidad:", font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(10, 0))
        self.combo_calidad_audio = ctk.CTkComboBox(self.frame_audio_opciones, 
                                                   values=["320 kbps (Excelente)", "256 kbps (Alta)", "192 kbps (Buena)", "128 kbps (Normal)"],
                                                   width=200, height=30, corner_radius=15,
                                                   fg_color=COLOR_INPUT, button_color=COLOR_MORADO, border_color=COLOR_INPUT)
        self.combo_calidad_audio.set("192 kbps (Buena)")
        self.combo_calidad_audio.grid(row=1, column=1, sticky="w", pady=(10, 0))

        # Información
        frame_info = ctk.CTkFrame(self.tab_audio, fg_color="transparent")
        frame_info.pack(pady=5, fill="x", padx=10)

        if self.ruta_ffmpeg and self.ruta_ffprobe:
            ctk.CTkLabel(frame_info, text=" Carátulas verificadas con FFprobe", 
                         font=("Segoe UI", 9), text_color=COLOR_EXITO).pack()
        else:
            ctk.CTkLabel(frame_info, text=" Sin FFmpeg/FFprobe: Carátulas no disponibles", 
                         font=("Segoe UI", 9), text_color=COLOR_AMARILLO).pack()

        self.switch_playlist_audio = ctk.CTkSwitch(self.tab_audio, text="Descargar Playlist Completa", variable=self.playlist_mode,
                                                   progress_color=COLOR_MORADO, button_color="white")
        self.switch_playlist_audio.pack(pady=5)


        self.frame_ruta = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.frame_ruta.pack(fill="x", padx=60, pady=(5, 5))
        self.entry_ruta = ctk.CTkEntry(self.frame_ruta, textvariable=self.ruta_var, state="disabled",
                                       fg_color=COLOR_FRAME, border_width=0, corner_radius=10, height=35)
        self.entry_ruta.pack(side="left", fill="x", expand=True, padx=(0,10))
        ctk.CTkButton(self.frame_ruta, text="SELECCIONAR CARPETA", width=160, height=35, command=self.seleccionar_carpeta,
                      fg_color=COLOR_INPUT, hover_color="#444", corner_radius=10, font=("Segoe UI", 11, "bold")).pack(side="left")

        self.progress_bar = ctk.CTkProgressBar(self.scroll_frame, width=500, progress_color=COLOR_MORADO, fg_color=COLOR_INPUT, height=12)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(0, 2))
        self.lbl_estado = ctk.CTkLabel(self.scroll_frame, text="Listo para descargar", text_color="gray", font=("Segoe UI", 11))
        self.lbl_estado.pack(pady=(0, 10))


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

    def seleccionar_carpeta(self):
        ruta = filedialog.askdirectory()
        if ruta:
            self.ruta_var.set(ruta)
            self.guardar_ruta(ruta)

    def hilo_analizar(self):
        url = self.entry_url.get().strip()
        if not url: 
            return

        self.btn_analizar.configure(state="disabled")
        self.lbl_titulo.configure(text="Buscando información...")

        try: 
            self.lbl_imagen.configure(image=self.img_vacia, text="")
        except: 
            pass

        self.imagen_actual = None
        self.info_video_actual = None

        threading.Thread(target=self.analizar_video, args=(url,), daemon=True).start()

    def analizar_video(self, url):
        try:
            if not url.startswith("http"):
                url = f"ytsearch1:{url}"
                es_busqueda = True
            else:
                es_busqueda = False

            ydl_opts = {
                'quiet': True, 
                'noplaylist': True, 
                'extract_flat': False,
                'http_headers': HEADERS_NAVEGADOR
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info: 
                    info = info['entries'][0]

                self.info_video_actual = info

                titulo = info.get('title', 'Video sin título')
                artista = info.get('uploader', 'Desconocido')
                prefijo = "Resultado: " if es_busqueda else ""
                self.after(0, lambda: self.lbl_titulo.configure(
                    text=f"{prefijo}{titulo[:60]}...\nArtista: {artista[:30]}"))

                # Calidades para video
                formatos = set()
                altas_resoluciones = []
                self.max_resolucion = 0

                if 'formats' in info:
                    for f in info['formats']:
                        if f.get('height') and f.get('vcodec') != 'none':
                            altura = f['height']
                            formatos.add(altura)
                            if altura > self.max_resolucion:
                                self.max_resolucion = altura
                            if altura >= 2160:
                                altas_resoluciones.append(f'{altura}p')
                            elif altura >= 1440:
                                altas_resoluciones.append(f'{altura}p (2K)')

                lista_c = sorted(list(formatos), reverse=True)
                lista_f = []
                for res in lista_c:
                    if res >= 2160:
                        lista_f.append(f"{res}p (4K/8K)")
                    elif res >= 1440:
                        lista_f.append(f"{res}p (2K)")
                    else:
                        lista_f.append(f"{res}p")

                lista_f.insert(0, "Mejor Calidad (Auto)")
                if not lista_f: 
                    lista_f = ["Mejor Calidad (Auto)"]

                self.calidades_disponibles = lista_c

                self.after(0, lambda: self.combo_calidad.configure(values=lista_f))
                self.after(0, lambda: self.combo_calidad.set("Mejor Calidad (Auto)"))

                if altas_resoluciones:
                    res_text = ", ".join(sorted(set(altas_resoluciones), reverse=True))
                    self.after(0, lambda: self.lbl_titulo.configure(
                        text=f"{prefijo}{titulo[:50]}... [{res_text}]\nArtista: {artista[:30]}"))

                # Thumbnail - USAR LA MEJOR CALIDAD
                mejor_thumbnail = obtener_mejor_thumbnail_url(info)
                if mejor_thumbnail:
                    print(f"📸 Mejor thumbnail encontrado: {mejor_thumbnail}")
                    try:
                        resp = requests.get(mejor_thumbnail, headers=HEADERS_NAVEGADOR, timeout=5)
                        if resp.status_code == 200:
                            img_data = Image.open(BytesIO(resp.content))
                            img_data = img_data.resize((400, 225), Image.Resampling.LANCZOS)
                            nueva_img = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(400, 225))
                            self.imagen_actual = nueva_img
                            self.after(0, lambda: self.lbl_imagen.configure(image=self.imagen_actual, text=""))
                            print(f"✅ Vista previa cargada correctamente")
                    except Exception as e:
                        print(f"❌ Error cargando vista previa: {e}")
                        self.after(0, lambda: self.lbl_imagen.configure(image=self.img_vacia, text="🎵 Sin vista previa"))

        except Exception as e:
            self.after(0, lambda: self.lbl_titulo.configure(text="❌ Error en enlace"))
            print(f"Error analizando video: {e}")
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

        self.hilo_descarga = threading.Thread(target=self.proceso_descarga_con_caratulas, daemon=True)
        self.hilo_descarga.start()

    def filtro_cancelacion(self, info_dict, *, incomplete):
        if self.cancelar_flag: 
            return "Descarga cancelada"
        return None

    def hook_progreso(self, d):
        if self.cancelar_flag: 
            raise Exception("CANCELADO_POR_USUARIO")

        if d.get('status') == 'downloading':
            try:
                p = float(re.sub(r'\x1b\[[0-9;]*m', '', d.get('_percent_str', '0%')).replace('%',''))
                self.progress_bar.set(p / 100)
                msg = f"Bajando: {p:.1f}% | {d.get('_speed_str', '')}"
                self.lbl_estado.configure(text=msg, text_color=COLOR_MORADO)
            except: 
                pass
        elif d.get('status') == 'finished':
            if self.tabview.get() == "Audio":
                self.lbl_estado.configure(text="Procesando audio...", text_color=COLOR_AZUL)
            else:
                sel = self.combo_calidad.get()
                res_num = self.obtener_resolucion_numerica(sel)

                if res_num >= 2160:
                    self.lbl_estado.configure(text="Convirtiendo 4K/8K...", text_color=COLOR_NARANJA)
                elif res_num >= 1440:
                    self.lbl_estado.configure(text="Convirtiendo 2K...", text_color=COLOR_AMARILLO)
                else:
                    self.lbl_estado.configure(text="Convirtiendo a MP4...", text_color="white")

    def obtener_resolucion_numerica(self, texto_resolucion):
        if texto_resolucion == "Mejor Calidad (Auto)":
            return self.max_resolucion if hasattr(self, 'max_resolucion') else 0

        numeros = re.findall(r'\d+', texto_resolucion)
        if numeros:
            return int(numeros[0])
        return 0

    def limpiar_basura(self, al_cerrar=False):
        if not al_cerrar: 
            time.sleep(1.5)

        if ES_WINDOWS:
            try: 
                subprocess.Popen(['taskkill', '/F', '/IM', 'ffmpeg.exe'], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL,
                                creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(0.5)
            except: 
                pass

        if al_cerrar: 
            return

        extensiones_b = ['.part', '.ytdl', '.webp', '.jpg', '.jpeg', '.png', 
                        '.info.json', '.temp', '.tmp']

        for r in list(self.archivos_rastreados):
            try:
                d = os.path.dirname(r)
                p = os.path.splitext(os.path.basename(r))[0]
                if os.path.exists(d):
                    for f in os.listdir(d):
                        if f.startswith(p) and any(f.endswith(ext) for ext in extensiones_b):
                            try: 
                                os.remove(os.path.join(d, f))
                            except: 
                                pass
            except: 
                pass
        self.archivos_rastreados.clear()

    def proceso_descarga_con_caratulas(self):
        """Proceso de descarga corregido para encontrar FFmpeg correctamente"""
        try:
            url_in = self.entry_url.get().strip()
            ruta = self.ruta_var.get()
            tab_actual = self.tabview.get()

            if not self.info_video_actual:
                self.after(0, lambda: self.finalizar(False, "Analiza el video primero"))
                return

            titulo = self.info_video_actual.get('title', 'archivo_descargado')
            artista = self.info_video_actual.get('uploader', 'Desconocido')
            mejor_thumbnail_url = obtener_mejor_thumbnail_url(self.info_video_actual)
            
            # --- CORRECCIÓN: Configurar ruta de ffmpeg inteligentemente ---
            ffmpeg_dir = None
            if self.ruta_ffmpeg and self.ruta_ffmpeg not in ["ffmpeg", "ffmpeg.exe"]:
                ffmpeg_dir = os.path.dirname(self.ruta_ffmpeg)
            
            # --- SECCIÓN DE AUDIO ---
            if tab_actual == "Audio":
                formato_seleccionado = self.combo_formato_audio.get()
                calidad_texto = self.combo_calidad_audio.get()
                calidad_num = int(calidad_texto.split()[0])

                formatos_map = {"MP3": "mp3", "AAC": "m4a", "OPUS": "opus", "FLAC": "flac", "WAV": "wav"}
                cod_ffmpeg = "mp3"
                for key, val in formatos_map.items():
                    if key in formato_seleccionado:
                        cod_ffmpeg = val
                        break

                con_caratula = "sin carátula" not in formato_seleccionado.lower() and cod_ffmpeg != 'wav'

                opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(ruta, '%(title)s.%(ext)s'),
                    'restrictfilenames': True,
                    'overwrites': True,
                    'noplaylist': not self.playlist_mode.get(),
                    'ignoreerrors': True,
                    'match_filter': self.filtro_cancelacion,
                    'progress_hooks': [self.hook_progreso],
                    'http_headers': HEADERS_NAVEGADOR,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': cod_ffmpeg,
                        'preferredquality': str(calidad_num),
                    }]
                }
                
                if ffmpeg_dir:
                    opts['ffmpeg_location'] = ffmpeg_dir

                self.after(0, lambda: self.lbl_estado.configure(text=f"Bajando {cod_ffmpeg.upper()}...", text_color=COLOR_MORADO))
                
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url_in])

                if self.cancelar_flag:
                    self.limpiar_basura()
                    return

                archivo_descargado = buscar_archivo_descargado(ruta, titulo)
                
                if archivo_descargado:
                    if con_caratula and mejor_thumbnail_url and self.ruta_ffmpeg:
                        self.after(0, lambda: self.lbl_estado.configure(text="Incrustando carátula...", text_color=COLOR_AZUL))
                        import hashlib
                        hash_t = hashlib.md5(titulo.encode()).hexdigest()[:8]
                        caratula_temp = os.path.join(ruta, f'thumb_{hash_t}.jpg')
                        
                        if descargar_caratula_mejorada(mejor_thumbnail_url, caratula_temp):
                            incrustar_caratula_con_ffprobe(archivo_descargado, caratula_temp, titulo, artista)
                            if os.path.exists(caratula_temp): os.remove(caratula_temp)

                    self.after(0, lambda: self.finalizar_audio(True, formato_seleccionado, calidad_texto, con_caratula, archivo_descargado))
                else:
                    self.after(0, lambda: self.finalizar(False, "No se encontró el archivo de audio"))

            # --- SECCIÓN DE VIDEO ---
            else:
                calidad_sel = self.combo_calidad.get()
                resolucion = self.max_resolucion if calidad_sel == "Mejor Calidad (Auto)" else self.obtener_resolucion_numerica(calidad_sel)

                if resolucion <= 1080:
                    formato_string = f"bestvideo[height<={resolucion}][ext=mp4]+bestaudio[ext=m4a]/best[height<={resolucion}][ext=mp4]/best"
                    contenedor = "mp4"
                else:
                    formato_string = f"bestvideo[height<={resolucion}]+bestaudio/best[height<={resolucion}]"
                    contenedor = "mkv"

                opts = {
                    'format': formato_string,
                    'outtmpl': os.path.join(ruta, '%(title)s.%(ext)s'),
                    'merge_output_format': contenedor,
                    'restrictfilenames': True,
                    'overwrites': True,
                    'noplaylist': not self.playlist_mode.get(),
                    'ignoreerrors': True,
                    'progress_hooks': [self.hook_progreso],
                    'http_headers': HEADERS_NAVEGADOR,
                    'quiet': True,
                }
                
                if ffmpeg_dir:
                    opts['ffmpeg_location'] = ffmpeg_dir

                self.after(0, lambda: self.lbl_estado.configure(text=f"Bajando {resolucion}p ({contenedor.upper()})...", text_color=COLOR_MORADO))

                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url_in])

                if self.cancelar_flag:
                    self.limpiar_basura()
                    return

                time.sleep(2)
                archivo_descargado = buscar_archivo_descargado(ruta, titulo)

                if archivo_descargado:
                    tipo_res = "4k" if resolucion >= 2160 else ("2k" if resolucion >= 1440 else "")
                    self.after(0, lambda: self.finalizar_video(True, resolucion, archivo_descargado, tipo_res))
                else:
                    self.after(0, lambda: self.finalizar(False, "No se encontró el archivo de video"))

        except Exception as e:
            print(f"❌ ERROR CRÍTICO: {traceback.format_exc()}")
            self.after(0, lambda: self.finalizar(False, f"Error: {str(e)[:100]}"))

    def finalizar_audio(self, exito, formato, calidad, tiene_caratula, ruta_archivo):
            """Finalización para audio"""
            self.btn_descargar.configure(state="normal", text="DESCARGAR ARCHIVO")
            self.btn_cancelar.configure(state="disabled")

            if exito:
                self.progress_bar.set(1)
                nombre_archivo = os.path.basename(ruta_archivo)

                # Bloque para MP3
                if "MP3" in formato:
                    if tiene_caratula:
                        self.lbl_estado.configure(text=f"✅ ¡MP3 Descargado! ({calidad} + carátula)",
                                                text_color=COLOR_AZUL)
                        self.crear_popup("¡Exitoso!",
                            f"Audio descargado: {nombre_archivo}\n\nFormato: MP3 {calidad}\nCarátula: ✅ Sí (verificada)")
                    else:
                        self.lbl_estado.configure(text=f"✅ ¡MP3 Descargado! ({calidad})",
                                                text_color=COLOR_VERDE)
                        self.crear_popup("¡Exitoso!",
                            f"Audio descargado: {nombre_archivo}\n\nFormato: MP3 {calidad}\nCarátula: No")

                # Bloque para AAC
                elif "AAC" in formato:
                    self.lbl_estado.configure(text=f"✅ ¡AAC Descargado! ({calidad})",
                                            text_color=COLOR_VERDE)
                    self.crear_popup("¡Exitoso!",
                        f"Audio descargado: {nombre_archivo}\n\nFormato: AAC {calidad}")

                # --- NUEVO: Bloque genérico para WAV, FLAC, OPUS, etc. ---
                else:
                    self.lbl_estado.configure(text=f"✅ ¡Audio Descargado! ({formato})",
                                            text_color=COLOR_EXITO)
                    self.crear_popup("¡Exitoso!",
                        f"Audio descargado: {nombre_archivo}\n\nFormato: {formato}\nCalidad: Alta")

                self.limpiar_basura()
            else:
                self.lbl_estado.configure(text=" Error", text_color=COLOR_ROJO)

    def finalizar_video(self, exito, resolucion, ruta_archivo, tipo_res):
        """Finalización para video"""
        self.btn_descargar.configure(state="normal", text="DESCARGAR ARCHIVO")
        self.btn_cancelar.configure(state="disabled")

        if exito:
            self.progress_bar.set(1)
            nombre_archivo = os.path.basename(ruta_archivo)

            if tipo_res == "4k":
                self.lbl_estado.configure(text=f"✅ ¡4K/8K Descargado! ({resolucion}p)", 
                                         text_color=COLOR_NARANJA)
                self.crear_popup("¡Exitoso!", 
                    f"Video descargado: {nombre_archivo}\n\nResolución: {resolucion}p (4K/8K)\nFormato: MP4")
            elif tipo_res == "2k":
                self.lbl_estado.configure(text=f"✅ ¡2K Descargado! ({resolucion}p)", 
                                         text_color=COLOR_AMARILLO)
                self.crear_popup("¡Exitoso!", 
                    f"Video descargado: {nombre_archivo}\n\nResolución: {resolucion}p (2K)\nFormato: MP4")
            else:
                self.lbl_estado.configure(text=f"✅ ¡Video Descargado! ({resolucion}p)", 
                                         text_color=COLOR_EXITO)
                self.crear_popup("¡Exitoso!", 
                    f"Video descargado: {nombre_archivo}\n\nResolución: {resolucion}p\nFormato: MP4")

            self.limpiar_basura()
        else:
            self.lbl_estado.configure(text=" Error", text_color=COLOR_ROJO)

    def finalizar(self, exito, error=""):
        """Finalización general"""
        self.btn_descargar.configure(state="normal", text="DESCARGAR ARCHIVO")
        self.btn_cancelar.configure(state="disabled")

        if not exito:
            self.progress_bar.set(0)
            self.lbl_estado.configure(text=" Error", text_color=COLOR_ROJO)
            if error and "CANCELADO" not in error.upper():
                self.crear_popup("Error", error[:100], es_error=True)

if __name__ == "__main__":
    if ES_WINDOWS:
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('chimo.converter.ffprobe')
        except: 
            pass

    def excepthook(exctype, value, tb):
        error_msg = ''.join(traceback.format_exception(exctype, value, tb))
        print(f"Error no capturado: {error_msg}")

        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            tk.messagebox.showerror("Error", "Ocurrió un error inesperado.")
        except:
            pass

        if getattr(sys, 'frozen', False):
            os._exit(1)

    sys.excepthook = excepthook

    app = NeonConverter()

    nombre_ico = "icon.ico" if ES_WINDOWS else "icon.png"
    if getattr(sys, 'frozen', False):
        ruta_ico = os.path.join(sys._MEIPASS, nombre_ico)
    else:
        ruta_ico = nombre_ico

    if os.path.exists(ruta_ico):
        try:
            if ES_WINDOWS:
                app.iconbitmap(ruta_ico)
            else:
                img = ImageTk.PhotoImage(Image.open(ruta_ico))
                app.wm_iconphoto(True, img)
        except: 
            pass

    try:
        app.mainloop()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error en mainloop: {e}")
    finally:
        if getattr(sys, 'frozen', False):
            os._exit(0)
