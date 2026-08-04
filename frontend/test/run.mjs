/**
 * Runner des tests frontend.
 *
 * Bundle chaque `test/*.test.jsx` avec esbuild (déjà présent via Vite),
 * puis l'exécute dans un DOM simulé jsdom. Aucun navigateur requis.
 *
 *   npm test
 */
import { build } from 'esbuild';
import { JSDOM } from 'jsdom';
import { readdirSync, readFileSync, mkdtempSync } from 'fs';
import { tmpdir } from 'os';
import path from 'path';

const TEST_DIR = 'test';
const files = readdirSync(TEST_DIR).filter((f) => f.endsWith('.test.jsx'));

if (files.length === 0) {
  console.error('Aucun fichier de test trouvé dans test/');
  process.exit(1);
}

const outDir = mkdtempSync(path.join(tmpdir(), 'fe-tests-'));
let failed = false;

for (const file of files) {
  const outfile = path.join(outDir, file.replace('.jsx', '.js'));

  await build({
    entryPoints: [path.join(TEST_DIR, file)],
    bundle: true,
    platform: 'browser',
    format: 'iife',
    jsx: 'automatic',
    outfile,
    logLevel: 'error',
    // `import.meta.env` n'existe pas hors du serveur Vite : on fournit la valeur
    define: { 'import.meta.env.VITE_API_URL': '"http://localhost:8000"' },
  });

  const dom = new JSDOM('<!doctype html><html><body><div id="app"></div></body></html>', {
    url: 'http://localhost/',
    runScripts: 'outside-only',
    pretendToBeVisual: true,
  });

  // Remonte les logs du DOM simulé vers la console Node
  dom.window.console = console;
  dom.window.process = { exitCode: 0 };
  // jsdom n'expose pas TextEncoder/TextDecoder sur `window` (contrairement à
  // un vrai navigateur) — nécessaires pour lire un flux de réponse chunké.
  dom.window.TextEncoder = TextEncoder;
  dom.window.TextDecoder = TextDecoder;

  console.log(`\n──────── ${file} ────────`);
  dom.window.__TESTS_DONE__ = false;
  dom.window.eval(readFileSync(outfile, 'utf8'));

  // Attend le signal de fin émis par check.report(), avec un garde-fou
  // pour ne pas bloquer indéfiniment si la suite plante en cours de route.
  const TIMEOUT_MS = 30000;
  const started = Date.now();
  while (!dom.window.__TESTS_DONE__) {
    if (Date.now() - started > TIMEOUT_MS) {
      console.error(`\n${file} : délai dépassé (${TIMEOUT_MS} ms) — suite interrompue.`);
      failed = true;
      break;
    }
    await new Promise((r) => setTimeout(r, 50));
  }
  if (dom.window.process.exitCode !== 0) failed = true;
}

console.log('');
if (failed) {
  console.error('Des tests ont échoué.');
  process.exit(1);
}
console.log('Tous les tests frontend sont passés.');
