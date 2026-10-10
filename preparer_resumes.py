"""Téléchargements officiels épinglés et vérifiés pour le moteur CPU."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import os
import platform
import tarfile
import urllib.request
import zipfile

MODEL = 'Qwen/Qwen2.5-14B-Instruct-GGUF'
REVISION = 'b466e1f8c07172155743e8e1307507d8a4f91fbd'
RUNTIME = 'b11541'
CACHE = Path(os.environ.get('RESUMES_CACHE', str(Path(__file__).resolve().parent / '.cache-modeles/gguf14')))
FILES = [
    ('qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf', 'a09ea5e7b1eafb1b30b241726c3cc3c905c96f14ad41e246ffa5f44e53904f68'),
    ('qwen2.5-14b-instruct-q4_k_m-00002-of-00003.gguf', '21b9457d079680d284e90ef69607c4b2d8ef64a09d4729cb7b5e1357bdba41ae'),
    ('qwen2.5-14b-instruct-q4_k_m-00003-of-00003.gguf', 'c8d37006760a387a35216e070e6664d7da927f10be8eb870fef2e3d4833d9976')]
SIZES = dict(zip((nom for nom, _ in FILES), (3991999872, 3989373504, 1006737120)))

def segments(url, destination, total):
    # Écrire directement à l'offset voulu : pas de deuxième copie de 9 Go.
    taille = 32 * 1024 * 1024
    temporaire = destination.with_suffix('.tmp')
    if not temporaire.exists() or temporaire.stat().st_size != total:
        with temporaire.open('wb') as sortie:
            sortie.truncate(total)
    tranches = [(debut, min(total-1, debut+taille-1)) for debut in range(0, total, taille)]
    def lire(tranche):
        debut, fin = tranche
        for tentative in range(3):
            try:
                req = urllib.request.Request(url, headers={'Range': f'bytes={debut}-{fin}'})
                with urllib.request.urlopen(req, timeout=120) as source, temporaire.open('r+b') as sortie:
                    if source.status != 206 or not source.headers.get('Content-Range', '').startswith(f'bytes {debut}-{fin}/'):
                        raise ValueError('Réponse partielle invalide')
                    sortie.seek(debut)
                    lus = 0
                    while bloc := source.read(1024 * 1024):
                        if lus + len(bloc) > fin-debut+1:
                            raise ValueError('Segment trop volumineux')
                        sortie.write(bloc)
                        lus += len(bloc)
                if lus != fin-debut+1:
                    raise ValueError('Segment incomplet')
                return
            except Exception:
                if tentative == 2:
                    raise
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lire, tranches))
    temporaire.replace(destination)


def telecharger(url, destination, empreinte):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        with destination.open('rb') as source:
            valide = hashlib.file_digest(source, 'sha256').hexdigest() == empreinte
        if not valide:
            # Ce fichier de cache ne doit jamais être exécuté ni chargé.
            destination.unlink()
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
