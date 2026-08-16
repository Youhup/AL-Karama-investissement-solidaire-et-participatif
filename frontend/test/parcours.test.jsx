/**
 * Suite de tests des parcours frontend principaux.
 * Vérifie le rendu ET les requêtes réellement envoyées au backend
 * (format du corps, en-têtes, méthode) — c'est là que se cachent
 * les bugs d'intégration silencieux.
 */
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { createRoot } from 'react-dom/client';
import { AuthProvider } from '../src/context/AuthContext';
import { ToastProvider } from '../src/components/ui/ToastProvider';
import Login from '../src/pages/Login';
import DeposerProjet from '../src/pages/DeposerProjet';
import ProjectDetail from '../src/pages/ProjectDetail';
import MyPortfolio from '../src/pages/MyPortfolio';
import AdminProjectReview from '../src/pages/AdminProjectReview';
import ChatWidget from '../src/components/ChatWidget';
import {
  createFetchMock, setValue, submit, click, findByText, sleep, createChecker,
} from './helpers.js';

const check = createChecker('frontend');
const container = document.getElementById('app');

function render(ui) {
  const root = createRoot(container);
  root.render(ui);
  return root;
}

const ME_INVESTISSEUR = {
  id: 'inv-1', email: 's@t.ma', full_name: 'Sara', role: 'investisseur', is_verified: true,
};

// ---------------------------------------------------------------- Connexion
async function testLogin() {
  console.log('\n=== Connexion ===');
  window.localStorage.clear();
  window.fetch = createFetchMock([
    ['/auth/login', { status: 200, body: { access_token: 'tok', token_type: 'bearer' } }],
    ['/auth/me', { status: 200, body: ME_INVESTISSEUR }],
  ]);

  const root = render(
    <MemoryRouter><AuthProvider><ToastProvider><Login /></ToastProvider></AuthProvider></MemoryRouter>
  );
  await sleep(150);

  setValue(document.getElementById('email'), 's@t.ma');
  setValue(document.getElementById('password'), 'demo1234');
  submit('form');
  await sleep(250);

  const call = window.fetch.find('/auth/login');
  const body = String(call?.options.body);
  check('POST /auth/login envoyé', !!call);
  check(
    'corps en x-www-form-urlencoded (exigence OAuth2 de FastAPI, pas du JSON)',
    call?.options.headers['Content-Type'] === 'application/x-www-form-urlencoded'
      && body.includes('username=s%40t.ma') && body.includes('password=demo1234')
  );
  check('token persisté', window.localStorage.getItem('al_karama_token') === 'tok');
  check('profil rechargé via /auth/me', !!window.fetch.find('/auth/me'));
  root.unmount();
}

// ------------------------------------------------------------ Dépôt projet
async function testDeposerProjet() {
  console.log('\n=== Dépôt de projet ===');
  window.localStorage.setItem('al_karama_token', 'tok');
  window.fetch = createFetchMock([
    ['/auth/me', { status: 200, body: { ...ME_INVESTISSEUR, role: 'porteur' } }],
    ['/sectors', { status: 200, body: [{ id: 3, name: 'Artisanat', description: null }] }],
    [(u, o) => u.endsWith('/projects') && o.method === 'POST',
      { status: 201, body: { id: 'p1', status: 'brouillon' } }],
  ]);

  const root = render(
    <MemoryRouter><AuthProvider><ToastProvider><DeposerProjet /></ToastProvider></AuthProvider></MemoryRouter>
  );
  await sleep(250);

  check('secteurs chargés dans le menu déroulant',
    document.querySelectorAll('#sector_id option').length === 1);

  setValue(document.getElementById('title'), 'Atelier poterie');
  setValue(document.getElementById('description'), 'Description du projet.');
  setValue(document.getElementById('amount_requested'), '18000');
  submit('form');
  await sleep(250);

  const call = window.fetch.find('/projects', 'POST');
  const body = call ? JSON.parse(call.options.body) : {};
  check('POST /projects envoyé', !!call);
  check('sector_id transmis en nombre (pas en chaîne)', typeof body.sector_id === 'number');
  check('amount_requested transmis en nombre', typeof body.amount_requested === 'number');
  root.unmount();
}

