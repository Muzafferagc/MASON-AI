"""
autostart.py - MASON'u Windows acilisinda otomatik baslatir.

Kullanim:
    python autostart.py          -> otomatik baslatmayi ACAR (kurar)
    python autostart.py off      -> otomatik baslatmayi KAPATIR (kaldirir)
    python autostart.py status   -> mevcut durumu gosterir

Nasil calisir:
    HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
    kayit anahtarina "MASON" adinda bir giris ekler. Bilgisayar acildiginda
    MASON konsolsuz (pythonw) ve gizli (tepside) baslar; "hey mason" bekler.
"""
import sys
from pathlib import Path

APP_NAME = "MASON"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _command() -> str:
    """pythonw.exe + run.py tam yolu (tirnakli)."""
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    if not pythonw.exists():
        pythonw = exe  # pythonw yoksa python.exe (konsol gorunur)
    run_py = Path(__file__).resolve().parent / "run.py"
    return f'"{pythonw}" "{run_py}"'


def enable() -> None:
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                        winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _command())
    print("[OK] Otomatik baslatma ACILDI.")
    print("     Komut:", _command())
    print("     Bilgisayari yeniden baslatinca MASON arka planda calisacak.")


def disable() -> None:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
        print("[OK] Otomatik baslatma KAPATILDI.")
    except FileNotFoundError:
        print("[i] Zaten kapali (kayit bulunamadi).")


def status() -> None:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
        print("[ACIK] Otomatik baslatma etkin.")
        print("       Komut:", val)
    except FileNotFoundError:
        print("[KAPALI] Otomatik baslatma etkin degil.")


if __name__ == "__main__":
    if sys.platform != "win32":
        print("Bu betik yalnizca Windows icindir.")
        sys.exit(1)
    arg = (sys.argv[1].lower() if len(sys.argv) > 1 else "on")
    if arg in ("off", "disable", "kaldir", "kapat"):
        disable()
    elif arg in ("status", "durum"):
        status()
    else:
        enable()
