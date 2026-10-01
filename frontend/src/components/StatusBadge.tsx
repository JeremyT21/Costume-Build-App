import { STATUS_LABELS } from '../labels';
import type { Status } from '../types';

interface StatusBadgeProps {
  status: Status;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`badge badge-${status}`}>{STATUS_LABELS[status]}</span>;
}
