import { apiFetch } from './client';

export function listMyInvestments() {
  return apiFetch('/investments/me');
}

export function listRefundAllocations(investmentId) {
  return apiFetch(`/investments/${investmentId}/refund-allocations`);
}
