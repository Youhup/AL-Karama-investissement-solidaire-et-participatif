import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import StatusBadge from '../components/StatusBadge';
import { listMyProjects } from '../api/projects';

export default function MyProjects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    listMyProjects()
      .then(setProjects)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <Navbar />
      <div className="wrap form-page">
        <div className="dashboard-header">
          <div>
            <h1 className="page-title">Mes projets</h1>
            <p>Tous vos dossiers, du brouillon au remboursement.</p>
          </div>
          <Link className="btn-primary" to="/deposer">Déposer un nouveau projet</Link>
        </div>

        {loading && <p>Chargement...</p>}
        {error && <div className="form-error">{error}</div>}

        {!loading && !error && projects.length === 0 && (
          <div className="empty-state">
            Vous n'avez pas encore de dossier. <Link to="/deposer">Déposez votre premier projet</Link>.
          </div>
        )}

        {projects.length > 0 && (
          <div className="list-rows">
            {projects.map((p) => (
              <Link key={p.id} to={`/mes-projets/${p.id}`} className="list-row">
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
        )}
      </div>
      <Footer />
    </>
  );
}
