/**
 * Petit harnais de test pour les composants React, sans framework lourd.
 *
 * Principe : chaque fichier `*.test.jsx` est bundlé par esbuild puis exécuté
 * dans un DOM simulé (jsdom). `fetch` est mocké pour vérifier précisément
 * les requêtes envoyées au backend, sans avoir besoin de le lancer.
 *
 * Lancer : npm test
 */

/**
 * Simule `response.body` (ReadableStream) pour les endpoints consommés en
 * streaming (chat IA) : renvoie tout le texte en un seul chunk, ce qui
 * suffit à exercer le code de lecture progressive côté composant.
 */
function makeStreamBody(text) {
  const encoder = new TextEncoder();
  let sent = false;
  return {
    getReader() {
      return {
        async read() {
          if (sent) return { done: true, value: undefined };
          sent = true;
          return { done: false, value: encoder.encode(text) };
        },
      };
    },
  };
}

export function createFetchMock(routes) {
  const calls = [];

  const fetchMock = async (url, options = {}) => {
    calls.push({ url, options });
    for (const [matcher, handler] of routes) {
      const matches =
        typeof matcher === 'function' ? matcher(url, options) : url.includes(matcher);
      if (matches) {
        const result = typeof handler === 'function' ? handler(url, options) : handler;
        const streamText =
          result.body && typeof result.body === 'object' && 'reply' in result.body
            ? result.body.reply
            : JSON.stringify(result.body);
        return {
          ok: result.status < 400,
          status: result.status,
          json: async () => result.body,
          body: makeStreamBody(streamText),
        };
      }
    }
    return { ok: false, status: 404, json: async () => ({ detail: 'non mocké : ' + url }) };
  };

  fetchMock.calls = calls;
  fetchMock.find = (fragment, method) =>
    calls.find(
      (c) => c.url.includes(fragment) && (!method || (c.options.method || 'GET') === method)
    );
  return fetchMock;
}

/** Renseigne un champ contrôlé par React (input ou textarea). */
export function setValue(el, value) {
  const proto =
    el.tagName === 'TEXTAREA'
      ? window.HTMLTextAreaElement.prototype
      : window.HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value);
  el.dispatchEvent(new Event('input', { bubbles: true }));
}

export function submit(formOrSelector) {
  const form =
    typeof formOrSelector === 'string' ? document.querySelector(formOrSelector) : formOrSelector;
  form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
}

export function click(elOrSelector) {
  const el = typeof elOrSelector === 'string' ? document.querySelector(elOrSelector) : elOrSelector;
  el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
}

export function findByText(selector, text) {
  return [...document.querySelectorAll(selector)].find((el) => el.textContent.includes(text));
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Collecte les assertions et produit un rapport lisible en fin de fichier. */
export function createChecker(suiteName) {
  const failures = [];
  const check = (label, condition) => {
    console.log(`  [${condition ? 'OK ' : 'FAIL'}] ${label}`);
    if (!condition) failures.push(label);
  };
  check.report = () => {
    console.log('');
    if (failures.length) {
      console.log(`RESULT: FAIL (${suiteName}) — ${failures.length} échec(s)`);
      failures.forEach((f) => console.log('   - ' + f));
      process.exitCode = 1;
    } else {
      console.log(`RESULT: ALL PASS (${suiteName})`);
    }
    // Signale au runner que la suite est terminée (évite une attente fixe,
    // qui masquerait un échec survenant dans le dernier test).
    window.__TESTS_DONE__ = true;
  };
  return check;
}
