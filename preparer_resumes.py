"""Téléchargements officiels épinglés et vérifiés pour le moteur CPU."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import os
import platform
import tarfile
import urllib.request
import zipfile

MODEL = 'Qwen/Qwen2.5-7B-Instruct-GGUF'
REVISION = 'bb5d59e06d9551d752d08b292a50eb208b07ab1f'
RUNTIME = 'b11541'
CACHE = Path(os.environ.get('RESUMES_CACHE', '.cache-modeles/gguf'))
FILES = [
    ('qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf', 'dfce12e3862a5283ccfb88221b48480e58745165de856439950d0f22590580db'),
    ('qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf', '539cf93f78e887edea1c04e2d7d8cdaca9d01dae9c9025bcb8accbe29df3d72a')]
SIZES = dict(zip((nom for nom, _ in FILES), (3993201344, 689872288)))

def segments(url, destination, total):
    taille = 32 * 1024 * 1024
    tranches = [(debut, min(total-1, debut+taille-1)) for debut in range(0, total, taille)]
    def lire(tranche):
        debut, fin = tranche
        part = destination.with_name(destination.name + '.' + str(debut) + '.part')
        if part.exists() and part.stat().st_size == fin-debut+1:
            return part
        for tentative in range(3):
            try:
                req = urllib.request.Request(url, headers={'Range': f'bytes={debut}-{fin}'})
                with urllib.request.urlopen(req, timeout=120) as source, part.open('wb') as sortie:
                    if source.status != 206 or not source.headers.get('Content-Range', '').startswith(f'bytes {debut}-{fin}/'):
                        raise ValueError('Réponse partielle invalide')
                    while bloc := source.read(1024 * 1024):
                        sortie.write(bloc)
                if part.stat().st_size != fin-debut+1:
                    raise ValueError('Segment incomplet')
                return part
            except Exception:
                if tentative == 2:
                    raise
    with ThreadPoolExecutor(max_workers=8) as pool:
        parts = list(pool.map(lire, tranches))
    temporaire = destination.with_suffix('.assemble')
    with temporaire.open('wb') as sortie:
        for part in parts:
            with part.open('rb') as source:
                while bloc := source.read(8 * 1024 * 1024):
                    sortie.write(bloc)
    temporaire.replace(destination)
    # Uniquement les segments créés pour ce téléchargement.
    for part in parts:
        if part.resolve().is_relative_to(CACHE.resolve()):
            part.unlink()

def telecharger(url, destination, empreinte):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        if destination.name in SIZES:
            segments(url, destination, SIZES[destination.name])
        else:
            temporaire = destination.with_suffix(destination.suffix + '.tmp')
            with urllib.request.urlopen(url, timeout=120) as source, temporaire.open('wb') as sortie:
                while bloc := source.read(8 * 1024 * 1024):
                    sortie.write(bloc)
            temporaire.replace(destination)
    with destination.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    if digest != empreinte:
        raise ValueError('Empreinte incorrecte : ' + destination.name)
    print('Téléchargement vérifié : ' + destination.name, flush=True)

def preparer():
    windows = platform.system() == 'Windows'
    asset = 'llama-' + RUNTIME + '-bin-' + ('win-cpu-x64.zip' if windows else 'ubuntu-x64.tar.gz')
    sha = 'cdc0535d11038bb337dfba3c15682050eaa9c07aedd0f915b4c09e8a8e8c0a5c' if windows else '36ca310be4405acb7ba59b32dbdce32bb9cd7b1ef95358997b7eaed2c6f0188b'
    archive = CACHE / asset
    telecharger('https://github.com/ggml-org/llama.cpp/releases/download/' + RUNTIME + '/' + asset, archive, sha)
    dossier = CACHE / ('llama-' + RUNTIME)
    dossier.mkdir(parents=True, exist_ok=True)
    if windows:
        with zipfile.ZipFile(archive) as z:
            for nom in z.namelist():
                if not (dossier / nom).resolve().is_relative_to(dossier.resolve()):
                    raise ValueError('Chemin archive invalide')
            z.extractall(dossier)
    else:
        with tarfile.open(archive) as z:
            z.extractall(dossier, filter='data')
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(telecharger, 'https://huggingface.co/' + MODEL + '/resolve/' + REVISION + '/' + nom, CACHE / nom, sha) for nom, sha in FILES]
        for job in jobs:
            job.result()
    return next(dossier.rglob('llama-server.exe' if windows else 'llama-server')), CACHE / FILES[0][0]

if __name__ == '__main__':
    preparer()
