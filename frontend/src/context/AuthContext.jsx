import { createContext, useContext, useEffect, useState } from 'react';
import { apiFetch, getToken, loginRequest, setToken } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadCurrentUser() {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const me = await apiFetch('/auth/me');
        setUser(me);
      } catch {
        // Token expiré ou invalide : on nettoie silencieusement
        setToken(null);
      } finally {
        setLoading(false);
      }
    }
    loadCurrentUser();
  }, []);

  async function login(email, password) {
    const { access_token } = await loginRequest(email, password);
    setToken(access_token);
    const me = await apiFetch('/auth/me');
    setUser(me);
    return me;
  }

  async function register(payload) {
    await apiFetch('/auth/register', { method: 'POST', body: payload });
    // Le endpoint /auth/register ne renvoie pas de token : on enchaîne
    // avec une connexion pour obtenir directement une session active.
    return login(payload.email, payload.password);
  }

  function logout() {
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth doit être utilisé à l’intérieur de <AuthProvider>');
  return ctx;
}
