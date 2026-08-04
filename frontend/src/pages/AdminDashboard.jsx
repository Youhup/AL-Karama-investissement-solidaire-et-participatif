import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import StatusBadge from '../components/StatusBadge';
import { listAllProjectsAdmin } from '../api/projects';

export default function AdminDashboard() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    listAllProjectsAdmin()
      .then(setProjects)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
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
