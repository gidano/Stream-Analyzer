# -*- coding: utf-8 -*-
"""
Online Stream Audio & Network Analyzer
Indítás: python stream_analyzer.py  (vagy .pyw Windows alatt)
"""

import sys
import os
import traceback
import tempfile
from datetime import datetime

# ---------- CRASH LOG ----------
def _crash_log_path():
    # A .pyw mellett próbáljuk, ha nem megy, a temp könyvtárba
    try:
        base = os.path.dirname(os.path.abspath(sys.argv[0])) or os.getcwd()
        return os.path.join(base, "stream_analyzer_crash.log")
    except Exception:
        return os.path.join(tempfile.gettempdir(), "stream_analyzer_crash.log")

def log_crash(exc_type, exc_value, exc_tb):
    try:
        with open(_crash_log_path(), "a", encoding="utf-8") as f:
            f.write("\n" + "=" * 70 + "\n")
            f.write(f"Időpont: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"Futtatva: {sys.executable}\n")
            f.write("-" * 70 + "\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    except Exception:
        pass
    # Fallback: próbáljunk egy messageboxot is (a nyelvváltás itt még nem elérhető, ezért kétnyelvű)
    try:
        import tkinter.messagebox as mb
        mb.showerror(
            "Hiba történt / Error",
            f"A program hibával leállt. / The program has stopped due to an error.\n\n"
            f"{exc_type.__name__}: {exc_value}\n\n"
            f"Részletek / Details: {_crash_log_path()}"
        )
    except Exception:
        pass

sys.excepthook = log_crash

# ---------- FÜGGŐSÉGEK ELLENŐRZÉSE ----------
_missing = []
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
except Exception as e:
    _missing.append(f"tkinter ({e})")

try:
    import requests
except Exception as e:
    _missing.append(f"requests ({e})")

try:
    import winreg
except Exception as e:
    _missing.append(f"winreg ({e})")

if _missing:
    try:
        import tkinter.messagebox as mb
        import tkinter as _tk
        _r = _tk.Tk(); _r.withdraw()
        mb.showerror("Hiányzó függőség / Missing dependency",
                     "A program nem tud elindulni, mert hiányzik: / "
                     "The program cannot start because the following is missing:\n\n"
                     + "\n".join(_missing)
                     + "\n\nTelepítés / Install: pip install requests")
        _r.destroy()
    except Exception:
        pass
    sys.exit(1)

# A többi import csak ezután
import subprocess
import json
import threading
import time
import statistics
import csv
import shutil
import re
import socket
import ssl
from urllib.parse import urlparse


# ---------- SEGÉD: erőforrás elérési út (fejlesztés / PyInstaller .exe) ----------
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# ---------- SEGÉD: ffprobe elérhetőség ----------
def ffprobe_available():
    return shutil.which("ffprobe") is not None


# ---------- FORDÍTÁSOK / TRANSLATIONS ----------
TRANSLATIONS = {
    "HU": {
        "app_title": "Online Stream Audio & Hálózat Elemző",
        "frame_url": " Stream URL ",
        "btn_start": "Indítás",
        "btn_stop": "Leállítás",
        "frame_audio": " Aktuális Audio Adatok ",
        "frame_net": " Hálózat, Késleltetés & Puffer Biztonság ",
        "frame_http": " HTTP / Stream Metaadatok ",
        "frame_conn": " Kapcsolódási Idő Részletezése ",
        "frame_session": " Munkamenet Összegzés ",
        "frame_log": " Mérési Napló ",
        "frame_theme": " Megjelenés (Színprofil) ",
        "tab_audio_net": "Audio && Hálózat",
        "tab_http": "Stream && Kapcsolat",
        "tab_session": "Összegzés",
        "tab_log": "Napló && Beállítások",
        "btn_help": "Súgó",
        "btn_save_log": "Napló mentése (CSV)",
        "btn_clear_log": "Napló törlése",
        "log_count": "Rögzített minták: {n}",
        "theme_auto": "Windows OS (Auto)",
        "theme_light": "Világos",
        "theme_dark": "Sötét",
        "paste": "Beillesztés",
        "labels": {
            "codec": "Codec:",
            "bitrate": "Névleges Bitrate:",
            "channels": "Csatornák (Mono/Stereo):",
            "samplerate": "Mintavételezés (kHz):",
            "bitdepth": "Mintavételi mélység:",
            "net_speed": "Valós hálózati sebesség:",
            "ping": "Ping (utolsó):",
            "chunk_jitter": "Valós adatfolyam jitter:",
            "jitter": "Ping jitter (utolsó):",
            "ping_stats": "Ping átlag / szórás:",
            "buffer": "Puffer biztonság:",
            "stalls": "Pufferelési megszakítások:",
            "alert": "Riasztás:",
            "timestamp": "Utolsó frissítés:",
            "status": "Állapot:",
            "server_sw": "Szerver szoftver:",
            "stream_status": "Stream állapot:",
            "content_type": "Content-Type (MIME):",
            "server_host": "Szerver:",
            "listeners": "Hallgatók (aktuális/max):",
            "stream_title": "Most szól:",
            "redirects": "Átirányítások száma:",
            "source_url": "Feloldott lejátszási lista:",
            "dns_time": "DNS feloldás:",
            "tcp_time": "TCP kapcsolódás:",
            "tls_time": "TLS handshake:",
            "ttfb_time": "Első byte-ig (TTFB):",
            "total_connect_time": "Összes kapcsolódási idő:",
            "sess_duration": "Munkamenet hossza:",
            "sess_samples": "Rögzített minták száma:",
            "sess_ping_range": "Ping (min / átlag / max):",
            "sess_speed_range": "Sebesség (min / átlag / max):",
            "sess_worst_window": "Legrosszabb 60 mp-es szakasz (átlag ping):",
            "sess_stalls": "Összes pufferelési megszakítás:",
        },
        "status": {
            "stopped": "Leállítva",
            "stopping": "Leállítás folyamatban...",
            "connecting": "Kapcsolódás...",
            "measuring_ping": "Kapcsolódási idők mérése...",
            "measuring_net": "Hálózat mérése...",
            "measuring_audio": "Audio elemzése...",
            "measuring_http": "HTTP fejlécek olvasása...",
            "measuring": "Mérés alatt...",
            "alert": "⚠ Instabil kapcsolat!",
            "alert_ok": "Rendben",
        },
        "stream_state": {
            "public": "Publikus",
            "private": "Privát",
            "public_icy": "Publikus (icy-name)",
            "unknown": "Ismeretlen",
        },
        "misc": {
            "unknown_codec": "Ismeretlen",
            "vbr": "VBR (Változó)",
            "net_error": "Hálózati hiba / Blokkolva",
            "peak": "csúcs",
            "avg_sd": "átlag {avg:.0f} ms / szórás {sd:.1f} ms",
            "buffer_reserve": "{val:.1f} s tartalék",
            "buffer_unknown": "n/a (VBR / ismeretlen névleges bitrate)",
            "no_data": "-",
            "min_avg_max": "{mn:.0f} / {avg:.0f} / {mx:.0f}",
            "min_avg_max_kbps": "{mn:.0f} / {avg:.0f} / {mx:.0f} kbps",
        },
        "msg": {
            "error_title": "Hiba",
            "error_url": "Kérlek, adj meg egy érvényes URL-t!",
            "ffprobe_title": "ffprobe nem található",
            "ffprobe_body": (
                "Az FFmpeg 'ffprobe' program nem található a PATH-ban.\n\n"
                "A program elindul, de az audio metaadatok (codec, bitrate, "
                "csatornák, mintavétel) nem lesznek elérhetők.\n\n"
                "Telepítés: https://www.gyan.dev/ffmpeg/builds/"
            ),
            "log_title": "Napló",
            "log_empty": "Nincs mit menteni – még nem gyűlt adat.",
            "log_save_dialog_title": "Napló mentése",
            "log_filetype_csv": "CSV fájl",
            "log_filetype_all": "Minden fájl",
            "log_saved": "Sikeresen mentve:\n{path}\n({n} minta)",
            "log_save_failed": "Mentés sikertelen:\n{err}",
            "log_clear_confirm_title": "Napló törlése",
            "log_clear_confirm_body": "Biztosan törlöd a rögzített mintákat?",
        },
        "help": {
            "title": "Súgó – Mért paraméterek",
            "close": "Bezárás",
            "sections": [
                ("Ping / Kapcsolódási idő",
                 "A teljes idő, amíg egy új kapcsolat felépül a szerverhez és "
                 "megérkezik az első válasz-byte. Ez az érték négy részre "
                 "bomlik a 'Kapcsolódási idő részletezése' panelen: DNS, "
                 "TCP, TLS és TTFB."),
                ("DNS feloldás / TCP kapcsolódás / TLS handshake / TTFB",
                 "A kapcsolódás négy szakasza külön mérve: mennyi ideig tart "
                 "a domain névfeloldás (DNS), a TCP kapcsolat felépülése, a "
                 "titkosított (HTTPS) kézfogás, és a szerver válaszának első "
                 "byte-jáig eltelt idő (TTFB). Ha valamelyik szakasz "
                 "kiugróan lassú, abból derül ki, hol a szűk keresztmetszet: "
                 "pl. lassú DNS-szolgáltató, távoli szerver, vagy túlterhelt "
                 "backend."),
                ("Ping jitter",
                 "A kapcsolódási idők (ping) változékonysága az utolsó "
                 "mérések alapján. A magas jitter instabil hálózatra utal."),
                ("Valós adatfolyam jitter",
                 "A tényleges audio-adatcsomagok érkezési időközeinek "
                 "szórása letöltés közben. Ez pontosabban tükrözi, amit a "
                 "lejátszó pufferje ténylegesen érez, mint a sima ping "
                 "jitter, mivel közvetlenül a stream-adatok ütemezését "
                 "méri."),
                ("Puffer biztonság",
                 "Másodpercben mutatja, hogy a jelenlegi hálózati sebesség "
                 "mennyi tartalékot biztosít a stream névleges bitrate-jéhez "
                 "képest. Minél magasabb az érték, annál biztonságosabb a "
                 "lejátszás internet-ingadozás esetén."),
                ("Pufferelési megszakítások",
                 "Számláló, amely azt mutatja, hányszor csökkent a puffer "
                 "biztonság kritikus szint alá a mérés indítása óta – ezek "
                 "gyakori akadozásra utalnak."),
                ("Riasztás",
                 "Amikor a ping jitter vagy az adatfolyam jitter túl "
                 "magasra emelkedik, vagy a puffer biztonság kritikus "
                 "szint alá esik, a program figyelmeztető hangjelzést ad "
                 "és pirosan jelzi az állapotot, amíg a kapcsolat nem "
                 "stabilizálódik."),
                ("Valós hálózati sebesség",
                 "A stream letöltése közben ténylegesen mért adatátviteli "
                 "sebesség (kbps), nem az internetkapcsolat elméleti "
                 "maximuma."),
                ("Szerver szoftver",
                 "A HTTP válasz fejléce alapján azonosított stream szerver "
                 "szoftver típusa (pl. Icecast, Shoutcast, nginx)."),
                ("Stream állapot",
                 "Megmutatja, hogy a stream nyilvánosan listázott (publikus) "
                 "rádió-e, vagy privát/relé jellegű forrás."),
                ("Content-Type (MIME)",
                 "A szerver által küldött pontos tartalomtípus, pl. "
                 "audio/mpeg (MP3) vagy audio/aacp (AAC+)."),
                ("Hallgatók száma",
                 "Az Icecast/Shoutcast szerver által jelentett aktuális és "
                 "maximális hallgatószám, ha a szerver ezt közzéteszi. Nem "
                 "minden szerver küldi ezt az adatot."),
                ("Most szól (StreamTitle)",
                 "A szerver által a stream-be ágyazott ICY metaadatból "
                 "kinyert aktuális szám/műsor cím. Csak akkor jelenik meg, "
                 "ha a szerver támogatja és küldi ezt az információt."),
                ("Átirányítások / Feloldott lejátszási lista",
                 "Ha a megadott cím egy .m3u/.pls lejátszási listára vagy "
                 "átirányításra mutat, a program automatikusan feloldja a "
                 "tényleges stream-címet, és ez a mező mutatja, hány "
                 "átirányítás történt, illetve mi a végleges URL."),
                ("Munkamenet összegzés",
                 "A mérés indítása óta összegyűlt statisztika: eltelt idő, "
                 "mintaszám, ping és sebesség minimum/átlag/maximum "
                 "értékei, valamint a legrosszabb 60 másodperces szakasz "
                 "átlagos pingje – ez utóbbi jól mutatja, mikor volt a "
                 "legkritikusabb az adott munkamenet."),
                ("Mérési napló",
                 "A mérések (időbélyeggel, minden fenti paraméterrel "
                 "együtt) CSV fájlba menthetők, így később bizonyítható, "
                 "ha egy rádió vagy az internetkapcsolat rendszeresen "
                 "akadozik egy adott napszakban."),
            ],
        },
    },
    "EN": {
        "app_title": "Online Stream Audio & Network Analyzer",
        "frame_url": " Stream URL ",
        "btn_start": "Start",
        "btn_stop": "Stop",
        "frame_audio": " Current Audio Data ",
        "frame_net": " Network, Latency & Buffer Safety ",
        "frame_http": " HTTP / Stream Metadata ",
        "frame_conn": " Connection Timing Breakdown ",
        "frame_session": " Session Summary ",
        "frame_log": " Measurement Log ",
        "frame_theme": " Appearance (Color Theme) ",
        "tab_audio_net": "Audio && Network",
        "tab_http": "Stream && Connection",
        "tab_session": "Summary",
        "tab_log": "Log && Settings",
        "btn_help": "Help",
        "btn_save_log": "Save Log (CSV)",
        "btn_clear_log": "Clear Log",
        "log_count": "Recorded samples: {n}",
        "theme_auto": "Windows OS (Auto)",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "paste": "Paste",
        "labels": {
            "codec": "Codec:",
            "bitrate": "Nominal Bitrate:",
            "channels": "Channels (Mono/Stereo):",
            "samplerate": "Sample Rate (kHz):",
            "bitdepth": "Bit Depth:",
            "net_speed": "Real Network Speed:",
            "ping": "Ping (last):",
            "chunk_jitter": "Real Stream Jitter:",
            "jitter": "Ping Jitter (last):",
            "ping_stats": "Ping Avg / Std Dev:",
            "buffer": "Buffer Safety:",
            "stalls": "Buffering Interruptions:",
            "alert": "Alert:",
            "timestamp": "Last Update:",
            "status": "Status:",
            "server_sw": "Server Software:",
            "stream_status": "Stream Status:",
            "content_type": "Content-Type (MIME):",
            "server_host": "Server:",
            "listeners": "Listeners (current/max):",
            "stream_title": "Now Playing:",
            "redirects": "Redirect Count:",
            "source_url": "Resolved Playlist Stream:",
            "dns_time": "DNS Lookup:",
            "tcp_time": "TCP Connect:",
            "tls_time": "TLS Handshake:",
            "ttfb_time": "Time to First Byte (TTFB):",
            "total_connect_time": "Total Connection Time:",
            "sess_duration": "Session Duration:",
            "sess_samples": "Samples Recorded:",
            "sess_ping_range": "Ping (min / avg / max):",
            "sess_speed_range": "Speed (min / avg / max):",
            "sess_worst_window": "Worst 60s Window (avg ping):",
            "sess_stalls": "Total Buffering Interruptions:",
        },
        "status": {
            "stopped": "Stopped",
            "stopping": "Stopping...",
            "connecting": "Connecting...",
            "measuring_ping": "Measuring connection timing...",
            "measuring_net": "Measuring network...",
            "measuring_audio": "Analyzing audio...",
            "measuring_http": "Reading HTTP headers...",
            "measuring": "Measuring...",
            "alert": "⚠ Unstable connection!",
            "alert_ok": "OK",
        },
        "stream_state": {
            "public": "Public",
            "private": "Private",
            "public_icy": "Public (icy-name)",
            "unknown": "Unknown",
        },
        "misc": {
            "unknown_codec": "Unknown",
            "vbr": "VBR (Variable)",
            "net_error": "Network error / Blocked",
            "peak": "peak",
            "avg_sd": "avg {avg:.0f} ms / std dev {sd:.1f} ms",
            "buffer_reserve": "{val:.1f} s reserve",
            "buffer_unknown": "n/a (VBR / unknown nominal bitrate)",
            "no_data": "-",
            "min_avg_max": "{mn:.0f} / {avg:.0f} / {mx:.0f}",
            "min_avg_max_kbps": "{mn:.0f} / {avg:.0f} / {mx:.0f} kbps",
        },
        "msg": {
            "error_title": "Error",
            "error_url": "Please enter a valid URL!",
            "ffprobe_title": "ffprobe not found",
            "ffprobe_body": (
                "The FFmpeg 'ffprobe' tool was not found in PATH.\n\n"
                "The program will still run, but audio metadata (codec, "
                "bitrate, channels, sample rate) will not be available.\n\n"
                "Install: https://www.gyan.dev/ffmpeg/builds/"
            ),
            "log_title": "Log",
            "log_empty": "Nothing to save yet – no data collected.",
            "log_save_dialog_title": "Save Log",
            "log_filetype_csv": "CSV file",
            "log_filetype_all": "All files",
            "log_saved": "Successfully saved:\n{path}\n({n} samples)",
            "log_save_failed": "Save failed:\n{err}",
            "log_clear_confirm_title": "Clear Log",
            "log_clear_confirm_body": "Are you sure you want to clear the recorded samples?",
        },
        "help": {
            "title": "Help – Measured Parameters",
            "close": "Close",
            "sections": [
                ("Ping / Connection Time",
                 "The total time it takes to establish a new connection to "
                 "the server and receive the first response byte. This "
                 "value is broken down into four phases on the 'Connection "
                 "Timing Breakdown' panel: DNS, TCP, TLS and TTFB."),
                ("DNS Lookup / TCP Connect / TLS Handshake / TTFB",
                 "The four phases of connecting, measured separately: how "
                 "long the domain name lookup (DNS) takes, how long the TCP "
                 "connection setup takes, the encrypted (HTTPS) handshake, "
                 "and the time until the first byte of the server's "
                 "response (TTFB). If one phase stands out as unusually "
                 "slow, it points to where the bottleneck is: e.g. a slow "
                 "DNS provider, a distant server, or an overloaded "
                 "backend."),
                ("Ping Jitter",
                 "The variability of connection times (ping) over the "
                 "recent measurements. High jitter indicates an unstable "
                 "network."),
                ("Real Stream Jitter",
                 "The variability of the actual audio data packets' "
                 "arrival intervals while downloading. This reflects what "
                 "the player's buffer actually experiences more accurately "
                 "than plain ping jitter, since it directly measures the "
                 "pacing of the stream data itself."),
                ("Buffer Safety",
                 "Shows, in seconds, how much reserve the current network "
                 "speed provides compared to the stream's nominal bitrate. "
                 "The higher the value, the safer playback is against "
                 "internet fluctuations."),
                ("Buffering Interruptions",
                 "A counter showing how many times the buffer safety "
                 "dropped to a critical level since the measurement "
                 "started – frequent increases suggest recurring stutter."),
                ("Alert",
                 "When the ping jitter or stream jitter rises too high, or "
                 "the buffer safety drops below a critical level, the "
                 "program plays a warning sound and shows a red status "
                 "until the connection stabilizes again."),
                ("Real Network Speed",
                 "The data transfer speed actually measured while "
                 "downloading the stream (kbps), not the theoretical "
                 "maximum of your internet connection."),
                ("Server Software",
                 "The type of streaming server software identified from "
                 "the HTTP response headers (e.g. Icecast, Shoutcast, "
                 "nginx)."),
                ("Stream Status",
                 "Shows whether the stream is a publicly listed radio "
                 "station or a private/relay source."),
                ("Content-Type (MIME)",
                 "The exact content type sent by the server, e.g. "
                 "audio/mpeg (MP3) or audio/aacp (AAC+)."),
                ("Listener Count",
                 "The current and maximum listener count reported by the "
                 "Icecast/Shoutcast server, if the server publishes it. "
                 "Not every server sends this information."),
                ("Now Playing (StreamTitle)",
                 "The current track/show title extracted from the ICY "
                 "metadata embedded in the stream by the server. Only "
                 "shown if the server supports and sends this "
                 "information."),
                ("Redirects / Resolved Playlist",
                 "If the given address points to an .m3u/.pls playlist or "
                 "a redirect, the program automatically resolves the "
                 "actual stream address, and this field shows how many "
                 "redirects occurred and what the final URL is."),
                ("Session Summary",
                 "Statistics gathered since the measurement started: "
                 "elapsed time, sample count, min/avg/max ping and speed "
                 "values, and the average ping of the worst 60-second "
                 "window – the latter clearly shows when the session was "
                 "at its most critical."),
                ("Measurement Log",
                 "Measurements (with timestamps, together with every "
                 "parameter above) can be saved to a CSV file, so it can "
                 "later be proven if a radio station or internet "
                 "connection stutters regularly at a given time of day."),
            ],
        },
    },
}


class StreamStats:
    """A mérési ciklus során gyűjtött adatok konténere."""
    WINDOW_SIZE = 60

    def __init__(self):
        self.ping_history = []
        self.last_ping = None
        self.last_jitter = None
        self.last_chunk_jitter = None
        self.stall_count = 0
        self.buffer_health_sec = 0.0
        self.net_speed_kbps = None
        self.peak_net_speed = 0
        self.is_first_measurement = True
        self.alert_active = False

        self.stream_title = None
        self.resolved_url = None
        self.was_playlist = False

        self.session_start = datetime.now()
        self.ping_count = 0
        self.ping_sum = 0.0
        self.ping_min = None
        self.ping_max = None
        self.speed_count = 0
        self.speed_sum = 0.0
        self.speed_min = None
        self.speed_max = None
        self.window_pings = []
        self.worst_window_avg = None

    def reset(self):
        self.__init__()

    def record_ping(self, ping_ms):
        if ping_ms is None:
            return
        self.ping_count += 1
        self.ping_sum += ping_ms
        self.ping_min = ping_ms if self.ping_min is None else min(self.ping_min, ping_ms)
        self.ping_max = ping_ms if self.ping_max is None else max(self.ping_max, ping_ms)

        self.window_pings.append(ping_ms)
        if len(self.window_pings) > self.WINDOW_SIZE:
            self.window_pings.pop(0)
        if len(self.window_pings) == self.WINDOW_SIZE:
            avg = sum(self.window_pings) / self.WINDOW_SIZE
            if self.worst_window_avg is None or avg > self.worst_window_avg:
                self.worst_window_avg = avg

    def record_speed(self, speed_kbps):
        if speed_kbps is None:
            return
        self.speed_count += 1
        self.speed_sum += speed_kbps
        self.speed_min = speed_kbps if self.speed_min is None else min(self.speed_min, speed_kbps)
        self.speed_max = speed_kbps if self.speed_max is None else max(self.speed_max, speed_kbps)


class StreamAnalyzerApp:
    MAX_PING_HISTORY = 10
    LOG_FILE_DEFAULT = "stream_log.csv"
    APP_NAME = "Stream Analyzer"
    APP_VERSION = "v1.1"
    JITTER_ALERT_MS = 150.0
    CHUNK_JITTER_ALERT_MS = 400.0
    BUFFER_ALERT_SEC = 2.0
    TITLE_POLL_EVERY = 5  # StreamTitle/ICY lekérdezés ritkábban, hogy ne terhelje feleslegesen a szervert

    def __init__(self, root):
        self.root = root
        self.root.geometry("700x640")
        self.root.minsize(640, 560)
        self.root.resizable(True, True)

        try:
            self.root.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass

        self.is_running = False
        self.worker_thread = None
        self.loop_counter = 0
        self.stats = StreamStats()
        self.log_rows = []

        self.theme_mode = tk.StringVar(value="Auto")
        self.lang_var = tk.StringVar(value="HU")
        self.current_lang = self.lang_var.get()

        self.create_widgets()
        self.setup_context_menu()
        self.update_theme()
        self.poll_system_theme()
        self.apply_language()

        # ffprobe figyelmeztetés (ha nincs, a program fut, csak az audio adatok maradnak "-")
        if not ffprobe_available():
            self.root.after(500, self._warn_ffprobe_missing)

    def _warn_ffprobe_missing(self):
        m = self.tr("msg")
        messagebox.showwarning(m["ffprobe_title"], m["ffprobe_body"])

    # ---------- Fordítás ----------
    def tr(self, *path):
        node = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["HU"])
        for p in path:
            node = node[p]
        return node

    def apply_language(self):
        self.current_lang = self.lang_var.get()
        t = TRANSLATIONS[self.current_lang]

        self.root.title(t["app_title"])
        self.link_frame.configure(text=t["frame_url"])
        self.data_frame.configure(text=t["frame_audio"])
        self.net_frame.configure(text=t["frame_net"])
        self.http_frame.configure(text=t["frame_http"])
        self.conn_frame.configure(text=t["frame_conn"])
        self.session_frame.configure(text=t["frame_session"])
        self.log_frame.configure(text=t["frame_log"])
        self.theme_frame.configure(text=t["frame_theme"])

        for i, key in enumerate(("tab_audio_net", "tab_http", "tab_session",
                                 "tab_log")):
            self.notebook.tab(i, text=t[key])

        self.btn_toggle.configure(
            text=t["btn_stop"] if self.is_running else t["btn_start"])
        self.btn_help.configure(text=t["btn_help"])
        self.btn_save_log.configure(text=t["btn_save_log"])
        self.btn_clear_log.configure(text=t["btn_clear_log"])

        for key, lbl in self.labels_dict.items():
            if key in t["labels"]:
                lbl.configure(text=t["labels"][key])

        for mode, key in (("Auto", "theme_auto"), ("Light", "theme_light"),
                          ("Dark", "theme_dark")):
            self.theme_radios[mode].configure(text=t[key])

        self.context_menu.entryconfig(0, label=t["paste"])

        self._update_log_count_label()

        if not self.is_running:
            self.info_variables["status"].set(t["status"]["stopped"])
            self.info_variables["alert"].set(t["misc"]["no_data"])

    # ---------- Téma ----------
    def get_windows_theme(self):
        try:
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(
                registry,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "Light" if value == 1 else "Dark"
        except Exception:
            return "Light"

    def _current_theme_name(self):
        mode = self.theme_mode.get()
        return self.get_windows_theme() if mode == "Auto" else mode

    def _apply_dark_titlebar(self, window, dark):
        # Windows 10 1809+ / 11: a natív fejléc (title bar) sötétítése.
        if sys.platform != "win32":
            return
        try:
            import ctypes
            window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            value = ctypes.c_int(1 if dark else 0)
            for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (új/régi build)
                res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(value), ctypes.sizeof(value))
                if res == 0:
                    break
        except Exception:
            pass

    def _theme_colors(self):
        current_theme = self._current_theme_name()
        if current_theme == "Dark":
            return {
                "bg": "#1e1e1e", "fg": "#ffffff",
                "entry_bg": "#3d3d3d", "accent": "#64b5f6",
                "separator": "#aaaaaa", "warn": "#ff8a80",
            }
        return {
            "bg": "#f0f0f0", "fg": "#000000",
            "entry_bg": "#ffffff", "accent": "#0056b3",
            "separator": "gray", "warn": "#c62828",
        }

    def update_theme(self):
        colors = self._theme_colors()
        bg_color, fg_color = colors["bg"], colors["fg"]
        entry_bg, accent_color = colors["entry_bg"], colors["accent"]
        warn_color = colors["warn"]

        self.root.config(bg=bg_color)
        for frame in (self.top_bar, self.link_frame, self.data_frame,
                      self.net_frame, self.http_frame, self.conn_frame,
                      self.session_frame, self.theme_frame, self.log_frame,
                      self.tab_audio_net, self.tab_http, self.tab_session,
                      self.tab_log, self.footer_frame):
            frame.configure(style="TFrame")

        self.footer_name_lbl.configure(background=bg_color, foreground=fg_color)
        self.footer_copy_lbl.configure(background=bg_color, foreground=fg_color)

        self.url_entry.configure(background=entry_bg, foreground=fg_color,
                                 insertbackground=fg_color)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("TFrame", background=bg_color)
        style.configure("TLabelframe", background=bg_color, foreground=fg_color)
        style.configure("TLabelframe.Label", background=bg_color,
                        foreground=fg_color, font=("Arial", 10, "bold"))
        style.configure("TLabel", background=bg_color, foreground=fg_color)
        style.configure("TRadiobutton", background=bg_color, foreground=fg_color)
        style.configure("TButton", font=("Arial", 9))
        style.configure("TNotebook", background=bg_color, borderwidth=0)
        style.configure("TNotebook.Tab", background=entry_bg, foreground=fg_color)
        style.map("TNotebook.Tab", background=[("selected", bg_color)])

        for lbl in self.labels_dict.values():
            lbl.configure(background=bg_color, foreground=fg_color)

        self._apply_dark_titlebar(self.root, self._current_theme_name() == "Dark")

        accent_keys = {"net_speed", "ping", "jitter", "chunk_jitter",
                       "buffer", "stalls"}
        warn_keys = {"jitter", "chunk_jitter", "stalls", "alert"}
        for key, val_lbl in self.values_dict.items():
            if key in warn_keys:
                color = warn_color
            elif key in accent_keys:
                color = accent_color
            else:
                color = fg_color
            val_lbl.configure(background=bg_color, foreground=color)

    def poll_system_theme(self):
        if self.theme_mode.get() == "Auto":
            self.update_theme()
        self.root.after(2000, self.poll_system_theme)

    # ---------- Widgetek ----------
    def create_widgets(self):
        t = TRANSLATIONS[self.current_lang]

        # Felső sáv: nyelvváltás + súgó
        self.top_bar = ttk.Frame(self.root, padding=(15, 10, 15, 0))
        self.top_bar.pack(fill="x")

        lang_box = ttk.Frame(self.top_bar)
        lang_box.pack(side="left")
        ttk.Radiobutton(lang_box, text="HU", variable=self.lang_var,
                        value="HU", command=self.apply_language).pack(
                            side="left", padx=(0, 4))
        ttk.Radiobutton(lang_box, text="EN", variable=self.lang_var,
                        value="EN", command=self.apply_language).pack(
                            side="left")

        self.btn_help = ttk.Button(self.top_bar, text=t["btn_help"],
                                   command=self.show_help)
        self.btn_help.pack(side="right")

        self.link_frame = ttk.LabelFrame(self.root, text=t["frame_url"],
                                         padding=10)
        self.link_frame.pack(fill="x", padx=15, pady=8)

        self.url_entry = tk.Entry(self.link_frame, width=50, font=("Arial", 10),
                                  bd=1, relief="solid")
        self.url_entry.pack(side="left", padx=5, expand=True, fill="x")
        self.url_entry.insert(0, "http://stream.radioparadise.com/rock-flacm")

        self.btn_toggle = ttk.Button(self.link_frame, text=t["btn_start"],
                                     command=self.toggle_monitoring)
        self.btn_toggle.pack(side="right", padx=5)

        # Lábléc: szoftver név/verzió balra, copyright jobbra
        self.footer_frame = ttk.Frame(self.root, padding=(15, 2, 15, 6))
        self.footer_frame.pack(side="bottom", fill="x")

        self.footer_name_lbl = ttk.Label(
            self.footer_frame, text=f"{self.APP_NAME} {self.APP_VERSION}",
            font=("Arial", 8))
        self.footer_name_lbl.pack(side="left")

        self.footer_copy_lbl = ttk.Label(
            self.footer_frame, text="2026 © gidano", font=("Arial", 8))
        self.footer_copy_lbl.pack(side="right")

        # Fő tabfüzet
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        self.tab_audio_net = ttk.Frame(self.notebook, padding=6)
        self.tab_http = ttk.Frame(self.notebook, padding=6)
        self.tab_session = ttk.Frame(self.notebook, padding=6)
        self.tab_log = ttk.Frame(self.notebook, padding=6)

        self.notebook.add(self.tab_audio_net, text=t["tab_audio_net"])
        self.notebook.add(self.tab_http, text=t["tab_http"])
        self.notebook.add(self.tab_session, text=t["tab_session"])
        self.notebook.add(self.tab_log, text=t["tab_log"])

        self.info_variables, self.labels_dict, self.values_dict = {}, {}, {}

        # -- Tab 1: Audio & Hálózat --
        self.data_frame = ttk.LabelFrame(self.tab_audio_net,
                                         text=t["frame_audio"], padding=10)
        self.data_frame.pack(fill="x", pady=(0, 8))
        audio_label_keys = ["codec", "bitrate", "channels", "samplerate",
                            "bitdepth"]
        self._build_label_rows(self.data_frame, t, audio_label_keys,
                               start_row=0, reuse_dicts=True)

        self.net_frame = ttk.LabelFrame(self.tab_audio_net,
                                        text=t["frame_net"], padding=10)
        self.net_frame.pack(fill="x")
        net_label_keys = ["net_speed", "ping", "chunk_jitter", "jitter",
                          "ping_stats", "buffer", "stalls", "alert",
                          "timestamp", "status"]
        self._build_label_rows(self.net_frame, t, net_label_keys, start_row=0,
                               reuse_dicts=True)
        self.info_variables["status"].set(t["status"]["stopped"])
        self.info_variables["alert"].set(t["misc"]["no_data"])

        # -- Tab 2: Stream & Kapcsolat --
        self.http_frame = ttk.LabelFrame(self.tab_http, text=t["frame_http"],
                                         padding=10)
        self.http_frame.pack(fill="x", pady=(0, 8))
        http_label_keys = ["server_sw", "stream_status", "content_type",
                           "server_host", "listeners", "stream_title",
                           "redirects", "source_url"]
        self._build_label_rows(self.http_frame, t, http_label_keys,
                               start_row=0, reuse_dicts=True)

        self.conn_frame = ttk.LabelFrame(self.tab_http, text=t["frame_conn"],
                                         padding=10)
        self.conn_frame.pack(fill="x")
        conn_label_keys = ["dns_time", "tcp_time", "tls_time", "ttfb_time",
                           "total_connect_time"]
        self._build_label_rows(self.conn_frame, t, conn_label_keys,
                               start_row=0, reuse_dicts=True)

        # -- Tab 3: Összegzés --
        self.session_frame = ttk.LabelFrame(self.tab_session,
                                            text=t["frame_session"],
                                            padding=10)
        self.session_frame.pack(fill="x")
        session_label_keys = ["sess_duration", "sess_samples",
                              "sess_ping_range", "sess_speed_range",
                              "sess_worst_window", "sess_stalls"]
        self._build_label_rows(self.session_frame, t, session_label_keys,
                               start_row=0, reuse_dicts=True)

        # -- Tab 4: Napló & Beállítások --
        self.log_frame = ttk.LabelFrame(self.tab_log, text=t["frame_log"],
                                        padding=8)
        self.log_frame.pack(fill="x", pady=(0, 8))

        self.lbl_log_count = ttk.Label(
            self.log_frame, text=t["log_count"].format(n=0), font=("Arial", 9))
        self.lbl_log_count.pack(side="left", padx=5)

        self.btn_save_log = ttk.Button(self.log_frame, text=t["btn_save_log"],
                                       command=self.save_log_csv)
        self.btn_save_log.pack(side="right", padx=5)
        self.btn_clear_log = ttk.Button(self.log_frame, text=t["btn_clear_log"],
                                        command=self.clear_log)
        self.btn_clear_log.pack(side="right", padx=5)

        self.theme_frame = ttk.LabelFrame(self.tab_log, text=t["frame_theme"],
                                          padding=5)
        self.theme_frame.pack(fill="x")
        self.theme_radios = {}
        for mode, key in (("Auto", "theme_auto"), ("Light", "theme_light"),
                          ("Dark", "theme_dark")):
            rb = ttk.Radiobutton(self.theme_frame, text=t[key],
                                 variable=self.theme_mode, value=mode,
                                 command=self.update_theme)
            rb.pack(side="left", padx=15, expand=True)
            self.theme_radios[mode] = rb

    def _build_label_rows(self, parent, t, keys, start_row=0, reuse_dicts=False):
        if not reuse_dicts:
            self.info_variables, self.labels_dict, self.values_dict = {}, {}, {}

        for i, key in enumerate(keys, start=start_row):
            bold = key in ("status", "net_speed", "ping", "jitter",
                           "chunk_jitter", "buffer", "stalls", "alert")
            lbl = ttk.Label(parent, text=t["labels"][key],
                            font=("Arial", 10, "bold" if bold else "normal"))
            lbl.grid(row=i, column=0, sticky="w", pady=3)
            self.labels_dict[key] = lbl

            var = tk.StringVar(value="-")
            self.info_variables[key] = var

            val_lbl = ttk.Label(parent, textvariable=var, wraplength=380,
                                justify="left",
                                font=("Arial", 10, "bold" if bold else "normal"))
            val_lbl.grid(row=i, column=1, sticky="w", padx=20, pady=3)
            self.values_dict[key] = val_lbl

    # ---------- Súgó ----------
    def show_help(self):
        t = self.tr("help")
        colors = self._theme_colors()

        win = tk.Toplevel(self.root)
        win.title(t["title"])
        win.geometry("580x620")
        win.configure(bg=colors["bg"])
        win.transient(self.root)
        win.grab_set()
        self._apply_dark_titlebar(win, self._current_theme_name() == "Dark")

        container = tk.Frame(win, bg=colors["bg"])
        container.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(container)
        scrollbar.pack(side="right", fill="y")

        text = tk.Text(container, wrap="word", padx=16, pady=14,
                       font=("Arial", 10), relief="flat",
                       bg=colors["bg"], fg=colors["fg"],
                       highlightthickness=0, insertbackground=colors["fg"],
                       yscrollcommand=scrollbar.set, cursor="arrow")
        text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text.yview)

        text.tag_configure("heading", font=("Arial", 11, "bold"),
                           foreground=colors["accent"], spacing1=10,
                           spacing3=4)
        text.tag_configure("body", font=("Arial", 10), spacing3=14)

        for heading, body in t["sections"]:
            text.insert("end", heading + "\n", "heading")
            text.insert("end", body + "\n", "body")

        text.config(state="disabled")

        btn_frame = tk.Frame(win, bg=colors["bg"])
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text=t["close"], command=win.destroy).pack()

    # ---------- Kontextusmenü ----------
    def setup_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(
            label=TRANSLATIONS[self.current_lang]["paste"],
            command=self.paste_from_clipboard)
        self.url_entry.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def paste_from_clipboard(self):
        try:
            content = self.root.clipboard_get()
            if content:
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, content.strip())
        except tk.TclError:
            pass

    # ---------- Indítás / leállítás ----------
    def toggle_monitoring(self):
        t = self.tr("status")
        if self.is_running:
            self.is_running = False
            self.btn_toggle.config(text=self.tr("btn_start"))
            self.info_variables["status"].set(t["stopping"])
        else:
            url = self.url_entry.get().strip()
            if not url:
                m = self.tr("msg")
                messagebox.showerror(m["error_title"], m["error_url"])
                return
            self.is_running = True
            self.loop_counter = 0
            self.stats.reset()
            self.btn_toggle.config(text=self.tr("btn_stop"))
            self.info_variables["status"].set(t["connecting"])
            self.worker_thread = threading.Thread(
                target=self.monitor_stream, args=(url,), daemon=True
            )
            self.worker_thread.start()

    # ---------- Lejátszási lista / átirányítás feloldása ----------
    def resolve_playlist_url(self, url, timeout=5.0):
        try:
            with requests.get(url, timeout=timeout, stream=True) as r:
                r.raise_for_status()
                ctype = r.headers.get("content-type", "").lower()
                lower_url = url.lower()
                is_playlist = (
                    lower_url.endswith((".m3u", ".m3u8", ".pls")) or
                    any(x in ctype for x in
                        ("mpegurl", "x-scpls", "vnd.apple.mpegurl"))
                )
                if not is_playlist:
                    return url, False
                raw_bytes = b""
                for chunk in r.iter_content(chunk_size=512):
                    raw_bytes += chunk
                    if len(raw_bytes) >= 4096:
                        break
                content = raw_bytes.decode("utf-8", errors="ignore")
            for ln in content.splitlines():
                ln = ln.strip()
                if not ln or ln.startswith("#"):
                    continue
                if ln.lower().startswith("file1="):
                    ln = ln.split("=", 1)[1].strip()
                if ln.startswith("http://") or ln.startswith("https://"):
                    return ln, True
            return url, False
        except Exception:
            return url, False

    # ---------- Mérések ----------
    def measure_network_speed(self, url, duration=3):
        try:
            start_time = time.time()
            bytes_received = 0
            arrival_times = []
            with requests.get(url, stream=True, timeout=5) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=4096):
                    if not self.is_running:
                        return None, None
                    if chunk:
                        bytes_received += len(chunk)
                        arrival_times.append(time.perf_counter())
                    if time.time() - start_time >= duration:
                        break
            actual = time.time() - start_time
            speed = 0 if actual == 0 else int((bytes_received * 8 / 1000) / actual)

            chunk_jitter_ms = None
            if len(arrival_times) >= 3:
                intervals = [
                    (arrival_times[i] - arrival_times[i - 1]) * 1000.0
                    for i in range(1, len(arrival_times))
                ]
                chunk_jitter_ms = statistics.pstdev(intervals)

            return speed, chunk_jitter_ms
        except Exception:
            return None, None

    def measure_connection_timing(self, url, timeout=5.0):
        sock = None
        try:
            parsed = urlparse(url)
            host = parsed.hostname
            if not host:
                return None
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query

            t_start = time.perf_counter()
            addr_info = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
            t_dns = time.perf_counter()
            dns_ms = (t_dns - t_start) * 1000.0

            family, socktype, proto, _, sockaddr = addr_info[0]
            sock = socket.socket(family, socktype, proto)
            sock.settimeout(timeout)
            t_tcp_start = time.perf_counter()
            sock.connect(sockaddr)
            t_tcp = time.perf_counter()
            tcp_ms = (t_tcp - t_tcp_start) * 1000.0

            tls_ms = 0.0
            if parsed.scheme == "https":
                ctx = ssl.create_default_context()
                t_tls_start = time.perf_counter()
                sock = ctx.wrap_socket(sock, server_hostname=host)
                t_tls = time.perf_counter()
                tls_ms = (t_tls - t_tls_start) * 1000.0

            request_line = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                f"User-Agent: StreamAnalyzer/1.0\r\n"
                f"Accept: */*\r\n"
                f"Connection: close\r\n\r\n"
            ).encode("ascii", errors="ignore")

            t_ttfb_start = time.perf_counter()
            sock.sendall(request_line)
            sock.recv(1)
            t_ttfb = time.perf_counter()
            ttfb_ms = (t_ttfb - t_ttfb_start) * 1000.0

            total_ms = (t_ttfb - t_start) * 1000.0
            return {
                "dns_ms": dns_ms, "tcp_ms": tcp_ms, "tls_ms": tls_ms,
                "ttfb_ms": ttfb_ms, "total_ms": total_ms,
            }
        except Exception:
            return None
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass

    def fetch_http_metadata(self, url, timeout=4.0):
        try:
            state_t = self.tr("stream_state")
            with requests.get(url, stream=True, timeout=timeout,
                              allow_redirects=True) as r:
                r.raise_for_status()
                headers = {k.lower(): v for k, v in r.headers.items()}
                final_url = r.url
                server = headers.get("server", "")
                content_type = headers.get("content-type", "")

                icy_name = headers.get("icy-name", "")
                icy_pub = headers.get("icy-pub")
                icy_listeners = headers.get("icy-listeners")
                icy_max_listeners = headers.get("icy-max-listeners")

                sw = server
                lowered = (server + " " + headers.get("via", "")).lower()
                if "icecast" in lowered:
                    sw = f"Icecast ({server})" if server else "Icecast"
                elif "shoutcast" in lowered or "icy" in headers:
                    sw = f"Shoutcast ({server})" if server else "Shoutcast"
                elif not sw:
                    sw = self.tr("misc", "unknown_codec")

                if icy_pub is not None:
                    state = (state_t["public"] if icy_pub in ("1", "true", "True")
                             else state_t["private"])
                elif icy_name:
                    state = state_t["public_icy"]
                else:
                    state = state_t["unknown"]

                try:
                    host = urlparse(final_url).netloc
                except Exception:
                    host = "-"

                if icy_listeners is not None or icy_max_listeners is not None:
                    listeners = f"{icy_listeners or '-'} / {icy_max_listeners or '-'}"
                else:
                    listeners = "-"

                meta = {
                    "server_sw": sw,
                    "stream_status": state,
                    "content_type": content_type or "-",
                    "server_host": host or "-",
                    "listeners": listeners,
                    "redirects": str(len(r.history)),
                }
                r.close()
                return meta
        except Exception:
            return None

    def fetch_stream_title(self, url, timeout=(3.0, 5.0)):
        try:
            headers = {"Icy-MetaData": "1"}
            with requests.get(url, headers=headers, stream=True,
                              timeout=timeout) as r:
                r.raise_for_status()
                icy_metaint = r.headers.get("icy-metaint")
                if not icy_metaint:
                    return None
                icy_metaint = int(icy_metaint)
                raw = r.raw
                raw.decode_content = True

                skipped = 0
                while skipped < icy_metaint:
                    chunk = raw.read(min(4096, icy_metaint - skipped))
                    if not chunk:
                        return None
                    skipped += len(chunk)

                meta_len_byte = raw.read(1)
                if not meta_len_byte:
                    return None
                meta_len = meta_len_byte[0] * 16
                if meta_len == 0:
                    return None
                meta_data = raw.read(meta_len)
                text = meta_data.decode("utf-8", errors="ignore").strip("\x00")
                match = re.search(r"StreamTitle='([^']*)'", text)
                return match.group(1) if match else None
        except Exception:
            return None

    def probe_audio_stream(self, url):
        if not ffprobe_available():
            return None
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json',
               '-show_streams', '-select_streams', 'a',
               '-probesize', '32768', url]
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=6, startupinfo=startupinfo)
            if result.returncode != 0 or not result.stdout.strip():
                return None
            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            if not streams:
                return None
            s = streams[0]
            codec = s.get("codec_name", self.tr("misc", "unknown_codec")).upper()
            br_raw = s.get("bit_rate")
            bitrate = (f"{int(br_raw) // 1000} kbps" if br_raw
                      else self.tr("misc", "vbr"))
            ch_num = s.get("channels", 0)
            channels = ("Stereo" if ch_num == 2
                        else "Mono" if ch_num == 1
                        else f"{ch_num} ch")
            sr_raw = s.get("sample_rate")
            samplerate = f"{float(sr_raw) / 1000:.1f} kHz" if sr_raw else "-"
            sample_fmt = s.get("sample_fmt", "-")
            if "s16" in sample_fmt:
                bitdepth = "16 bit"
            elif "s32" in sample_fmt or "24" in sample_fmt:
                bitdepth = "24 bit"
            elif "flt" in sample_fmt:
                bitdepth = f"32 bit ({sample_fmt})"
            else:
                bitdepth = sample_fmt

            nominal_br_bps = int(br_raw) if br_raw else None
            return {
                "codec": codec,
                "bitrate": bitrate,
                "channels": channels,
                "samplerate": samplerate,
                "bitdepth": bitdepth,
                "nominal_bps": nominal_br_bps,
            }
        except Exception:
            return None

    # ---------- Jitter / puffer ----------
    def update_ping_stats(self, ping_ms):
        if ping_ms is None:
            return
        self.stats.ping_history.append(ping_ms)
        if len(self.stats.ping_history) > self.MAX_PING_HISTORY:
            self.stats.ping_history.pop(0)

        self.stats.last_ping = ping_ms
        if len(self.stats.ping_history) >= 2:
            diffs = [abs(self.stats.ping_history[i] - self.stats.ping_history[i - 1])
                     for i in range(1, len(self.stats.ping_history))]
            self.stats.last_jitter = statistics.mean(diffs)
        else:
            self.stats.last_jitter = 0.0

    def update_buffer_health(self, net_speed_kbps, nominal_bps):
        # Ha nincs érvényes névleges bitrate (pl. VBR/FLAC stream, amit az
        # ffprobe nem tud egyetlen számmal jellemezni), nincs mihez
        # viszonyítani a mért sebességet - ilyenkor a puffer biztonság
        # "ismeretlen", NEM automatikusan 0 (ami hamis instabilitás-jelzést
        # okozna egy amúgy stabil, nagy sávszélességű kapcsolatnál is).
        if net_speed_kbps is None or not nominal_bps:
            self.stats.buffer_health_sec = None
            return

        nominal_kbps = nominal_bps / 1000.0
        if nominal_kbps <= 0:
            self.stats.buffer_health_sec = None
            return

        margin_kbps = net_speed_kbps - nominal_kbps
        buffer_gain = (margin_kbps / nominal_kbps) * 3.0
        previous = (self.stats.buffer_health_sec
                   if self.stats.buffer_health_sec is not None else 0.0)
        self.stats.buffer_health_sec = max(0.0, previous * 0.5 + buffer_gain * 0.5)

        if net_speed_kbps < nominal_kbps * 0.9 and self.stats.buffer_health_sec <= 0.05:
            self.stats.stall_count += 1

    def check_alert(self):
        jitter_bad = (self.stats.last_jitter is not None and
                     self.stats.last_jitter > self.JITTER_ALERT_MS)
        chunk_jitter_bad = (self.stats.last_chunk_jitter is not None and
                           self.stats.last_chunk_jitter > self.CHUNK_JITTER_ALERT_MS)
        buffer_bad = (self.stats.buffer_health_sec is not None and
                     self.stats.buffer_health_sec < self.BUFFER_ALERT_SEC)
        alert_now = jitter_bad or chunk_jitter_bad or buffer_bad
        if alert_now and not self.stats.alert_active:
            self.root.after(0, self.root.bell)
        self.stats.alert_active = alert_now
        return alert_now

    # ---------- Fő ciklus ----------
    def monitor_stream(self, url_input):
        try:
            resolved_url, was_playlist = self.resolve_playlist_url(url_input)
            self.stats.resolved_url = resolved_url
            self.stats.was_playlist = was_playlist
            url = resolved_url

            while self.is_running:
                self.loop_counter += 1
                status_t = self.tr("status")
                misc_t = self.tr("misc")

                # 1) Kapcsolódási idő (DNS/TCP/TLS/TTFB) — ez adja a "ping"-et is
                self.root.after(0, self.info_variables["status"].set,
                                status_t["measuring_ping"])
                conn_timing = self.measure_connection_timing(url)
                if not self.is_running:
                    break
                ping_ms = conn_timing["total_ms"] if conn_timing else None
                self.update_ping_stats(ping_ms)
                self.stats.record_ping(ping_ms)

                # 2) Hálózat + valós adatfolyam jitter
                self.root.after(0, self.info_variables["status"].set,
                                status_t["measuring_net"])
                net_speed_kbps, chunk_jitter_ms = self.measure_network_speed(
                    url, duration=3)
                if not self.is_running:
                    break

                self.stats.net_speed_kbps = net_speed_kbps
                self.stats.last_chunk_jitter = chunk_jitter_ms
                self.stats.record_speed(net_speed_kbps)
                if net_speed_kbps is not None:
                    if self.stats.is_first_measurement:
                        self.stats.peak_net_speed = net_speed_kbps
                        self.stats.is_first_measurement = False
                    elif net_speed_kbps > self.stats.peak_net_speed:
                        self.stats.peak_net_speed = net_speed_kbps

                # 3) Audio
                self.root.after(0, self.info_variables["status"].set,
                                status_t["measuring_audio"])
                audio = self.probe_audio_stream(url) or {}

                # 4) Puffer
                self.update_buffer_health(net_speed_kbps,
                                          audio.get("nominal_bps"))

                # 5) HTTP / ICY metaadatok
                self.root.after(0, self.info_variables["status"].set,
                                status_t["measuring_http"])
                http_meta = self.fetch_http_metadata(url) or {}

                if self.loop_counter % self.TITLE_POLL_EVERY == 1:
                    title = self.fetch_stream_title(url)
                    if title:
                        self.stats.stream_title = title
                http_meta["stream_title"] = self.stats.stream_title or "-"
                http_meta["source_url"] = (resolved_url if was_playlist
                                           else misc_t["no_data"])

                # 6) Riasztás ellenőrzése
                alert_now = self.check_alert()

                # 7) UI szöveg összeállítása
                current_time = time.strftime("%H:%M:%S")
                if net_speed_kbps is not None:
                    net_text = (f"{net_speed_kbps} kbps ({misc_t['peak']}: "
                               f"{self.stats.peak_net_speed} kbps)")
                else:
                    net_text = misc_t["net_error"]

                ping_text = (f"{ping_ms:.0f} ms" if ping_ms is not None
                            else misc_t["no_data"])
                jitter_text = (f"{self.stats.last_jitter:.1f} ms"
                               if self.stats.last_jitter is not None
                               else misc_t["no_data"])
                chunk_jitter_text = (f"{chunk_jitter_ms:.1f} ms"
                                     if chunk_jitter_ms is not None
                                     else misc_t["no_data"])

                if len(self.stats.ping_history) >= 2:
                    avg = statistics.mean(self.stats.ping_history)
                    sd = statistics.pstdev(self.stats.ping_history)
                    ping_stats_text = misc_t["avg_sd"].format(avg=avg, sd=sd)
                else:
                    ping_stats_text = misc_t["no_data"]

                if self.stats.buffer_health_sec is None:
                    buffer_text = misc_t["buffer_unknown"]
                else:
                    buffer_text = misc_t["buffer_reserve"].format(
                        val=self.stats.buffer_health_sec)
                stalls_text = str(self.stats.stall_count)
                alert_text = (status_t["alert"] if alert_now
                             else status_t["alert_ok"])

                if conn_timing:
                    dns_text = f"{conn_timing['dns_ms']:.0f} ms"
                    tcp_text = f"{conn_timing['tcp_ms']:.0f} ms"
                    tls_text = (f"{conn_timing['tls_ms']:.0f} ms"
                               if conn_timing['tls_ms'] > 0 else misc_t["no_data"])
                    ttfb_text = f"{conn_timing['ttfb_ms']:.0f} ms"
                    total_conn_text = f"{conn_timing['total_ms']:.0f} ms"
                else:
                    dns_text = tcp_text = tls_text = ttfb_text = \
                        total_conn_text = misc_t["no_data"]

                self.root.after(
                    0, self.update_ui,
                    audio.get("codec", "-"),
                    audio.get("bitrate", "-"),
                    audio.get("channels", "-"),
                    audio.get("samplerate", "-"),
                    audio.get("bitdepth", "-"),
                    net_text, ping_text, chunk_jitter_text, jitter_text,
                    ping_stats_text, buffer_text, stalls_text, alert_text,
                    current_time, status_t["measuring"], http_meta,
                    dns_text, tcp_text, tls_text, ttfb_text, total_conn_text,
                )

                self.root.after(0, self.update_session_ui)

                self.append_log_row(
                    current_time=current_time,
                    url=url,
                    net_speed_kbps=net_speed_kbps,
                    ping_ms=ping_ms,
                    jitter_ms=self.stats.last_jitter,
                    chunk_jitter_ms=chunk_jitter_ms,
                    buffer_sec=self.stats.buffer_health_sec,
                    stalls=self.stats.stall_count,
                    audio=audio,
                    http_meta=http_meta,
                    conn_timing=conn_timing,
                )

                time.sleep(1)
        except Exception:
            log_crash(*sys.exc_info())
        finally:
            self.is_running = False
            self.root.after(0, self._reset_ui_after_stop)

    def _reset_ui_after_stop(self):
        self.btn_toggle.config(text=self.tr("btn_start"))
        no_data = self.tr("misc", "no_data")
        self.update_ui("-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-",
                       "-", no_data, "-", self.tr("status", "stopped"), {},
                       "-", "-", "-", "-", "-")

    # ---------- UI ----------
    def update_ui(self, codec, bitrate, channels, samplerate, bitdepth,
                  net_speed, ping, chunk_jitter, jitter, ping_stats, buffer,
                  stalls, alert, timestamp, status, http_meta,
                  dns_time, tcp_time, tls_time, ttfb_time, total_connect_time):
        self.info_variables["codec"].set(codec)
        self.info_variables["bitrate"].set(bitrate)
        self.info_variables["channels"].set(channels)
        self.info_variables["samplerate"].set(samplerate)
        self.info_variables["bitdepth"].set(bitdepth)
        self.info_variables["net_speed"].set(net_speed)
        self.info_variables["ping"].set(ping)
        self.info_variables["chunk_jitter"].set(chunk_jitter)
        self.info_variables["jitter"].set(jitter)
        self.info_variables["ping_stats"].set(ping_stats)
        self.info_variables["buffer"].set(buffer)
        self.info_variables["stalls"].set(stalls)
        self.info_variables["alert"].set(alert)
        self.info_variables["timestamp"].set(timestamp)
        self.info_variables["status"].set(status)

        self.info_variables["dns_time"].set(dns_time)
        self.info_variables["tcp_time"].set(tcp_time)
        self.info_variables["tls_time"].set(tls_time)
        self.info_variables["ttfb_time"].set(ttfb_time)
        self.info_variables["total_connect_time"].set(total_connect_time)

        if http_meta:
            self.info_variables["server_sw"].set(http_meta.get("server_sw", "-"))
            self.info_variables["stream_status"].set(http_meta.get("stream_status", "-"))
            self.info_variables["content_type"].set(http_meta.get("content_type", "-"))
            self.info_variables["server_host"].set(http_meta.get("server_host", "-"))
            self.info_variables["listeners"].set(http_meta.get("listeners", "-"))
            self.info_variables["stream_title"].set(http_meta.get("stream_title", "-"))
            self.info_variables["redirects"].set(http_meta.get("redirects", "-"))
            self.info_variables["source_url"].set(http_meta.get("source_url", "-"))
        else:
            for key in ("server_sw", "stream_status", "content_type",
                       "server_host", "listeners", "stream_title",
                       "redirects", "source_url"):
                self.info_variables[key].set("-")

    def update_session_ui(self):
        misc_t = self.tr("misc")
        s = self.stats

        duration = datetime.now() - s.session_start
        total_sec = int(duration.total_seconds())
        h, rem = divmod(total_sec, 3600)
        m, sec = divmod(rem, 60)
        self.info_variables["sess_duration"].set(f"{h:02d}:{m:02d}:{sec:02d}")
        self.info_variables["sess_samples"].set(str(len(self.log_rows)))

        if s.ping_count > 0:
            avg = s.ping_sum / s.ping_count
            self.info_variables["sess_ping_range"].set(
                misc_t["min_avg_max"].format(mn=s.ping_min, avg=avg, mx=s.ping_max))
        else:
            self.info_variables["sess_ping_range"].set(misc_t["no_data"])

        if s.speed_count > 0:
            avg = s.speed_sum / s.speed_count
            self.info_variables["sess_speed_range"].set(
                misc_t["min_avg_max_kbps"].format(mn=s.speed_min, avg=avg,
                                                   mx=s.speed_max))
        else:
            self.info_variables["sess_speed_range"].set(misc_t["no_data"])

        if s.worst_window_avg is not None:
            self.info_variables["sess_worst_window"].set(
                f"{s.worst_window_avg:.0f} ms")
        else:
            self.info_variables["sess_worst_window"].set(misc_t["no_data"])

        self.info_variables["sess_stalls"].set(str(s.stall_count))

    # ---------- Naplózás ----------
    def append_log_row(self, current_time, url, net_speed_kbps, ping_ms,
                       jitter_ms, chunk_jitter_ms, buffer_sec, stalls, audio,
                       http_meta, conn_timing):
        row = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "time_only": current_time,
            "url": url,
            "net_speed_kbps": net_speed_kbps if net_speed_kbps is not None else "",
            "ping_ms": f"{ping_ms:.1f}" if ping_ms is not None else "",
            "jitter_ms": f"{jitter_ms:.2f}" if jitter_ms is not None else "",
            "chunk_jitter_ms": (f"{chunk_jitter_ms:.2f}"
                                if chunk_jitter_ms is not None else ""),
            "buffer_sec": f"{buffer_sec:.2f}" if buffer_sec is not None else "",
            "stalls": stalls,
            "codec": audio.get("codec", ""),
            "bitrate": audio.get("bitrate", ""),
            "channels": audio.get("channels", ""),
            "samplerate": audio.get("samplerate", ""),
            "bitdepth": audio.get("bitdepth", ""),
            "server_sw": http_meta.get("server_sw", ""),
            "stream_status": http_meta.get("stream_status", ""),
            "content_type": http_meta.get("content_type", ""),
            "server_host": http_meta.get("server_host", ""),
            "listeners": http_meta.get("listeners", ""),
            "stream_title": http_meta.get("stream_title", ""),
            "redirects": http_meta.get("redirects", ""),
            "source_url": http_meta.get("source_url", ""),
            "dns_ms": f"{conn_timing['dns_ms']:.1f}" if conn_timing else "",
            "tcp_ms": f"{conn_timing['tcp_ms']:.1f}" if conn_timing else "",
            "tls_ms": (f"{conn_timing['tls_ms']:.1f}"
                      if conn_timing and conn_timing['tls_ms'] > 0 else ""),
            "ttfb_ms": f"{conn_timing['ttfb_ms']:.1f}" if conn_timing else "",
        }
        self.log_rows.append(row)
        self.root.after(0, self._update_log_count_label)

    def _update_log_count_label(self):
        self.lbl_log_count.config(
            text=self.tr("log_count").format(n=len(self.log_rows)))

    def save_log_csv(self):
        m = self.tr("msg")
        if not self.log_rows:
            messagebox.showinfo(m["log_title"], m["log_empty"])
            return
        path = filedialog.asksaveasfilename(
            title=m["log_save_dialog_title"],
            defaultextension=".csv",
            initialfile=self.LOG_FILE_DEFAULT,
            filetypes=[(m["log_filetype_csv"], "*.csv"),
                      (m["log_filetype_all"], "*.*")],
        )
        if not path:
            return
        try:
            fieldnames = list(self.log_rows[0].keys())
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames,
                                        delimiter=";")
                writer.writeheader()
                writer.writerows(self.log_rows)
            messagebox.showinfo(
                m["log_title"],
                m["log_saved"].format(path=path, n=len(self.log_rows)))
        except Exception as e:
            messagebox.showerror(m["error_title"],
                                 m["log_save_failed"].format(err=e))

    def clear_log(self):
        if not self.log_rows:
            return
        m = self.tr("msg")
        if messagebox.askyesno(m["log_clear_confirm_title"],
                               m["log_clear_confirm_body"]):
            self.log_rows.clear()
            self._update_log_count_label()


# ---------- FŐPROGRAM ----------
def main():
    try:
        root = tk.Tk()
    except Exception:
        log_crash(*sys.exc_info())
        return
    try:
        app = StreamAnalyzerApp(root)
        root.mainloop()
    except Exception:
        log_crash(*sys.exc_info())


if __name__ == "__main__":
    main()
