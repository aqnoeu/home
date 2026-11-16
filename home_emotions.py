"""HOME expression policy. Brand Guidelines 1.2 + approved contextual evolution.

Eyes are unchanged in the official logo; application eyes may express moods
through motion and muted brand tints. No global keylogging or background audio.
"""
import ctypes
import os
import time
from dataclasses import dataclass

EMOTIONS = ("neutro", "raiva", "sonolento", "tedio")
IDLE_SLEEP_SECONDS = 5 * 60
SAME_WINDOW_BORED_SECONDS = 12 * 60
CONVERSATION_HOLD_SECONDS = 15


def normalize_emotion(value):
    return value if isinstance(value, str) and value in EMOTIONS else "neutro"


@dataclass
class ContextState:
    last_activity: float = 0.0
    focused_window: int = 0
    focused_since: float = 0.0
    conversation_emotion: str = "neutro"
    conversation_until: float = 0.0

    def note_conversation(self, emotion, now=None):
        now = time.monotonic() if now is None else now
        self.conversation_emotion = normalize_emotion(emotion)
        self.conversation_until = now + CONVERSATION_HOLD_SECONDS
        self.last_activity = now

    def choose(self, now, charging=False):
        # A reply is always visible while the assistant speaks.
        if now < self.conversation_until:
            return self.conversation_emotion
        # Charging is an operational condition, not an AI-generated emotion.
        if charging:
            return "carregando"
        if self.last_activity and now - self.last_activity >= IDLE_SLEEP_SECONDS:
            return "sonolento"
        if self.focused_since and now - self.focused_since >= SAME_WINDOW_BORED_SECONDS:
            return "tedio"
        return "neutro"


class WindowsContext:
    """Small Win32 queries without a hook, polling keyboard, or saving app titles."""
    class LastInputInfo(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint),
                    ("dwTime", ctypes.c_uint)]

    class SystemPowerStatus(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_ubyte),
            ("BatteryFlag", ctypes.c_ubyte),
            ("BatteryLifePercent", ctypes.c_ubyte),
            ("SystemStatusFlag", ctypes.c_ubyte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong),
        ]

    @staticmethod
    def sample(now=None):
        now = time.monotonic() if now is None else now
        if os.name != "nt":
            return now, 0, False
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            li = WindowsContext.LastInputInfo()
            li.cbSize = ctypes.sizeof(li)
            if user32.GetLastInputInfo(ctypes.byref(li)):
                ticks = int(kernel32.GetTickCount64()) & 0xFFFFFFFF
                elapsed = ((ticks - int(li.dwTime)) & 0xFFFFFFFF) / 1000.0
                last_activity = now - elapsed
            else:
                last_activity = now
            hwnd = int(user32.GetForegroundWindow())
            power = WindowsContext.SystemPowerStatus()
            charging = bool(kernel32.GetSystemPowerStatus(ctypes.byref(power))
                            and power.ACLineStatus == 1
                            and power.BatteryFlag != 128)
            return last_activity, hwnd, charging
        except (OSError, AttributeError, ValueError):
            return now, 0, False
