import { useEffect, useId, useRef } from 'react';

const FOCUSABLE = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/**
 * Primitive de modale accessible : focus initial dans la carte, piège du
 * Tab, Échap pour fermer, restauration du focus à la fermeture. Rendue
 * inline (pas de portal) : la position fixed suffit visuellement et les
 * tests jsdom interrogent le document entier.
 *
 * `initialFocus` : sélecteur CSS de l'élément à focaliser à l'ouverture
 * (par défaut, le premier élément focalisable).
 */
export default function Modal({ title, onClose, children, closeOnOverlay = true, initialFocus }) {
  const titleId = useId();
  const cardRef = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    const previouslyFocused = document.activeElement;
    const card = cardRef.current;
    const target = (initialFocus && card?.querySelector(initialFocus)) || card?.querySelector(FOCUSABLE);
    target?.focus();

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        event.stopPropagation();
        onCloseRef.current?.();
        return;
      }
      if (event.key !== 'Tab' || !card) return;
      const focusables = card.querySelectorAll(FOCUSABLE);
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener('keydown', handleKeyDown, true);
    return () => {
      document.removeEventListener('keydown', handleKeyDown, true);
      if (previouslyFocused instanceof HTMLElement) previouslyFocused.focus();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onMouseDown={(event) => {
        if (closeOnOverlay && event.target === event.currentTarget) onCloseRef.current?.();
      }}
    >
      <div className="modal-card" ref={cardRef}>
        <h3 id={titleId}>{title}</h3>
        {children}
      </div>
    </div>
  );
}
