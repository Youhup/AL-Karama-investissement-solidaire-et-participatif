// Jours restants avant l'échéance de collecte (funding_deadline, calculé
// côté API comme validated_at + funding_duration_days). null tant que le
// projet n'a pas encore été validé (pas de compte à rebours à afficher).
export function daysRemaining(fundingDeadline) {
  if (!fundingDeadline) return null;
  const diffMs = new Date(fundingDeadline).getTime() - Date.now();
  return Math.max(0, Math.ceil(diffMs / (24 * 60 * 60 * 1000)));
}

// Contenu + code couleur de l'étiquette d'échéance (cf. ProjectCard,
// ProjectDetail) : vert tant qu'il reste large, jaune sous 30 jours, rouge
// sous 10 jours. `finance` et échéance dépassée ont leur propre état, pas de
// compte à rebours à afficher dans ces cas.
export function deadlineBadge(status, fundingDeadline) {
  if (status === 'finance') {
    return { state: 'funded', num: 'Financé', unit: 'objectif atteint' };
  }
  const remaining = daysRemaining(fundingDeadline);
  if (remaining == null) return null;
  if (remaining <= 0) {
    return { state: 'closed', num: 'Terminé', unit: 'objectif non atteint' };
  }
  const state = remaining < 10 ? 'urgent' : remaining < 30 ? 'warn' : 'safe';
  return { state, num: remaining, unit: `jour${remaining > 1 ? 's' : ''} restant${remaining > 1 ? 's' : ''}` };
}
