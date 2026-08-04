import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { createProject, listSectors } from '../api/projects';

export default function DeposerProjet() {
  const navigate = useNavigate();

  const [sectors, setSectors] = useState([]);
  const [sectorsError, setSectorsError] = useState('');
  const [form, setForm] = useState({
    title: '', description: '', sector_id: '', amount_requested: '',
    funding_duration_days: 60, city: '', region: '', project_stage: 'idee',
  });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    listSectors()
      .then((data) => {
        setSectors(data);
        if (data.length > 0) setForm((f) => ({ ...f, sector_id: String(data[0].id) }));
      })
      .catch(() => setSectorsError("Impossible de charger la liste des secteurs. Vérifiez que le serveur est démarré."));
  }, []);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');

    if (!form.sector_id) {
      setError('Merci de choisir un secteur.');
      return;
    }

    setSubmitting(true);
    try {
      const project = await createProject({
        title: form.title,
        description: form.description,
        sector_id: Number(form.sector_id),
        amount_requested: Number(form.amount_requested),
        funding_duration_days: Number(form.funding_duration_days),
        city: form.city || undefined,
        region: form.region || undefined,
        project_stage: form.project_stage,
      });
      navigate(`/mes-projets/${project.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Navbar />
      <div className="wrap form-page">
        <h1 className="page-title">Déposer un projet</h1>
        <p className="page-subtitle">
          Décrivez votre activité et le montant dont vous avez besoin. Vous pourrez ajouter vos
          documents justificatifs et définir votre plan de remboursement en nature à l'étape
          suivante, avant de soumettre le dossier pour analyse.
        </p>

        <div className="form-panel">
          {error && <div className="form-error">{error}</div>}
          {sectorsError && <div className="form-error">{sectorsError}</div>}

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="title">Titre du projet</label>
              <input
                id="title" required value={form.title}
                placeholder="Ex. Coopérative Argane Ait Souala"
                onChange={(e) => update('title', e.target.value)}
              />
            </div>

            <div className="field">
              <label htmlFor="project_stage">Étape actuelle du projet</label>
              <select
                id="project_stage" required value={form.project_stage}
                onChange={(e) => update('project_stage', e.target.value)}
              >
                <option value="idee">Idée</option>
                <option value="demarrage">Démarrage</option>
                <option value="croissance">En croissance</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="description">Description</label>
              <textarea
                id="description" required value={form.description}
                placeholder="Présentez votre activité, votre expérience, et ce que le financement permettra de faire."
                onChange={(e) => update('description', e.target.value)}
              />
            </div>

            <div className="field">
              <label htmlFor="sector_id">Secteur</label>
              <select
                id="sector_id" required value={form.sector_id}
                onChange={(e) => update('sector_id', e.target.value)}
              >
                {sectors.length === 0 && <option value="">Chargement...</option>}
                {sectors.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>

            <div className="field-row">
              <div className="field">
                <label htmlFor="amount_requested">Montant demandé (MAD)</label>
                <input
                  id="amount_requested" type="number" min="100" step="100" required
                  value={form.amount_requested}
                  onChange={(e) => update('amount_requested', e.target.value)}
                />
                <p className="field-hint">Doit être un multiple de 100 MAD.</p>
              </div>
              <div className="field">
                <label htmlFor="funding_duration_days">Durée de collecte (jours)</label>
                <input
                  id="funding_duration_days" type="number" min="7" step="1" required
                  value={form.funding_duration_days}
                  onChange={(e) => update('funding_duration_days', e.target.value)}
                />
              </div>
            </div>

            <div className="field-row">
              <div className="field">
                <label htmlFor="city">Ville</label>
                <input id="city" value={form.city} onChange={(e) => update('city', e.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="region">Région</label>
                <input id="region" value={form.region} onChange={(e) => update('region', e.target.value)} />
              </div>
            </div>

            <p className="field-hint">
              Ce dossier restera en brouillon tant que vous ne l'aurez pas soumis explicitement —
              vous pourrez le modifier et ajouter des documents avant de le finaliser.
            </p>

            <button className="btn-primary btn-block" type="submit" disabled={submitting}>
              {submitting ? 'Création...' : 'Créer le brouillon'}
            </button>
          </form>
        </div>
      </div>
      <Footer />
    </>
  );
}
