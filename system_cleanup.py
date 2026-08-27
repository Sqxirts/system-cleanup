"""Interactive disk cleanup: Recycle Bin, Windows Update cache, user Temp.

Scans all three, shows sizes, asks yes/no per category, then clears what
you approve. Windows Update cache is owned by SYSTEM/TrustedInstaller, so
clearing it needs admin rights - if this isn't running elevated, it
relaunches just that one step in an elevated window (UAC prompt) rather
than elevating the whole script.

Run it:
    python system_cleanup.py
"""

import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

UPDATE_CACHE = Path(r"C:\Windows\SoftwareDistribution\Download")


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def human_gb(num_bytes: int) -> float:
    return round(num_bytes / (1024**3), 2)


def dir_size(path: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path, onerror=lambda e: None):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                pass
    return total


class _ShQueryRbInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("i64Size", ctypes.c_int64),
        ("i64NumItems", ctypes.c_int64),
    ]


def recycle_bin_size() -> int:
    info = _ShQueryRbInfo()
    info.cbSize = ctypes.sizeof(_ShQueryRbInfo)
    result = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
    return info.i64Size if result == 0 else 0


def empty_recycle_bin() -> None:
    no_confirmation, no_progress_ui, no_sound = 0x1, 0x2, 0x4
    flags = no_confirmation | no_progress_ui | no_sound
    ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)


def clear_temp(temp_dir: Path) -> None:
    for entry in temp_dir.iterdir():
        try:
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry, ignore_errors=True)
            else:
                entry.unlink(missing_ok=True)
        except OSError:
            pass  # locked by a running app - just skip it


def clear_update_cache_now() -> None:
    """Assumes admin rights are already in effect."""
    subprocess.run(["net", "stop", "wuauserv"], check=False)
    subprocess.run(["net", "stop", "bits"], check=False)
    shutil.rmtree(UPDATE_CACHE, ignore_errors=True)
    UPDATE_CACHE.mkdir(parents=True, exist_ok=True)
    subprocess.run(["net", "start", "bits"], check=False)
    subprocess.run(["net", "start", "wuauserv"], check=False)
    print("Windows Update cache cleared.")


def clear_update_cache_elevated() -> None:
    script = str(Path(__file__).resolve())
    params = f'"{script}" --clear-update-cache-only'
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    print("Admin window opened - approve the UAC prompt to finish clearing the Windows Update cache.")


def ask(prompt: str) -> bool:
    return input(f"{prompt} [y/N] ").strip().lower() == "y"


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--clear-update-cache-only":
        clear_update_cache_now()
        input("Press Enter to close...")
        return

    print("Scanning...")
    recycle_gb = human_gb(recycle_bin_size())
    temp_dir = Path(os.environ.get("TEMP", ""))
    temp_gb = human_gb(dir_size(temp_dir)) if temp_dir.exists() else 0.0
    update_gb = human_gb(dir_size(UPDATE_CACHE)) if UPDATE_CACHE.exists() else 0.0

    print(f"\nRecycle Bin:          {recycle_gb} GB")
    print(f"User Temp:            {temp_gb} GB  ({temp_dir})")
    print(f"Windows Update cache: {update_gb} GB  ({UPDATE_CACHE})\n")

    if recycle_gb > 0 and ask("Empty Recycle Bin? (permanent, not recoverable)"):
        empty_recycle_bin()
        print("Recycle Bin cleared.")

    if temp_gb > 0 and ask("Clear user Temp folder? (files in use are skipped)"):
        clear_temp(temp_dir)
        print("Temp folder cleared.")

    if update_gb > 0 and ask("Clear Windows Update cache? (needs admin - UAC prompt)"):
        if is_admin():
            clear_update_cache_now()
        else:
            clear_update_cache_elevated()

    print("\nDone.")


if __name__ == "__main__":
    main()
