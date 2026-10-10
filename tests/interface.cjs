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
    return { ok: true, json: async () => JSON.parse(fs.readFileSync(path, 'utf8')) };
  }
});
vm.runInContext(script, context);
setImmediate(() => {
  assert.equal(requests.length, 2);
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
  console.log('Interface : sections, cinq thèmes, publication et liens vérifiés.');
});