// ----------------------------------------------------------- Investissement
async function testInvestissement() {
  console.log('\n=== Investissement ===');
  window.localStorage.setItem('al_karama_token', 'tok');
  let raised = 22500;
  window.fetch = createFetchMock([
    ['/auth/me', { status: 200, body: ME_INVESTISSEUR }],
    ['/sectors', { status: 200, body: [{ id: 1, name: 'Agriculture' }] }],
    [(u, o) => u.includes('/projects/p-safran/investments') && o.method === 'POST',
      (u, o) => { raised += JSON.parse(o.body).amount; return { status: 201, body: { id: 'i1' } }; }],
    // Pas de plan de remboursement ni d'utilisation des fonds déclarée pour
    // ce projet de test : 404, comme le backend le ferait réellement (à
    // placer AVANT le matcher générique ci-dessous, qui matche par
    // sous-chaîne et intercepterait sinon ces deux routes plus précises).
    ['/projects/p-safran/refund-plan', { status: 404, body: { detail: 'Aucun plan' } }],
    ['/projects/p-safran/fund-usage-items', { status: 200, body: [] }],
    ['/projects/p-safran', () => ({
      status: 200,
      body: {
        id: 'p-safran', title: 'Safran de Taliouine', description: 'desc',
        sector_id: 1, amount_requested: 50000, amount_raised: raised,
        status: 'en_financement', city: 'Taliouine',
      },
    })],
  ]);

  const root = render(
    <MemoryRouter initialEntries={['/projets/p-safran']}>
      <AuthProvider>
        <ToastProvider>
          <Routes><Route path="/projets/:id" element={<ProjectDetail />} /></Routes>
        </ToastProvider>
      </AuthProvider>
    </MemoryRouter>
  );
  await sleep(350);

  const before = document.querySelector('.ring-pct')?.textContent;
  check('progression initiale calculée depuis les montants réels (45%)', before === '45%');

  setValue(document.getElementById('amount'), '5000');
  submit('.invest-panel form');
  await sleep(350);

  // La soumission du formulaire ouvre d'abord la modale de consentement au
  // partage de coordonnées (nécessaire à la livraison de la contrepartie en
  // nature) — l'investissement n'est réellement envoyé qu'après ce choix.
  check('modale de consentement affichée avant tout envoi', !!document.querySelector('.modal-overlay'));
  check('rien envoyé avant la confirmation', !window.fetch.find('/investments', 'POST'));
  click('.modal-actions .btn-primary');
  await sleep(350);

  const call = window.fetch.find('/investments', 'POST');
  check('montant envoyé en nombre', call && JSON.parse(call.options.body).amount === 5000);
  check('consentement au partage transmis (bouton "J\'accepte" cliqué)',
    call && JSON.parse(call.options.body).share_contact_consent === true);
  check('progression réactualisée après investissement (55%)',
    document.querySelector('.ring-pct')?.textContent === '55%');
  check('confirmation affichée', container.textContent.includes('Investissement confirmé'));
  root.unmount();
}

// -------------------------------------------------------------- Portefeuille
async function testPortefeuille() {
  console.log('\n=== Portefeuille investisseur ===');
  window.localStorage.setItem('al_karama_token', 'tok');
  window.fetch = createFetchMock([
    ['/auth/me', { status: 200, body: ME_INVESTISSEUR }],
    ['/investments/i-A/refund-allocations', { status: 200, body: [
      { id: 'a1', investment_id: 'i-A', quantity_allocated: 12.5, status: 'livre', delivered_at: '2026-05-25', installment_number: 1, due_date: '2026-05-25' },
      { id: 'a2', investment_id: 'i-A', quantity_allocated: 12.5, status: 'a_venir', delivered_at: null, installment_number: 2, due_date: '2026-06-25' },
    ] }],
    ['/investments/me', { status: 200, body: [
      { id: 'i-A', project_id: 'p-argane', amount: 25000, status: 'confirme', invested_at: '2026-02-01' },
      { id: 'i-B', project_id: 'p-safran', amount: 12500, status: 'confirme', invested_at: '2026-03-01' },
    ] }],
    ['/projects/p-argane', { status: 200, body: { id: 'p-argane', title: 'Coopérative Argane', status: 'en_remboursement' } }],
    ['/projects/p-safran', { status: 200, body: { id: 'p-safran', title: 'Safran de Taliouine', status: 'en_financement' } }],
  ]);

  const root = render(
    <MemoryRouter><AuthProvider><ToastProvider><MyPortfolio /></ToastProvider></AuthProvider></MemoryRouter>
  );
  await sleep(400);

  check('total investi agrégé correctement (37 500 MAD)',
    document.querySelector('.stat-value')?.textContent === '37\u202F500 MAD');
  check('suivi de remboursement proposé uniquement pour le projet en remboursement',
    document.querySelectorAll('.btn-toggle').length === 1);

  click('.btn-toggle');
  await sleep(350);
  const rows = document.querySelectorAll('.allocation-table tbody tr');
  check('échéances affichées', rows.length === 2);
  check('quantité et statut de la 1re échéance corrects',
    rows[0]?.textContent.includes('12.5') && rows[0]?.textContent.includes('Livré'));
  root.unmount();
}

