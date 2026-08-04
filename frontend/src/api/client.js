export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'al_karama_token';

/**
 * `detail` est une chaîne pour nos HTTPException custom, mais FastAPI
 * renvoie une liste d'erreurs Pydantic (422) pour les validations de schéma
 * — on extrait le premier message dans ce cas pour rester affichable
 * directement dans les formulaires.
 */
export function extractDetail(errorBody, fallback) {
  if (typeof errorBody?.detail === 'string') return errorBody.detail;
  if (Array.isArray(errorBody?.detail) && errorBody.detail[0]?.msg) {
    return errorBody.detail[0].msg.replace(/^Value error,\s*/, '');
  }
  return fallback;
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

/**
 * Appel API générique en JSON. Attache automatiquement le token Bearer
 * s'il existe. Lève une erreur avec le message renvoyé par FastAPI
 * (`detail`) pour un affichage direct dans les formulaires.
 */
export async function apiFetch(path, { method = 'GET', body, headers = {} } = {}) {
  const token = getToken();

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let detail = `Erreur ${response.status}`;
    try {
      detail = extractDetail(await response.json(), detail);
    } catch {
      // pas de corps JSON, on garde le message générique
    }
    throw new Error(detail);
  }

  if (response.status === 204) return null;
  return response.json();
}

/**
 * Upload multipart (FormData) — utilisé pour les documents. On ne fixe
 * PAS de Content-Type ici : le navigateur doit générer lui-même le
 * boundary du multipart/form-data.
 */
export async function apiUpload(path, formData) {
  const token = getToken();
  const response = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  if (!response.ok) {
    let detail = `Erreur ${response.status}`;
    try {
      detail = extractDetail(await response.json(), detail);
    } catch {
      // pas de corps JSON
    }
    throw new Error(detail);
  }
  return response.json();
}

/**
 * Télécharge un fichier protégé (Bearer requis, donc pas d'`<a href>` direct)
 * et déclenche le téléchargement/l'ouverture navigateur via un blob local.
 */
export async function apiDownload(path, filename) {
  const token = getToken();
  const response = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    let detail = `Erreur ${response.status}`;
    try {
      detail = extractDetail(await response.json(), detail);
    } catch {
      // pas de corps JSON
    }
    throw new Error(detail);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename || '';
  link.target = '_blank';
  link.rel = 'noopener';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/**
 * Connexion : FastAPI (OAuth2PasswordRequestForm) attend un corps
 * x-www-form-urlencoded avec les champs `username` et `password`,
 * pas du JSON — d'où ce cas séparé.
 */
export async function loginRequest(email, password) {
  const form = new URLSearchParams();
  form.set('username', email);
  form.set('password', password);

  const response = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || 'Email ou mot de passe incorrect');
  }
  return response.json(); // { access_token, token_type }
}
