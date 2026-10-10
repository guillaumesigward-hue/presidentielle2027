// Run the actual page script against the committed data and a minimal DOM.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('index.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const elements = {};
const buttons = ['ecole', 'sante', 'energie', 'fiscalite', 'ecologie'].map(theme => ({
  dataset: { theme }, classList: { add() {}, remove() {} },
  setAttribute() {}, addEventListener(event, callback) { this.click = callback; }
}));
const requests = [];
const context = vm.createContext({
  console, Date, document: {
    getElementById(id) { return elements[id] ||= { innerHTML: '' }; },
    querySelectorAll() { return buttons; }
  }, fetch: async url => {
    requests.push(url);
    const path = url.split('?')[0];
    if (path === 'data/suivi.json') {
      return { ok: true, json: async () => ({
        last_checked_utc: new Date().toISOString(), last_checked_fr: '10 octobre 2026',
        sources: { blast: { ok: true, etat_extraction: 'partielle', extractions_vides: 6 },
          disclose: { ok: false } }
      }) };
    }
    return { ok: true, json: async () => JSON.parse(fs.readFileSync(path, 'utf8')) };
  }
});
vm.runInContext(script, context);
setImmediate(() => {
  assert.equal(requests.length, 3);
  assert(!requests.some(url => url.includes('a_valider')));
  for (const id of ['candidatures-grid', 'sondages-grid', 'programmes-grid', 'actualites-grid', 'sources-grid']) {
    assert(elements[id].innerHTML.includes('<article'), id);
    assert(!elements[id].innerHTML.includes('undefined'), id);
  }
  for (const button of buttons) {
    button.click();
    assert(elements['programmes-grid'].innerHTML.includes('<article'));
  }
  assert.equal(vm.runInContext('lienSource("javascript:alert(1)", "x")', context), '');
  assert(vm.runInContext('escapeHtml("<script>")', context).includes('&lt;'));
  assert(vm.runInContext('afficherSolidite({solidite_documentaire:"bad"})', context).includes('Non évaluée'));
  assert(elements.suivi.innerHTML.includes('extraction partielle'));
  assert(elements.suivi.innerHTML.includes('Source indisponible'));
  vm.runInContext(`electionData.eclairages_automatiques = [{source:"Disclose",titre:"Gouvernement et pollution",url:"https://disclose.ngo/fr/article/test",date_publication:"2026-06-18",themes:["Écologie"],candidats_mentions:[]}];
    electionData.notices_automatiques = [{titre:"Notice officielle",url:"https://www.commission-des-sondages.fr/notices/medias/fichiers/add/1",date_detection:"10 octobre 2026"}];
    themeActif = "ecologie"; afficherProgrammes(); afficherSondages();`, context);
  assert(elements['programmes-grid'].innerHTML.includes('Disclose'));
  assert(elements['notices-automatiques'].innerHTML.includes('Notice officielle'));
  vm.runInContext('suiviData = null; afficherSuivi()', context);
  assert(elements.suivi.innerHTML.includes('restent consultables'));
  vm.runInContext('suiviData = {last_checked_utc:"2000-01-01",sources:{}}; afficherSuivi()', context);
  assert(elements.suivi.innerHTML.includes('dernier contrôle est ancien'));
  console.log('Interface : sections, cinq thèmes, publication et liens vérifiés.');
});
