import { API_URL, apiFetch, extractDetail, getToken } from './client';

export function startConversation(contextRole, projectId) {
  const params = new URLSearchParams({ context_role: contextRole });
  if (projectId) params.set('project_id', projectId);
  return apiFetch(`/chat/conversations?${params.toString()}`, { method: 'POST' });
}

/**
 * Envoie un message et stream la réponse : `onChunk(fullTextSoFar)` est
 * appelé à chaque fragment reçu, pour un affichage progressif côté UI
 * plutôt que d'attendre la réponse complète du LLM.
 */
export async function sendChatMessage(conversationId, content, onChunk) {
  const token = getToken();
  const response = await fetch(`${API_URL}/chat/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ content }),
  });

  if (!response.ok) {
    let detail = `Erreur ${response.status}`;
    try {
      detail = extractDetail(await response.json(), detail);
    } catch {
      // pas de corps JSON
    }
    throw new Error(detail);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let full = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    full += decoder.decode(value, { stream: true });
    onChunk(full);
  }
  return full;
}
