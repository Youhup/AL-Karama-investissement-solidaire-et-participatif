import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import StatusBadge from '../components/StatusBadge';
import { getAnalysisQuality, listAllProjectsAdmin } from '../api/projects';

export default function AdminDashboard() {
  const [projects, setProjects] = useState([]);
  const [quality, setQuality] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    listAllProjectsAdmin()
      .then(setProjects)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
    // Statistiques de concordance IA <-> décisions admin : non bloquant
    // pour la file de validation si l'endpoint échoue.
    getAnalysisQuality().then(setQuality).catch(() => {});
  }, []);

  const pendingCount = projects.filter((p) => p.status === 'a_valider').length;

  return (
    <>
      <Navbar />
      <div className="wrap form-page">
        <div className="dashboard-header">
          <div>
            <h1 className="page-title">Espace admin</h1>
            <p>{pendingCount} dossier{pendingCount > 1 ? 's' : ''} en attente de validation.</p>
          </div>
        </div>

        {quality && quality.decided_reports > 0 && (
          <div className="card" style={{ marginBottom: '1.5rem', padding: '1rem 1.25rem' }}>
            <strong>Qualité de l'analyse IA</strong>
            <p style={{ margin: '0.35rem 0 0' }}>
              {quality.agreement_rate_percent != null
                ? `Concordance IA ↔ décisions : ${quality.agreement_rate_percent}% `
                  + `(${quality.agreements} accord${quality.agreements > 1 ? 's' : ''}, `
                  + `${quality.disagreements} désaccord${quality.disagreements > 1 ? 's' : ''}`
                  + `${quality.neutral_a_examiner ? `, ${quality.neutral_a_examiner} neutre${quality.neutral_a_examiner > 1 ? 's' : ''} « à examiner »` : ''})`
                : `${quality.decided_reports} dossier${quality.decided_reports > 1 ? 's' : ''} tranché${quality.decided_reports > 1 ? 's' : ''}, `
                  + 'tous avec verdict neutre « à examiner » — pas encore de taux de concordance.'}
            </p>
            {quality.recent_disagreements.length > 0 && (
              <p className="list-row-sub" style={{ margin: '0.35rem 0 0' }}>
                Derniers désaccords :{' '}
                {quality.recent_disagreements.slice(0, 3).map((d, i) => (
                  <span key={d.project_id}>
                    {i > 0 && ' · '}
                    <Link to={`/admin/projects/${d.project_id}`}>{d.project_title}</Link>
                    {` (IA : ${d.ai_verdict} / admin : ${d.admin_decision})`}
                  </span>
                ))}
              </p>
            )}
          </div>
        )}

        {loading && <p>Chargement...</p>}
        {error && <div className="form-error">{error}</div>}

        {!loading && !error && projects.length === 0 && (
          <div className="empty-state">Aucun dossier pour le moment.</div>
        )}

        <div className="list-rows">
          {projects.map((p) => (
            <Link key={p.id} to={`/admin/projects/${p.id}`} className="list-row">
              <div className="list-row-main">
                <h3>{p.title}</h3>
                <span className="list-row-sub">
                  {Number(p.amount_requested).toLocaleString('fr-FR')} MAD demandés
                  {p.city ? ` · ${p.city}` : ''}
                </span>
              </div>
              <div className="list-row-figures">
                <StatusBadge status={p.status} />
                <div className="list-row-date">
                  {new Date(p.created_at).toLocaleDateString('fr-FR')}
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
      <Footer />
    </>
  );
}
