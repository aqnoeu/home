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
RELEASES = f'https://api.github.com/repos/{OWNER}/{REPO}/releases?per_page=100'
VERSION = '2.0.0'
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
    # GitHub /releases/latest pode retornar Android. Selecionar a maior
    # versao Windows *com ambos os assets oficiais*, ignorando tags android-v*.
    import re
    releases = json.loads(fetch(RELEASES, 1800000))
    if not isinstance(releases, list):
        raise ValueError('Resposta de Releases inesperada')
    candidates = []
    for item in releases:
        if item.get('draft') or item.get('prerelease'):
            continue
        tag = item.get('tag_name', '')
        if not re.fullmatch(r'v\d+\.\d+\.\d+', tag):
            continue
        assets = {asset.get('name'): asset.get('browser_download_url', '')
                  for asset in item.get('assets', [])}
        if any(name not in assets or
               not assets[name].startswith(f'https://github.com/{OWNER}/{REPO}/releases/download/')
               for name in (ASSET, SUMS)):
            continue
        candidates.append((version_tuple(tag), item, assets))
    if not candidates:
        return None
    version, item, assets = max(candidates, key=lambda triple: triple[0])
    if version <= version_tuple(VERSION):
        return None
    return {'version': item['tag_name'], 'notes': item.get('body', '')[:3000],
            'zip': assets[ASSET], 'sums': assets[SUMS]}

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
