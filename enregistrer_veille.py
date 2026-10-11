"""Valider les données puis pousser sans jamais forcer une branche distante."""
from pathlib import Path
import os
import subprocess
import tempfile

FICHIERS = ['data/' + nom + '.json' for nom in (
    'election', 'programmes', 'status', 'actualites_detectees', 'a_valider', 'publications_auto')]


def git(*args, check=True):
    return subprocess.run(['git', *args], check=check, text=True, capture_output=True)


def valider():
    with tempfile.TemporaryDirectory() as dossier:
        site = str(Path(dossier) / 'site')
        subprocess.run(['python', 'construire_site.py', '--output', site], check=True)
        subprocess.run(['node', 'tests/interface.cjs'], check=True,
                       env={**os.environ, 'SITE_DATA_DIR': site})


def enregistrer():
    valider()
    git('config', 'user.name', 'presidentielle2027-bot')
    git('config', 'user.email', 'actions@users.noreply.github.com')
    git('add', *FICHIERS)
    if git('diff', '--cached', '--quiet', check=False).returncode:
        git('commit', '-m', 'Mise à jour automatique des données et résumés')
    for _ in range(3):
        git('fetch', 'origin', 'main')
        # Ne pas mélanger deux générations de données, même si Git pourrait les fusionner.
        base = git('merge-base', 'HEAD', 'origin/main').stdout.strip()
        changements = git('diff', '--name-only', base, 'origin/main').stdout.splitlines()
        if any(p in FICHIERS for p in changements):
            raise RuntimeError('Données modifiées sur main pendant la veille : passage abandonné sans écrasement ; reprise au prochain passage.')
        rebase = git('rebase', 'origin/main', check=False)
        if rebase.returncode:
            git('rebase', '--abort', check=False)
            raise RuntimeError('Modification concurrente incompatible ; aucun push forcé.')
        valider()
        resultat = git('push', 'origin', 'HEAD:main', check=False)
        if resultat.returncode == 0:
            revision = git('rev-parse', 'HEAD').stdout.strip()
            with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as sortie:
                sortie.write('revision=' + revision + '\n')
            return
    raise RuntimeError('Push refusé après trois tentatives ; vérifier droits, protection et activité de main.')


if __name__ == '__main__':
    enregistrer()
