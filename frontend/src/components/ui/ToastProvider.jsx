import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';

const ToastContext = createContext(null);

const MAX_TOASTS = 4;
const DEFAULT_DURATION = 4000;
const ERROR_DURATION = 6000;

/**
 * Système de toasts maison : `useToast()` expose { show, success, error, info }.
 * Les toasts s'empilent en haut à droite (au-dessus des modales), se ferment
 * seuls après quelques secondes et restent fermables à la main.
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(0);
  const timers = useRef(new Map());

  const dismiss = useCallback((id) => {
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const show = useCallback(({ variant = 'info', message, duration }) => {
    const id = ++nextId.current;
    const delay = duration ?? (variant === 'error' ? ERROR_DURATION : DEFAULT_DURATION);
    setToasts((current) => [...current.slice(-(MAX_TOASTS - 1)), { id, variant, message }]);
    timers.current.set(id, setTimeout(() => dismiss(id), delay));
    return id;
  }, [dismiss]);

  const value = useMemo(() => ({
    show,
    success: (message, duration) => show({ variant: 'success', message, duration }),
    error: (message, duration) => show({ variant: 'error', message, duration }),
    info: (message, duration) => show({ variant: 'info', message, duration }),
  }), [show]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-viewport" aria-live="polite" aria-atomic="false">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast ${toast.variant}`} role="status">
            <span>{toast.message}</span>
            <button
              type="button"
              className="toast-close"
              aria-label="Fermer"
              onClick={() => dismiss(toast.id)}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast doit être utilisé sous <ToastProvider>');
  }
  return context;
}
