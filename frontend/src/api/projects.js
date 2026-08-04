import { apiDownload, apiFetch, apiUpload } from './client';

export function listProjects() {
  return apiFetch('/projects');
}

export function listMyProjects() {
  return apiFetch('/projects/mine');
}

export function investInProject(projectId, amount, shareContactConsent) {
  return apiFetch(`/projects/${projectId}/investments`, {
    method: 'POST',
    body: { amount, share_contact_consent: shareContactConsent },
  });
}

export function listProjectInvestments(projectId) {
  return apiFetch(`/projects/${projectId}/investments`);
}

export function listSectors() {
  return apiFetch('/sectors');
}

export function createProject(payload) {
  return apiFetch('/projects', { method: 'POST', body: payload });
}

export function getProject(projectId) {
  return apiFetch(`/projects/${projectId}`);
}

export function updateProject(projectId, payload) {
  return apiFetch(`/projects/${projectId}`, { method: 'PATCH', body: payload });
}

export function submitProject(projectId) {
  return apiFetch(`/projects/${projectId}/submit`, { method: 'POST' });
}

export function listDocuments(projectId) {
  return apiFetch(`/projects/${projectId}/documents`);
}

export function uploadDocument(projectId, file, docType) {
  const formData = new FormData();
  formData.append('doc_type', docType);
  formData.append('file', file);
  return apiUpload(`/projects/${projectId}/documents`, formData);
}

export function deleteDocument(documentId) {
  return apiFetch(`/documents/${documentId}`, { method: 'DELETE' });
}

export function downloadDocument(documentId, filename) {
  return apiDownload(`/documents/${documentId}/download`, filename);
}

export function listFundUsageItems(projectId) {
  return apiFetch(`/projects/${projectId}/fund-usage-items`);
}

export function createFundUsageItem(projectId, payload) {
  return apiFetch(`/projects/${projectId}/fund-usage-items`, { method: 'POST', body: payload });
}

export function deleteFundUsageItem(itemId) {
  return apiFetch(`/projects/fund-usage-items/${itemId}`, { method: 'DELETE' });
}

export function listAllProjectsAdmin() {
  return apiFetch('/admin/projects');
}

export function getProjectAnalysis(projectId) {
  return apiFetch(`/admin/projects/${projectId}/analysis`);
}

export function submitAdminDecision(projectId, decision, notes) {
  return apiFetch(`/admin/projects/${projectId}/decision`, {
    method: 'POST',
    body: { decision, notes: notes || undefined },
  });
}
