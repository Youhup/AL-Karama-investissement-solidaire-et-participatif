import { apiFetch } from './client';

export function getRefundPlan(projectId) {
  return apiFetch(`/projects/${projectId}/refund-plan`);
}

export function createRefundPlan(projectId, payload) {
  return apiFetch(`/projects/${projectId}/refund-plan`, { method: 'POST', body: payload });
}

export function deliverInstallment(installmentId) {
  return apiFetch(`/refund-installments/${installmentId}/deliver`, { method: 'POST' });
}
