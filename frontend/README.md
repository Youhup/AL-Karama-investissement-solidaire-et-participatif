# Frontend — Al Karama (React + Vite)

## Note sur `npm audit`

`npm audit` signale 2 vulnérabilités liées à esbuild/vite. Elles ne
concernent que le **serveur de développement** de Vite (pas le build de
production) et ne sont pas exploitables en développement local. Le
correctif automatique (`npm audit fix --force`) imposerait Vite 8, un
changement majeur qui casserait la configuration ; on garde donc Vite 5,
stable et testé. Versions figées (non flottantes) dans `package.json`
pour une installation reproductible.

## Structure

```
src/
  api/
    client.js                  # apiFetch/apiUpload + gestion du JWT
    chat.js, investments.js, projects.js, refunds.js
  components/
    Navbar.jsx, Footer.jsx
    ZelligeRosette.jsx         # signature décorative (hero)
    ZelligeProgressRing.jsx    # anneau de progression réutilisable
    ProjectCard.jsx, StatusBadge.jsx
    ChatWidget.jsx, ChatMarkdown.jsx
    RequireAuth.jsx            # garde de route par rôle
  context/
    AuthContext.jsx
  pages/
    Home.jsx, Login.jsx, Register.jsx
    Projects.jsx, ProjectDetail.jsx, DeposerProjet.jsx
    MyProjects.jsx, ProjectManage.jsx, MyPortfolio.jsx
    AdminDashboard.jsx, AdminProjectReview.jsx
    EnConstruction.jsx         # page 404 (route "*")
  styles/
    global.css                 # tous les tokens de design (couleurs, typo)
  utils/
    geometry.js                # trigonométrie partagée (polarPoint)
    funding.js, labels.js
  App.jsx
  main.jsx
```

## Lancer en local

```bash
npm install
npm run dev        # http://localhost:5173
npm test           # suite de tests dans un DOM simulé (25 assertions)
```

## Tests

`test/parcours.test.jsx` couvre les 6 parcours principaux (connexion,
dépôt de projet, investissement, portefeuille, revue admin, chat IA),
vérifie précisément les requêtes envoyées au backend (méthode, en-têtes,
corps) — c'est là que se cachent les bugs d'intégration silencieux, par
exemple le corps `x-www-form-urlencoded` exigé par l'auth OAuth2 de
FastAPI, ou le `Content-Type` absent d'un upload multipart.

Le harnais est dans `test/helpers.js` (fetch mocké, DOM simulé jsdom,
aucun navigateur requis), le runner est `test/run.mjs`.

## Identité visuelle

Tokens définis dans `src/styles/global.css` (`:root`) :

| Rôle | Variable | Usage |
|---|---|---|
| Fond | `--sable` / `--sable-clair` | Page, cartes |
| Texte | `--cedre` / `--cedre-clair` | Titres, corps de texte |
| Action | `--rouge` / `--rouge-fonce` | CTA principal, anneau de progression |
| Système | `--vert` / `--vert-fonce` | Navigation, liens, bande "comment ça marche" |
| Accent | `--safran` | Détails dorés (contours, anneau extérieur de la rosace) |

Le composant `ZelligeRosette` régénère la géométrie de l'étoile à 8 branches
en JS/SVG (aucune image statique) — les tuiles s'animent en cascade via la
classe CSS `.tile` définie dans `global.css`.

`ZelligeProgressRing` reprend le même vocabulaire visuel (traits de "joint"
dorés) pour représenter le pourcentage financé d'un projet — utilisé dans
`ProjectCard` mais réutilisable partout où un pourcentage doit être affiché
(page détail projet, tableau de bord porteur, etc.).

## Authentification

- `src/context/AuthContext.jsx` — état global (`user`, `login`, `register`, `logout`),
  token JWT persisté dans `localStorage`
- `src/api/client.js` — attention : `POST /auth/login` doit être envoyé en
  `x-www-form-urlencoded` (exigence de `OAuth2PasswordRequestForm` côté
  FastAPI), alors que tous les autres endpoints attendent du JSON — les
  deux cas sont gérés séparément (`apiFetch` vs `loginRequest`)
