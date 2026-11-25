import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

NOFLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def recurso(nombre):
    """Ruta de un archivo incluido en el programa (icono, logo)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, nombre)


def herramienta(nombre):
    """Busca ffmpeg/ffprobe junto al programa; si no, en el PATH."""
    base = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
    exe = nombre + (".exe" if os.name == "nt" else "")
    local = os.path.join(base, exe)
    return local if os.path.exists(local) else nombre


FFMPEG = herramienta("ffmpeg")
FFPROBE = herramienta("ffprobe")

# Qué códecs se pueden copiar sin recomprimir en cada formato
COMPAT = {
    "mp4": ({"h264", "hevc", "av1", "mpeg4"}, {"aac", "mp3", "ac3", "eac3", "alac", "opus"}),
    "mkv": (None, None),  # acepta casi todo
    "webm": ({"vp8", "vp9", "av1"}, {"opus", "vorbis"}),
    "mov": ({"h264", "hevc", "mpeg4", "prores"}, {"aac", "alac", "mp3", "ac3", "pcm_s16le"}),
    "avi": ({"h264", "mpeg4", "mpeg2video"}, {"mp3", "ac3", "pcm_s16le"}),
    "ts": ({"h264", "hevc", "mpeg2video"}, {"aac", "mp3", "ac3", "eac3"}),
}

# Códecs de recodificación (alta calidad) por formato destino
RECODIF = {
    "webm": (["-c:v", "libvpx-vp9", "-crf", "18", "-b:v", "0"], ["-c:a", "libopus", "-b:a", "192k"]),
    "avi": (["-c:v", "libx264", "-crf", "16", "-preset", "slow"], ["-c:a", "libmp3lame", "-b:a", "320k"]),
}
RECODIF_DEF = (["-c:v", "libx264", "-crf", "16", "-preset", "slow"], ["-c:a", "aac", "-b:a", "320k"])


def sondear(ruta):
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", ruta],
        capture_output=True, text=True, creationflags=NOFLAGS,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "No se pudo leer el video")
    return json.loads(r.stdout)


def etiqueta_resolucion(alto):
    if alto >= 2160: return "4K (Ultra HD)"
    if alto >= 1440: return "2K (QHD)"
    if alto >= 1080: return "Full HD (1080p)"
    if alto >= 720: return "HD (720p)"
    if alto >= 480: return "SD (480p)"
    return "Baja resolución"


def tamano(n):
    n = float(n)
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.1f} {u}"
        n /= 1024


def fps_de(v):
    try:
        a, b = v.get("avg_frame_rate", "0/1").split("/")
        return float(a) / float(b) if float(b) else 0
    except Exception:
        return 0


def pantallas(vc, alto):
    """Dónde se puede reproducir según códec y resolución."""
    t = []
    t.append("Celular/Tablet: " + ("sí" if vc in {"h264", "hevc", "vp9", "av1", "mpeg4"} else "depende del modelo"))
    if vc == "h264" and alto <= 1080:
        t.append("Smart TV / TV Box: sí, incluso equipos viejos o de poca RAM")
    elif vc == "h264":
        t.append("Smart TV / TV Box: solo equipos que soporten 4K")
    elif vc == "hevc":
        t.append("Smart TV / TV Box: solo equipos recientes (H.265); los viejos no lo mueven bien")
    elif vc == "av1":
        t.append("Smart TV / TV Box: solo equipos muy nuevos")
    else:
        t.append("Smart TV / TV Box: puede fallar; mejor convertir a MP4 H.264")
    t.append("PC: sí (con VLC o similar)")
    t.append("Redes sociales/YouTube: " + ("sí" if vc in {"h264", "hevc", "vp9", "av1"} else "conviene convertir a MP4"))
    return "\n".join(t)


def detalles(ruta):
    d = sondear(ruta)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    f = d["format"]
    lineas = [
        f"Nombre: {os.path.basename(ruta)}",
        f"Tamaño: {tamano(os.path.getsize(ruta))}",
        f"Duración: {float(f.get('duration', 0)):.1f} s",
    ]
    if v:
        alto = int(v.get("height", 0))
        lineas += [
            f"Resolución: {v.get('width')}x{alto} - {etiqueta_resolucion(alto)}",
            f"Códec de video: {v.get('codec_name')}",
            f"Cuadros por segundo: {fps_de(v):.2f}",
        ]
    if a:
        lineas.append(f"Audio: {a.get('codec_name')}, {a.get('channels')} canales, {a.get('sample_rate')} Hz")
    if f.get("bit_rate"):
        lineas.append(f"Bitrate total: {int(f['bit_rate']) // 1000} kbps")
    if v:
        lineas += ["", "Dónde se puede usar:", pantallas(v.get("codec_name"), int(v.get("height", 0)))]
    return "\n".join(lineas), v, a, float(f.get("duration", 0))


def armar_comando(entrada, salida, fmt, v, a):
    vok, aok = COMPAT[fmt]
    vc = v.get("codec_name") if v else None
    ac = a.get("codec_name") if a else None
    rv, ra = RECODIF.get(fmt, RECODIF_DEF)
    cmd = [FFMPEG, "-y", "-i", entrada, "-map", "0:v:0?", "-map", "0:a?"]
    copia_v = vok is None or vc in vok
    copia_a = aok is None or ac in aok
    cmd += ["-c:v", "copy"] if copia_v else rv
    cmd += ["-c:a", "copy"] if copia_a else ra
    if fmt == "mp4":
        cmd += ["-movflags", "+faststart"]
    cmd += ["-progress", "pipe:1", "-nostats", salida]
    modo = "Sin pérdida (copia directa)" if copia_v and copia_a else (
        "Video sin pérdida, audio recodificado" if copia_v else
        "Audio sin pérdida, video recodificado en alta calidad" if copia_a else
        "Recodificado en alta calidad")
    return cmd, modo


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Convert")
        self.geometry("620x620")
        try:
            self.iconbitmap(recurso("icon.ico"))
        except Exception:
            pass
        self.ruta = None
        self.v = self.a = None
        self.dur = 0

        cab = ttk.Frame(self)
        cab.pack(pady=(12, 4))
        try:
            self.logo = tk.PhotoImage(file=recurso("logo.png"))
            ttk.Label(cab, image=self.logo).pack(side="left", padx=(0, 10))
        except Exception:
            pass
        ttk.Label(cab, text="Convert", font=("Segoe UI", 22, "bold")).pack(side="left")
        ttk.Button(self, text="Elegir video...", command=self.elegir).pack(pady=10)
        self.info = tk.Text(self, height=17, wrap="word", state="disabled")
        self.info.pack(fill="both", padx=10)

        fila = ttk.Frame(self)
        fila.pack(pady=10)
        ttk.Label(fila, text="Convertir a:").pack(side="left")
        self.fmt = ttk.Combobox(fila, values=list(COMPAT), state="readonly", width=8)
        self.fmt.set("mp4")
        self.fmt.pack(side="left", padx=8)
        self.btn = ttk.Button(fila, text="Convertir", command=self.convertir)
        self.btn.pack(side="left")

        self.barra = ttk.Progressbar(self, maximum=100)
        self.barra.pack(fill="x", padx=10)
        self.estado = ttk.Label(self, text="")
        self.estado.pack(pady=6)

    def poner(self, txt):
        self.info.config(state="normal")
        self.info.delete("1.0", "end")
        self.info.insert("end", txt)
        self.info.config(state="disabled")

    def elegir(self):
        ruta = filedialog.askopenfilename(
            filetypes=[("Videos", "*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.3gp *.mpg *.mpeg *.ts *.m2ts"), ("Todos", "*.*")])
        if not ruta:
            return
        try:
            txt, self.v, self.a, self.dur = detalles(ruta)
            self.ruta = ruta
            self.poner(txt)
            self.estado.config(text="")
            self.barra["value"] = 0
        except Exception as e:
            messagebox.showerror("Error", f"{e}\n\n¿Están ffmpeg.exe y ffprobe.exe junto al programa?")

    def convertir(self):
        if not self.ruta:
            messagebox.showinfo("Aviso", "Primero elige un video.")
            return
        fmt = self.fmt.get()
        base = os.path.splitext(self.ruta)[0]
        salida = filedialog.asksaveasfilename(initialfile=os.path.basename(base) + "_convertido." + fmt,
                                              defaultextension="." + fmt)
        if not salida:
            return
        cmd, modo = armar_comando(self.ruta, salida, fmt, self.v, self.a)
        self.estado.config(text=f"Modo: {modo}")
        self.btn.config(state="disabled")
        threading.Thread(target=self.correr, args=(cmd, salida), daemon=True).start()

    def correr(self, cmd, salida):
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, creationflags=NOFLAGS)
        for linea in p.stdout:
            if linea.startswith("out_time_us=") and self.dur:
                try:
                    pct = min(100, int(linea.split("=")[1]) / 1e6 / self.dur * 100)
                    self.after(0, lambda x=pct: self.barra.config(value=x))
                except ValueError:
                    pass
        p.wait()
        self.after(0, lambda: self.fin(p.returncode, salida))

    def fin(self, code, salida):
        self.btn.config(state="normal")
        if code == 0:
            self.barra["value"] = 100
            messagebox.showinfo("Listo", f"Video guardado en:\n{salida}\nTamaño: {tamano(os.path.getsize(salida))}")
        else:
            messagebox.showerror("Error", "La conversión falló.")


if __name__ == "__main__":
    App().mainloop()
