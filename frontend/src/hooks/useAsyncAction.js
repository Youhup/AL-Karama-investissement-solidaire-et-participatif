import { useCallback, useRef, useState } from 'react';

/**
 * Regroupe le triplet pending/error/run copié-collé dans chaque formulaire.
 *
 *   const save = useAsyncAction(async (...args) => { ...; return data; });
 *   const res = await save.run(args);   // { ok: true, data } | { ok: false, message }
 *
 * `run` ne lève jamais : l'appelant branche sur `res.ok` pour naviguer ou
 * afficher un toast. `setError` reste exposé pour les validations
 * synchrones avant soumission (mots de passe, multiples de 100, etc.).
 */
export function useAsyncAction(fn) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const fnRef = useRef(fn);
  fnRef.current = fn;

  const run = useCallback(async (...args) => {
    setError('');
    setPending(true);
    try {
      const data = await fnRef.current(...args);
      return { ok: true, data };
    } catch (err) {
      setError(err.message);
      return { ok: false, message: err.message };
    } finally {
      setPending(false);
    }
  }, []);

  const reset = useCallback(() => {
    setError('');
    setPending(false);
  }, []);

  return { run, pending, error, setError, reset };
}
