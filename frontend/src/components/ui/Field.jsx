/**
 * Champ de formulaire standard : label + contrôle + erreur inline + hint.
 * Reproduit exactement le markup `.field` historique pour que le CSS
 * existant s'applique tel quel.
 *
 *   <Field id="email" label="Adresse email" type="email" value={v} onChange={...} />
 *   <Field as="select" id="sector_id" label="Secteur" ...>{options}</Field>
 *   <Field as="textarea" id="notes" label="Note (optionnel)" rows={4} ... />
 */
export default function Field({ id, label, as = 'input', hint, error, children, className = '', ...rest }) {
  const Tag = as;
  const describedBy = [error && `${id}-error`, hint && `${id}-hint`].filter(Boolean).join(' ');
  return (
    <div className={`field ${className}`.trim()}>
      <label htmlFor={id}>{label}</label>
      <Tag
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy || undefined}
        {...rest}
      >
        {as === 'select' ? children : undefined}
      </Tag>
      {error && (
        <p className="field-error" id={`${id}-error`} role="alert">{error}</p>
      )}
      {hint && (
        <p className="field-hint" id={`${id}-hint`}>{hint}</p>
      )}
    </div>
  );
}
