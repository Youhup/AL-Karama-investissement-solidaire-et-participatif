import { PROJECT_STATUS_LABELS } from '../utils/labels';

export default function StatusBadge({ status }) {
  return <span className={`status-badge ${status}`}>{PROJECT_STATUS_LABELS[status] || status}</span>;
}
