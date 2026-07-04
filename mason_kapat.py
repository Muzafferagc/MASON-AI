"""
mason_kapat.py - Calisan MASON'u tamamen kapatir (konsol penceresi acmadan).
Masaustu "MASON Kapat" simgesi bunu pythonw ile calistirir.
"""
import subprocess
import sys

CREATE_NO_WINDOW = 0x08000000  # pencere acma

# run.py iceren tum python/pythonw sureclerini sonlandir (bu betik haric:
# komut satirinda 'run.py' gecmedigi icin kendini oldurmez).
PS = (
    "Get-CimInstance Win32_Process | "
    "Where-Object { $_.CommandLine -like '*run.py*' } | "
    "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
)

if __name__ == "__main__":
    if sys.platform != "win32":
        print("Bu betik yalnizca Windows icindir.")
        sys.exit(1)
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", PS],
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception:
        pass
