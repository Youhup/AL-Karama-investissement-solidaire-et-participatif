import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { createProject, listSectors } from '../api/projects';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { useToast } from '../components/ui/ToastProvider';
import Alert from '../components/ui/Alert';
import Field from '../components/ui/Field';
import SubmitButton from '../components/ui/SubmitButton';

export default function DeposerProjet() {
  const navigate = useNavigate();
  const toast = useToast();

  const [sectors, setSectors] = useState([]);
  const [sectorsError, setSectorsError] = useState('');
  const [form, setForm] = useState({
    title: '', description: '', sector_id: '', amount_requested: '',
    funding_duration_days: 60, city: '', region: '', project_stage: 'idee',
  });
  const create = useAsyncAction(() => createProject({
    title: form.title,
    description: form.description,
    sector_id: Number(form.sector_id),
    amount_requested: Number(form.amount_requested),
    funding_duration_days: Number(form.funding_duration_days),
    city: form.city || undefined,
    region: form.region || undefined,
    project_stage: form.project_stage,
  }));

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

    if (!form.sector_id) {
      create.setError('Merci de choisir un secteur.');
      return;
    }

    const res = await create.run();
    if (res.ok) {
      toast.success('Brouillon créé. Ajoutez maintenant vos documents.');
      navigate(`/mes-projets/${res.data.id}`);
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
          <Alert variant="error">{create.error}</Alert>
          <Alert variant="error">{sectorsError}</Alert>

          <form onSubmit={handleSubmit}>
            <Field
              id="title" label="Titre du projet" required value={form.title}
              placeholder="Ex. Coopérative Argane Ait Souala"
              onChange={(e) => update('title', e.target.value)}
            />

            <Field
              as="select" id="project_stage" label="Étape actuelle du projet" required
              value={form.project_stage}
              onChange={(e) => update('project_stage', e.target.value)}
            >
              <option value="idee">Idée</option>
              <option value="demarrage">Démarrage</option>
              <option value="croissance">En croissance</option>
            </Field>

            <Field
              as="textarea" id="description" label="Description" required value={form.description}
              placeholder="Présentez votre activité, votre expérience, et ce que le financement permettra de faire."
              onChange={(e) => update('description', e.target.value)}
            />

            <Field
              as="select" id="sector_id" label="Secteur" required value={form.sector_id}
              onChange={(e) => update('sector_id', e.target.value)}
            >
              {sectors.length === 0 && <option value="">Chargement...</option>}
              {sectors.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </Field>

            <div className="field-row">
              <Field
                id="amount_requested" label="Montant demandé (MAD)" type="number" min="100" step="100"
                required hint="Doit être un multiple de 100 MAD."
                value={form.amount_requested}
                onChange={(e) => update('amount_requested', e.target.value)}
              />
              <Field
                id="funding_duration_days" label="Durée de collecte (jours)" type="number" min="7" step="1"
                required value={form.funding_duration_days}
                onChange={(e) => update('funding_duration_days', e.target.value)}
              />
            </div>

            <div className="field-row">
              <Field id="city" label="Ville" value={form.city} onChange={(e) => update('city', e.target.value)} />
              <Field id="region" label="Région" value={form.region} onChange={(e) => update('region', e.target.value)} />
            </div>

            <p className="field-hint">
              Ce dossier restera en brouillon tant que vous ne l'aurez pas soumis explicitement —
              vous pourrez le modifier et ajouter des documents avant de le finaliser.
            </p>

            <SubmitButton className="btn-primary btn-block" pending={create.pending} pendingLabel="Création...">
              Créer le brouillon
            </SubmitButton>
          </form>
        </div>
      </div>
      <Footer />
    </>
  );
}
