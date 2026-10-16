"""Prépare un site public sans exposer la file éditoriale ni les extraits de veille."""
import argparse
import json
from pathlib import Path
import shutil
from automatisation import selectionner_articles
from update import SOURCES_JOURNALISTIQUES, fetch
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
CHAMPS_SUIVI = ('ok', 'url', 'notices_detectees', 'detections', 'liens_examines',
                'extractions_vides', 'etat_extraction')


def source_retiree(item):
    host = (urlsplit(item.get('url', '')).hostname or '').lower()
    return (host == 'mediapart.fr' or host.endswith('.mediapart.fr') or
            item.get('source', item.get('nom', '')).casefold() == 'mediapart')


def preparer_site(output, data_dir=None):
    data_dir = Path(data_dir or ROOT / 'data')
    election = json.loads((data_dir / 'election.json').read_text(encoding='utf-8'))
    programmes = json.loads((data_dir / 'programmes.json').read_text(encoding='utf-8'))
    status = json.loads((data_dir / 'status.json').read_text(encoding='utf-8'))
    for champ in ('candidatures', 'sondages', 'actualites', 'sources'):
        if not isinstance(election.get(champ), list) or any(not isinstance(x, dict) for x in election[champ]):
            raise ValueError(f'election.json : structure incorrecte pour {champ}')
    if not isinstance(programmes.get('pretendants'), list):
        raise ValueError('programmes.json : prétendants manquants')
    if not isinstance(status.get('publication_automatique'), bool) or not isinstance(status.get('sources'), dict):
        raise ValueError('status.json : garanties de veille absentes')
    # Retrait demandé : les anciens paquets ne doivent pas réintroduire cette source.
    for champ in ('actualites', 'sources'):
        election[champ] = [item for item in election[champ] if not source_retiree(item)]
    suivi = {key: status.get(key) for key in ('last_checked_utc', 'last_checked_fr')}
    suivi['publication_automatique'] = status['publication_automatique']
    suivi['sondages_automatiques'] = status.get('sondages_automatiques', {})
    suivi['campagnes_automatiques'] = status.get('campagnes_automatiques', {})
    suivi['resumes_automatiques'] = status.get('resumes_automatiques', {})
    if status['publication_automatique']:
        detections = json.loads((data_dir / 'actualites_detectees.json').read_text(encoding='utf-8'))
        queue = json.loads((data_dir / 'a_valider.json').read_text(encoding='utf-8'))
        exclusions = {item['url'] for item in queue if item.get('url') and item.get('statut') in ('Rejeté', 'Rejetée', 'Refusé')}
        snapshot = data_dir / 'publications_auto.json'
        if snapshot.exists():
            selection = json.loads(snapshot.read_text(encoding='utf-8'))
            if selection.get('last_checked_utc') != status['last_checked_utc'] or not isinstance(selection.get('articles'), list):
                raise ValueError('Sélection automatique désynchronisée avec le dernier contrôle')
            articles = selection['articles']
        else:
            # Compatibilité avec les archives antérieures au paquet reproductible.
            articles = selectionner_articles(detections, SOURCES_JOURNALISTIQUES, fetch, exclusions=exclusions)
        # Le site ne publie que les fiches dont le résumé détaillé a passé les contrôles.
        articles = [item for item in articles if item['url'] not in exclusions and not source_retiree(item)
                    and item.get('resume_statut') == 'disponible'
                    and isinstance(item.get('resume'), str) and item['resume'].strip()]
        urls_resumees = {item['url'] for item in articles}
        # Retirer aussi les anciennes fiches automatiques devenues sans résumé.
        election['actualites'] = [item for item in election['actualites']
            if not (item.get('controle') == 'automatique' and item.get('url')
                    and item['url'] not in urls_resumees)]
        existantes = {item.get('url') for item in election['actualites']}
        suivi['resumes_automatiques'] = dict(suivi['resumes_automatiques'],
            resumes=sum(item.get('resume_statut') == 'disponible' for item in articles),
            reutilises=0,
            indisponibles=sum(item.get('resume_statut') != 'disponible' for item in articles))
        election['actualites'] = [item for item in articles if item['url'] not in existantes] + election['actualites']
        suivi['articles_automatiques'] = len(articles)
        suivi['publications_par_media'] = {source['nom']: sum(x['source'] == source['nom'] for x in articles) for source in SOURCES_JOURNALISTIQUES}
        election['eclairages_automatiques'] = articles
        import re
        election['notices_automatiques'] = [
            {'titre': item['titre'], 'url': item['url'], 'date_detection': item.get('date_detection', '')}
            for item in reversed(detections)
            if item.get('type') == 'commission_sondages' and item.get('titre') and
            re.fullmatch(r'https://www\.commission-des-sondages\.fr/notices/medias/fichiers/add/\d+', item.get('url', ''))
        ][:12]
    urls = {item.get('url') for item in election['sources']}
    for source in SOURCES_JOURNALISTIQUES:
        if source['url'] not in urls:
            election['sources'].append({'nom': source['nom'], 'url': source['url'],
                'description': 'Média indépendant / investigation suivi automatiquement. Titres et analyses attribués au média ; enquêtes antérieures datées séparément.'})
    if status['publication_automatique']:
        for source in election['sources']:
            if source.get('nom') == 'Commission des sondages':
                source['description'] = 'Notices officielles suivies automatiquement. Les résultats des tableaux compatibles sont extraits avec leur méthodologie ; les autres formats sont signalés.'
            elif source.get('nom') == 'Verian':
                source['description'] = 'Publications et études suivies. Les résultats ne sont intégrés que lorsque leur tableau et leur méthodologie peuvent être contrôlés automatiquement.'
    suivi['sources'] = {nom: {key: source[key] for key in CHAMPS_SUIVI if key in source}
                        for nom, source in status['sources'].items()
                        if nom.casefold() != 'mediapart' and not source_retiree(source)}
    output = Path(output)
    # Un dossier existant pourrait exposer des anciens fichiers non prévus.
    output.mkdir(parents=True, exist_ok=False)
    (output / 'data').mkdir()
    shutil.copy2(ROOT / 'index.html', output / 'index.html')
    shutil.copy2(data_dir / 'programmes.json', output / 'data' / 'programmes.json')
    (output / 'data' / 'election.json').write_text(json.dumps(election, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'data' / 'suivi.json').write_text(
        json.dumps(suivi, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return suivi


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='_site')
    parser.add_argument('--data-dir', default=str(ROOT / 'data'))
    args = parser.parse_args()
    preparer_site(args.output, args.data_dir)

