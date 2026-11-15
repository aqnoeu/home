"""GitHub Releases update checker for Home Windows."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from io import BytesIO
from PySide6.QtCore import QThread, Signal

OWNER, REPO = 'aqnoeu', 'home'
LATEST = f'https://api.github.com/repos/{OWNER}/{REPO}/releases/latest'
VERSION = '0.7.0'
ASSET = 'Home-Windows.zip'
SUMS = 'SHA256SUMS.txt'
LIMIT = 90 * 1024 * 1024

def version_tuple(s):
    try:
        parts = s.removeprefix('v').split('.')
        if len(parts) != 3: return (0, 0, 0)
        return tuple(int(x) for x in parts)
    except (ValueError, AttributeError):
        return (0, 0, 0)

def fetch(url, limit=LIMIT):
    req = urllib.request.Request(url, headers={'User-Agent':'Home-Windows-Updater/0.7','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        if response.url.split('/')[2] not in ('github.com','api.github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'):
            raise ValueError('Servidor de download inesperado')
        data = response.read(limit+1)
    if len(data)>limit: raise ValueError('Arquivo excede o limite')
    return data

def release_info():
    d = json.loads(fetch(LATEST,200000))
    if d.get('draft') or d.get('prerelease') or version_tuple(d.get('tag_name',''))<=version_tuple(VERSION):
        return None
    assets = {a['name']:a['browser_download_url'] for a in d.get('assets',[])}
    for name in (ASSET,SUMS):
        if name not in assets or not assets[name].startswith(f'https://github.com/{OWNER}/{REPO}/releases/download/'):
            raise ValueError('Release sem pacote oficial')
    return {'version':d['tag_name'],'notes':d.get('body','')[:3000],'zip':assets[ASSET],'sums':assets[SUMS]}

def stage_update(info):
    data = fetch(info['zip'])
    expected = None
    for line in fetch(info['sums'],10000).decode('ascii').splitlines():
        fields=line.strip().split()
        if len(fields)>=2 and fields[-1].lstrip('*')==ASSET: expected=fields[0].lower()
    if not expected or hashlib.sha256(data).hexdigest()!=expected:
        raise ValueError('Checksum SHA-256 invalido')
    staged=Path(tempfile.mkdtemp(prefix='home_update_'))
    try:
        with zipfile.ZipFile(BytesIO(data)) as z:
            if set(z.namelist())!={'Home.exe','HomeUpdater.exe'}:
                raise ValueError('Pacote contem arquivos inesperados')
            for name in ('Home.exe','HomeUpdater.exe'):
                with z.open(name) as src,(staged/name).open('wb') as dst:
                    shutil.copyfileobj(src,dst)
        return staged
    except BaseException:
        shutil.rmtree(staged,ignore_errors=True)
        raise

def launch_update(staged):
    if not getattr(sys,'frozen',False):
        raise RuntimeError('Instalacao automatica disponivel apenas no Home.exe')
    target=Path(sys.executable).resolve().parent
    subprocess.Popen([str(staged/'HomeUpdater.exe'),'--target',str(target),'--source',str(staged),'--pid',str(os.getpid())],cwd=str(staged),close_fds=True)

class UpdateWorker(QThread):
    checked=Signal(object)
    staged=Signal(object)
    failed=Signal(str)
    def __init__(self,action='check',info=None,parent=None):
        super().__init__(parent)
        self.action,self.info=action,info
    def run(self):
        try:
            if self.action=='check': self.checked.emit(release_info())
            else: self.staged.emit(stage_update(self.info))
        except Exception as exc:
            self.failed.emit(str(exc))
