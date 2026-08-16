import Modal from './Modal';
import SubmitButton from './SubmitButton';

/**
 * Dialogue de confirmation avant action importante.
 *
 *   <ConfirmDialog open={!!confirm} danger title="Retirer ce document ?"
 *     message="Cette action est définitive." confirmLabel="Retirer"
 *     pending={pending} onConfirm={fn} onCancel={fn} />
 *
 * Pour les actions destructives (`danger`), le focus initial est mis sur
 * « Annuler » afin qu'un Entrée réflexe ne confirme pas la suppression.
 */
export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirmer',
  cancelLabel = 'Annuler',
  danger = false,
  pending = false,
  onConfirm,
  onCancel,
}) {
  if (!open) return null;
  return (
    <Modal
      title={title}
      onClose={pending ? () => {} : onCancel}
      closeOnOverlay={!pending}
      initialFocus={danger ? '.btn-secondary' : undefined}
    >
      {typeof message === 'string' ? <p>{message}</p> : message}
      <div className="modal-actions">
        <SubmitButton
          type="button"
          className={danger ? 'btn-danger btn-block' : 'btn-primary btn-block'}
          pending={pending}
          onClick={onConfirm}
        >
          {confirmLabel}
        </SubmitButton>
        <button
          type="button"
          className="btn-secondary btn-block"
          disabled={pending}
          onClick={onCancel}
        >
          {cancelLabel}
        </button>
      </div>
    </Modal>
  );
}
