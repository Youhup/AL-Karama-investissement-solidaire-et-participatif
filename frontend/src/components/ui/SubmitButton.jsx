/**
 * Bouton d'action avec état d'attente intégré : désactivé + spinner +
 * libellé de patience pendant `pending`. `className` remplace entièrement
 * la classe par défaut (passer p.ex. "btn-secondary" ou "btn-danger btn-block").
 */
export default function SubmitButton({
  pending = false,
  pendingLabel = 'Patientez...',
  className = 'btn-primary',
  type = 'submit',
  disabled = false,
  children,
  ...rest
}) {
  return (
    <button
      type={type}
      className={className}
      disabled={pending || disabled}
      aria-busy={pending || undefined}
      {...rest}
    >
      {pending ? (
        <>
          <span className="btn-spinner" aria-hidden="true" /> {pendingLabel}
        </>
      ) : (
        children
      )}
    </button>
  );
}