// -------------------------------------------------------------- Revue admin
async function testRevueAdmin() {
  console.log('\n=== Revue admin ===');
  window.localStorage.setItem('al_karama_token', 'tok');
  window.fetch = createFetchMock([
    ['/auth/me', { status: 200, body: { ...ME_INVESTISSEUR, role: 'admin' } }],
    ['/admin/projects/p-x/analysis', { status: 200, body: {
      id: 'r1', project_id: 'p-x', relevance_score: 78, fraud_risk_score: 22,
      verdict: 'a_examiner',
      findings: [{ type: 'document_manquant', severite: 'moyenne', description: 'Aucun devis fourni.' }],
      analyzed_at: '2026-01-01', reviewed_by_admin_id: null, admin_decision: null,
      admin_notes: null, reviewed_at: null,
    } }],
    [(u, o) => u.includes('/admin/projects/p-x/decision') && o.method === 'POST',
      { status: 200, body: { status: 'ok', new_status: 'rejete' } }],
    ['/sectors', { status: 200, body: [{ id: 1, name: 'Élevage' }] }],
    ['/projects/p-x/documents', { status: 200, body: [] }],
    // Pas de plan de remboursement ni d'utilisation des fonds déclarée : 404,
    // comme le backend le ferait réellement (AVANT le matcher générique
    // ci-dessous, qui matche par sous-chaîne et intercepterait sinon ces
    // deux routes plus précises).
    ['/projects/p-x/refund-plan', { status: 404, body: { detail: 'Aucun plan' } }],
    ['/projects/p-x/fund-usage-items', { status: 200, body: [] }],
    ['/projects/p-x', { status: 200, body: {
      id: 'p-x', title: 'Élevage caprin', description: 'desc',
      amount_requested: 25000, status: 'a_valider', city: 'Chefchaouen',
    } }],
  ]);

  const root = render(
    <MemoryRouter initialEntries={['/admin/projects/p-x']}>
      <AuthProvider>
        <ToastProvider>
          <Routes><Route path="/admin/projects/:id" element={<AdminProjectReview />} /></Routes>
        </ToastProvider>
      </AuthProvider>
    </MemoryRouter>
  );
  await sleep(400);

  check('verdict IA traduit en français', document.querySelector('.verdict-badge')?.textContent === 'À examiner');
  const scores = [...document.querySelectorAll('.score-value')].map((s) => s.textContent);
  check('scores de pertinence et de fraude affichés', scores.includes('78') && scores.includes('22'));
  check('faille détectée affichée', !!findByText('.finding-item', 'Aucun devis'));

  click(findByText('.decision-option', 'Rejeter'));
  setValue(document.getElementById('notes'), 'Dossier incomplet.');
  submit('.submit-panel:last-child form');
  await sleep(350);

  // Le rejet est irréversible : une boîte de confirmation s'interpose
  // désormais entre la soumission du formulaire et l'envoi de la décision.
  check('confirmation demandée avant le rejet', !!document.querySelector('.modal-overlay'));
  check('rien envoyé avant la confirmation', !window.fetch.find('/decision', 'POST'));
  click('.modal-actions .btn-danger');
  await sleep(350);

  const body = JSON.parse(window.fetch.find('/decision', 'POST').options.body);
  check('décision et note transmises', body.decision === 'rejete' && body.notes === 'Dossier incomplet.');
  check('confirmation affichée', container.textContent.includes('Décision enregistrée'));
  root.unmount();
}

// ------------------------------------------------------------- Widget chat
async function testChatWidget() {
  console.log('\n=== Widget de chat IA ===');
  window.localStorage.clear(); // visiteur anonyme
  window.fetch = createFetchMock([
    ['/chat/conversations/c-1/messages', { status: 200, body: { reply: "L'ESS privilégie l'utilité collective." } }],
    ['/chat/conversations?', { status: 200, body: { conversation_id: 'c-1' } }],
  ]);

  const root = render(
    <MemoryRouter><AuthProvider><ToastProvider><ChatWidget /></ToastProvider></AuthProvider></MemoryRouter>
  );
  await sleep(150);

  check('panneau fermé au départ', !document.querySelector('.chat-panel'));
  click('.chat-fab');
  await sleep(150);
  check('panneau ouvert au clic', !!document.querySelector('.chat-panel'));
  check('aucune conversation créée tant qu’aucun message n’est envoyé',
    window.fetch.calls.length === 0);

  setValue(document.querySelector('.chat-input-row input'), "C'est quoi l'ESS ?");
  submit('.chat-input-row');
  await sleep(350);

  const startCall = window.fetch.find('/chat/conversations?');
  check('conversation créée au 1er message', !!startCall);
  check('contexte « visiteur » transmis pour un utilisateur non connecté',
    startCall?.url.includes('context_role=visiteur'));
  check('message envoyé en JSON',
    JSON.parse(window.fetch.find('/messages', 'POST').options.body).content === "C'est quoi l'ESS ?");
  check('réponse de l’assistant affichée', container.textContent.includes("L'ESS privilégie"));
  root.unmount();
}

(async () => {
  await testLogin();
  await testDeposerProjet();
  await testInvestissement();
  await testPortefeuille();
  await testRevueAdmin();
  await testChatWidget();
  check.report();
})();
