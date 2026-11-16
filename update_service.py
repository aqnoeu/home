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
from PySide6.QtCore import QThread, Signal

OWNER, REPO = 'aqnoeu', 'home'
LATEST = f'https://api.github.com/repos/{OWNER}/{REPO}/releases/latest'
VERSION = '0.7.1'
ASSET = 'Home-Windows.zip'
SUMS = 'SHA256SUMS.txt'
# O executável Windows ganhou o runtime neural Kokoro/ONNX.
# Limite de download comprimido (protegido por SHA-256 e origem permitida).
LIMIT = 1024 * 1024 * 1024
# Limites de extração, para não confiar em metadados de ZIP sem verificações.
MAX_EXTRACTED_FILE = 1536 * 1024 * 1024
MAX_EXTRACTED_TOTAL = 2048 * 1024 * 1024

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

def download_package(url, destination, limit=LIMIT):
    """Baixa em blocos para disco, impondo limite real e calculando SHA-256."""
    req = urllib.request.Request(
        url, headers={'User-Agent': 'Home-Windows-Updater/0.7'})
    digest = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(req, timeout=60) as response:
        if response.url.split('/')[2] not in (
            'github.com', 'api.github.com',
            'release-assets.githubusercontent.com', 'objects.githubusercontent.com'
        ):
            raise ValueError('Servidor de download inesperado')
        with destination.open('wb') as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise ValueError(
                        'Arquivo excede o limite de 1 GB; verifique o tamanho da Release')
                output.write(chunk)
                digest.update(chunk)
    return digest.hexdigest()


def stage_update(info):
    expected = None
    for line in fetch(info['sums'], 10000).decode('ascii').splitlines():
        fields = line.strip().split()
        if len(fields) >= 2 and fields[-1].lstrip('*') == ASSET:
            expected = fields[0].lower()
    if not expected:
        raise ValueError('Checksum SHA-256 ausente')
    staged = Path(tempfile.mkdtemp(prefix='home_update_'))
    archive = staged / ASSET
    try:
        actual = download_package(info['zip'], archive)
        if actual != expected:
            raise ValueError('Checksum SHA-256 invalido')
        with zipfile.ZipFile(archive) as z:
            if set(z.namelist()) != {'Home.exe', 'HomeUpdater.exe'}:
                raise ValueError('Pacote contem arquivos inesperados')
            entries = {item.filename: item for item in z.infolist()}
            if any(item.file_size > MAX_EXTRACTED_FILE for item in entries.values()):
                raise ValueError('Executavel excede o limite de extracao')
            if sum(item.file_size for item in entries.values()) > MAX_EXTRACTED_TOTAL:
                raise ValueError('Pacote excede o limite de extracao')
            for name in ('Home.exe', 'HomeUpdater.exe'):
                with z.open(name) as src, (staged / name).open('wb') as dst:
                    copied = 0
                    while True:
                        chunk = src.read(1024 * 1024)
                        if not chunk:
                            break
                        copied += len(chunk)
                        if copied > MAX_EXTRACTED_FILE:
                            raise ValueError('Executavel excede o limite de extracao')
                        dst.write(chunk)
                    if copied != entries[name].file_size:
                        raise ValueError('Arquivo extraido incompleto')
        archive.unlink()
        return staged
    except BaseException:
        shutil.rmtree(staged, ignore_errors=True)
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
