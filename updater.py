"""External updater executable; run only after a user-approved download."""
import argparse
import ctypes
from pathlib import Path
import shutil
import subprocess
import sys
import time

def wait_exit(pid):
    if not pid: return
    handle=ctypes.windll.kernel32.OpenProcess(0x00100000,False,pid)
    if handle:
        ctypes.windll.kernel32.WaitForSingleObject(handle,60000)
        ctypes.windll.kernel32.CloseHandle(handle)
    else: time.sleep(2)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--target',required=True)
    parser.add_argument('--source',required=True)
    parser.add_argument('--pid',type=int,default=0)
    args=parser.parse_args()
    target=Path(args.target).resolve()
    source=Path(args.source).resolve()
    if not (source/'Home.exe').is_file() or not (source/'HomeUpdater.exe').is_file():
        return 1
    wait_exit(args.pid)
    target.mkdir(parents=True,exist_ok=True)
    exe=target/'Home.exe'
    backup=target/'Home.exe.bak'
    for attempt in range(20):
        try:
            if backup.exists(): backup.unlink()
            if exe.exists(): exe.replace(backup)
            (source/'Home.exe').replace(exe)
            shutil.copy2(source/'HomeUpdater.exe',target/'HomeUpdater.exe')
            subprocess.Popen([str(exe)],cwd=str(target),close_fds=True)
            return 0
        except OSError:
            if not exe.exists() and backup.exists():
                try: backup.replace(exe)
                except OSError: pass
            time.sleep(1)
    if not exe.exists() and backup.exists(): backup.replace(exe)
    if exe.exists(): subprocess.Popen([str(exe)],cwd=str(target),close_fds=True)
    return 2

if __name__=='__main__':
    sys.exit(main())
