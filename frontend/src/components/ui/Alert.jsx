const VARIANT_CLASS = {
  error: 'form-error',
  success: 'success-banner',
  info: 'info-banner',
};

/**
 * Bannière de feedback. Rend null si `children` est vide, ce qui permet
 * d'écrire `<Alert variant="error">{error}</Alert>` sans condition autour.
 */
export default function Alert({ variant = 'info', children, className = '' }) {
  if (!children) return null;
  return (
    <div
      className={`${VARIANT_CLASS[variant] || VARIANT_CLASS.info} ${className}`.trim()}
      role={variant === 'error' ? 'alert' : 'status'}
    >
      {children}
    </div>
  );
}
