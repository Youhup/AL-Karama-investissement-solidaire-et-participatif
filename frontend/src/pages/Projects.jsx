import { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import ProjectCard from '../components/ProjectCard';
import { listProjects, listSectors } from '../api/projects';
import { API_URL } from '../api/client';

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [sectorsById, setSectorsById] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([listProjects(), listSectors()])
      .then(([projectsData, sectorsData]) => {
        setProjects(projectsData);
        setSectorsById(Object.fromEntries(sectorsData.map((s) => [s.id, s.name])));
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <Navbar />
      <div className="wrap section">
        <div className="section-head">
          <div>
            <h2>Explorer les projets</h2>
            <p>Tous les dossiers validés, actuellement ouverts au financement.</p>
          </div>
        </div>

        {loading && <p>Chargement des projets...</p>}
        {error && <div className="form-error">{error}</div>}

        {!loading && !error && projects.length === 0 && (
          <p className="field-hint">Aucun projet disponible pour le moment.</p>
        )}

        <div className="cards">
          {projects.map((p) => (
            <ProjectCard
              key={p.id}
              id={p.id}
              tag={`${sectorsById[p.sector_id] || 'Projet'}${p.city ? ` · ${p.city}` : ''}`}
              title={p.title}
              location={p.description.length > 90 ? `${p.description.slice(0, 90)}…` : p.description}
              percent={p.amount_requested > 0 ? (p.amount_raised / p.amount_requested) * 100 : 0}
              amount={p.amount_raised}
              repayment="voir le détail du projet"
              photoUrl={p.photo_url ? `${API_URL}${p.photo_url}` : null}
              status={p.status}
              fundingDeadline={p.funding_deadline}
            />
          ))}
        </div>
      </div>
      <Footer />
    </>
  );
}
