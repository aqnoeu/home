"""Safe, on-demand Windows diagnostics and allowlisted system panels for HOME.

No arbitrary commands, network scans, logging, telemetry or content uploads.
"""
import ctypes
import os
import shutil
import sys
from pathlib import Path


def _size(n):
    return f"{n / (1024 ** 3):.1f} GB"


def battery_status():
    if sys.platform != "win32":
        return "Bateria: disponível somente no Windows."
    class Power(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_ubyte),
            ("BatteryFlag", ctypes.c_ubyte),
            ("BatteryLifePercent", ctypes.c_ubyte),
            ("SystemStatusFlag", ctypes.c_ubyte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong),
        ]
    state = Power()
    try:
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(state)):
            return "Não consegui consultar a bateria."
        if state.BatteryFlag == 128:
            return "Este computador não informou uma bateria."
        level = ("carga desconhecida" if state.BatteryLifePercent == 255
                 else f"{state.BatteryLifePercent}%")
        energy = ("ligado à tomada" if state.ACLineStatus == 1
                  else "usando bateria" if state.ACLineStatus == 0 else "fonte desconhecida")
        return f"Bateria: {level} · {energy}."
    except (OSError, AttributeError):
        return "Não consegui consultar a bateria."


def memory_status():
    if sys.platform != "win32":
        return "Memória: disponível somente no Windows."
    class Memory(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]
    value = Memory()
    value.dwLength = ctypes.sizeof(Memory)
    try:
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
            return f"RAM disponível: {_size(value.ullAvailPhys)} de {_size(value.ullTotalPhys)}."
    except (OSError, AttributeError):
        pass
    return "Não consegui consultar a memória."


def storage_status():
    if sys.platform != "win32":
        return "Armazenamento: disponível somente no Windows."
    try:
        drive = Path.home().anchor
        total, used, free = shutil.disk_usage(drive)
        return f"Disco {drive}: {_size(free)} livres de {_size(total)}."
    except OSError:
        return "Não consegui consultar o armazenamento."


def network_status():
    if sys.platform != "win32":
        return "Rede: disponível somente no Windows."
    try:
        flags = ctypes.c_ulong(0)
        connected = bool(ctypes.windll.wininet.InternetGetConnectedState(ctypes.byref(flags), 0))
        return ("Windows informa conectividade de rede. Isso não garante acesso à internet."
                if connected else "Windows não informa conexão de rede ativa.")
    except (OSError, AttributeError):
        return "Não consegui consultar a conexão de rede."


def overview():
    return "\n".join((battery_status(), network_status(), memory_status(), storage_status()))


def local_query(sentence):
    """Explicit read-only offline queries; all others return None to use normal routing."""
    import unicodedata
    q = "".join(c for c in unicodedata.normalize("NFKD", sentence.casefold())
                if not unicodedata.combining(c)).strip(" !?.")
    if any(x in q for x in ("estado do pc", "estado do notebook", "diagnostico do pc",
                              "diagnostico do notebook", "informacoes do computador")):
        return overview()
    if any(x in q for x in ("bateria", "carregador", "carregando")):
        return battery_status()
    if any(x in q for x in ("memoria ram", "ram disponivel")):
        return memory_status()
    if any(x in q for x in ("armazenamento", "espaco livre", "espaco no disco")):
        return storage_status()
    if any(x in q for x in ("status da internet", "estado da rede", "internet conectada",
                              "conexao de rede", "rede conectada")):
        return network_status()
    return None


# Applications and system panels are fixed: no untrusted program or URI is accepted.
SYSTEM_PANELS = {
    "wifi_settings": "ms-settings:network-wifi",
    "bluetooth_settings": "ms-settings:bluetooth",
    "sound_settings": "ms-settings:sound",
    "storage_settings": "ms-settings:storagesense",
    "calendar_settings": "ms-settings:dateandtime",
    "clock_app": "ms-clock:",
}


def open_panel(name):
    if sys.platform != "win32" or name not in SYSTEM_PANELS:
        raise ValueError("Ação não autorizada ou plataforma indisponível.")
    os.startfile(SYSTEM_PANELS[name])