- `src/components/RequireAuth.jsx` — à utiliser pour protéger les futures
  pages (`/deposer`, `/mes-projets`, `/admin`...) :
  ```jsx
  <Route path="/mes-projets" element={
    <RequireAuth roles={['porteur']}><MesProjets /></RequireAuth>
  } />
  ```
- Variable d'environnement `VITE_API_URL` (créer un fichier `.env` à la
  racine) pour pointer vers le backend, sinon `http://localhost:8000` par défaut

## Dépôt de projet (porteur)

- `/deposer` — formulaire de création (titre, description, secteur, montant,
  durée de collecte, ville/région) → `POST /projects`, redirige vers la
  page de gestion du dossier créé
- `/mes-projets/:id` — gestion du dossier : upload de documents (multipart,
  `POST /projects/{id}/documents`), suppression tant que le statut est
  `brouillon`, puis soumission (`POST /projects/{id}/submit`)
- `src/api/projects.js` regroupe tous les appels liés aux projets/secteurs/
  documents ; `apiUpload` dans `client.js` gère spécifiquement le
  multipart (ne pas fixer `Content-Type`, le navigateur doit générer le
  boundary lui-même)
- Nécessite l'endpoint backend `GET /sectors` (ajouté pour peupler le
  menu déroulant du formulaire)

## Explorer & investir

- `/projets` — liste publique (pas besoin d'être connecté) des projets
  ouverts au financement, réutilise `ProjectCard` avec le vrai
  pourcentage calculé depuis `amount_raised`/`amount_requested`
- `/projets/:id` — détail du projet + formulaire d'investissement,
  visible par tous mais le formulaire n'apparaît que pour un compte
  investisseur connecté (sinon CTA de connexion)
- `ZelligeProgressRing` accepte maintenant une prop `size` (utilisé en
  grand format sur la page de détail, en petit sur les cartes)
- Backend : `GET /projects` est passé en authentification optionnelle
  (`get_optional_user`) pour permettre la consultation publique, tout en
  gardant `POST /investments` réservé aux investisseurs connectés

## Tableaux de bord

- `/mes-projets` (porteur) — tous ses dossiers à tous les stades, via
  `GET /projects/mine` (nouveau, distinct de la liste publique qui ne
  montre jamais les brouillons)
- `/mon-portefeuille` (investisseur) — investissements enrichis avec le
  titre/statut de chaque projet (`GET /investments/me` + `GET /projects/{id}`
  en parallèle), total investi, et suivi détaillé du remboursement en
  nature échéance par échéance pour les projets `en_remboursement`/`clos`
  (`GET /investments/{id}/refund-allocations`, enrichi côté backend avec
  la date et le numéro d'échéance)
- La Navbar affiche désormais un lien vers le bon tableau de bord selon
  le rôle connecté

## Espace admin

- `/admin` — tous les dossiers, ceux en attente de validation (`a_valider`)
  remontés en premier
- `/admin/projects/:id` — description, documents, **rapport de l'IA
  agentique** (score de pertinence, score de risque de fraude, verdict,
  liste des failles détectées), puis décision humaine (valider/rejeter +
  note) — la décision reste toujours un acte humain, jamais automatique
- Backend : nouveau `GET /admin/projects`, et le rapport d'analyse est
  désormais sérialisé via un vrai schéma Pydantic (`AIAnalysisReportOut`)
  plutôt que renvoyé comme objet SQLAlchemy brut — plus sûr et plus
  prévisible sur le typage des champs JSONB (`findings`)

## Widget de chat IA

- `ChatWidget.jsx` — bulle flottante montée globalement dans `App.jsx`
  (visible sur toutes les pages), conversation créée paresseusement au
  premier message envoyé, contexte (`visiteur`/`porteur`/`investisseur`)
  déduit automatiquement du rôle connecté via `useAuth()`
- Backend : deux bugs corrigés à cette occasion — `POST /chat/conversations`
  exigeait une authentification alors que les visiteurs anonymes doivent
  pouvoir l'utiliser (`get_optional_user` au lieu de `get_current_user`),
  et `POST .../messages` recevait le message en paramètre de requête
  plutôt qu'en corps JSON (nouveau schéma `ChatMessageIn`)
- La maquette statique qui était dans la section ESS de la page d'accueil
  a été retirée (elle devenait trompeuse à côté du vrai widget)
