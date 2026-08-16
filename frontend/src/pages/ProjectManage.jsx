import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import StatusBadge from '../components/StatusBadge';
import {
  createFundUsageItem, deleteDocument, deleteFundUsageItem, getProject, listDocuments,
  listFundUsageItems, listProjectInvestments, submitProject, updateProject, uploadDocument,
} from '../api/projects';
import { daysRemaining } from '../utils/funding';
import { createRefundPlan, deliverInstallment, getRefundPlan } from '../api/refunds';
import {
  BENEFICIARY_LABELS, DOCUMENT_TYPE_LABELS, INSTALLMENT_STATUS_LABELS, INVESTMENT_STATUS_LABELS,
  LEGAL_STATUS_LABELS, REPAYMENT_FREQUENCY_LABELS,
} from '../utils/labels';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { useToast } from '../components/ui/ToastProvider';
import Alert from '../components/ui/Alert';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import Field from '../components/ui/Field';
import SubmitButton from '../components/ui/SubmitButton';

const DOC_TYPES = Object.keys(DOCUMENT_TYPE_LABELS);
const LEGAL_STATUSES = Object.keys(LEGAL_STATUS_LABELS);
const BENEFICIARIES = Object.keys(BENEFICIARY_LABELS);
const FREQUENCIES = Object.keys(REPAYMENT_FREQUENCY_LABELS);
const PLATFORM_MIN_INVESTMENT = 100;
// Le plan se saisit dès la création du dossier (brouillon) : l'admin doit
// pouvoir l'évaluer pendant l'instruction, et un investisseur potentiel doit
// pouvoir le consulter avant même que le projet soit validé. Reste
// consultable jusqu'à la clôture ; seul un dossier rejeté n'a plus d'intérêt.
const REFUND_STATUSES = [
  'brouillon', 'soumis', 'en_analyse', 'a_valider',
  'valide', 'en_financement', 'finance', 'en_remboursement', 'clos',
];

const emptyProfile = {
  legal_status: '', legal_id_number: '', activity_start_year: '',
  target_beneficiaries: [], jobs_created: 0, jobs_maintained: 0, social_impact_description: '',
  previous_funding: false, previous_funding_details: '', risk_factors: '',
  pitch_summary: '', references_text: '',
};

const emptyTier = {
  tier_max_amount: '', product_description: '', unit: '',
  quantity_per_occurrence: '1', frequency: 'mensuelle', installments_count: '', estimated_unit_value: '',
};

export default function ProjectManage() {
  const { id } = useParams();
  const toast = useToast();

  const [project, setProject] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [fundItems, setFundItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [activeTab, setActiveTab] = useState('documents');

  const [docType, setDocType] = useState(DOC_TYPES[0]);
  const [file, setFile] = useState(null);
  const [submitted, setSubmitted] = useState(false);

  // Dialogue de confirmation partagé par toutes les actions sensibles de la
  // page : { title, message, confirmLabel, danger, successMessage, action }.
  const [confirm, setConfirm] = useState(null);
  const [confirmPending, setConfirmPending] = useState(false);

  // --- Section A/D/E/F : profil du dossier (statut juridique, impact,
  // confiance, présentation) — un seul formulaire, un seul PATCH.
  const [profile, setProfile] = useState(emptyProfile);
  const [profileInitialized, setProfileInitialized] = useState(false);

  // --- Section B : utilisation des fonds ---
  const [newFundItem, setNewFundItem] = useState({ category: '', amount: '', description: '' });

  // --- Investisseurs (qui a financé, coordonnées si consenties) ---
  const [investments, setInvestments] = useState([]);
  const [investmentsError, setInvestmentsError] = useState('');

  // --- Section C : plan de remboursement en nature (paliers) ---
  const [refundPlan, setRefundPlan] = useState(null);
  const [refundPlanChecked, setRefundPlanChecked] = useState(false);
  const [tiers, setTiers] = useState([{ ...emptyTier, tier_max_amount: '' }]);
  const [startDate, setStartDate] = useState('');
  const [tierAddError, setTierAddError] = useState('');
  const [coverageWarnings, setCoverageWarnings] = useState([]);
  // Par palier, n'affiche par défaut que l'échéance courante (la prochaine
  // non livrée) plutôt que tout l'historique — trop volumineux dès que le
  // plan a beaucoup d'investisseurs et d'échéances.
  const [expandedTiers, setExpandedTiers] = useState({});

  async function refresh() {
    const [p, docs, items] = await Promise.all([
      getProject(id), listDocuments(id), listFundUsageItems(id),
    ]);
    setProject(p);
    setDocuments(docs);
    setFundItems(items);
  }

  useEffect(() => {
    refresh()
      .catch((err) => setLoadError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!project || profileInitialized) return;
    setProfile({
      legal_status: project.legal_status || '',
      legal_id_number: project.legal_id_number || '',
      activity_start_year: project.activity_start_year || '',
      target_beneficiaries: project.target_beneficiaries || [],
      jobs_created: project.jobs_created || 0,
      jobs_maintained: project.jobs_maintained || 0,
      social_impact_description: project.social_impact_description || '',
      previous_funding: project.previous_funding || false,
      previous_funding_details: project.previous_funding_details || '',
      risk_factors: project.risk_factors || '',
      pitch_summary: project.pitch_summary || '',
      references_text: project.references_text || '',
    });
    setProfileInitialized(true);
  }, [project, profileInitialized]);

  useEffect(() => {
    if (!project || !REFUND_STATUSES.includes(project.status)) return;
    getRefundPlan(id)
      .then(setRefundPlan)
      .catch(() => setRefundPlan(null))
      .finally(() => setRefundPlanChecked(true));
  }, [project?.status, id]);

  useEffect(() => {
    if (!project || project.status === 'brouillon') return;
    listProjectInvestments(id)
      .then(setInvestments)
      .catch((err) => setInvestmentsError(err.message));
  }, [project?.status, id]);

  const upload = useAsyncAction(async (formEl) => {
    await uploadDocument(id, file, docType);
    setFile(null);
    formEl.reset();
    await refresh();
  });

  const removeDoc = useAsyncAction(async (documentId) => {
    await deleteDocument(documentId);
    await refresh();
  });

  const submitDossier = useAsyncAction(async () => {
    const updated = await submitProject(id);
    setProject(updated);
    setSubmitted(true);
  });

  async function handleUpload(e) {
    e.preventDefault();
    if (!file) {
      upload.setError('Choisissez un fichier.');
      return;
    }
    const formEl = e.currentTarget;
    const res = await upload.run(formEl);
    if (res.ok) toast.success('Document ajouté.');
  }

  async function handleConfirm() {
    if (!confirm) return;
    setConfirmPending(true);
    const res = await confirm.action();
    setConfirmPending(false);
    setConfirm(null);
    if (res.ok) {
      if (confirm.successMessage) toast.success(confirm.successMessage);
    } else {
      toast.error(res.message);
    }
  }

  function updateProfile(field, value) {
    setProfile((p) => ({ ...p, [field]: value }));
  }

  function toggleBeneficiary(key) {
    setProfile((p) => ({
      ...p,
      target_beneficiaries: p.target_beneficiaries.includes(key)
        ? p.target_beneficiaries.filter((b) => b !== key)
        : [...p.target_beneficiaries, key],
    }));
  }

  const saveProfile = useAsyncAction(async () => {
    const updated = await updateProject(id, {
      legal_status: profile.legal_status || undefined,
      legal_id_number: profile.legal_id_number || undefined,
      activity_start_year: profile.activity_start_year ? Number(profile.activity_start_year) : undefined,
      target_beneficiaries: profile.target_beneficiaries,
      jobs_created: Number(profile.jobs_created) || 0,
      jobs_maintained: Number(profile.jobs_maintained) || 0,
      social_impact_description: profile.social_impact_description || undefined,
      previous_funding: profile.previous_funding,
      previous_funding_details: profile.previous_funding_details || undefined,
      risk_factors: profile.risk_factors || undefined,
      pitch_summary: profile.pitch_summary || undefined,
      references_text: profile.references_text || undefined,
    });
    setProject(updated);
  });

  async function handleSaveProfile() {
    const res = await saveProfile.run();
    if (res.ok) toast.success('Informations enregistrées.');
  }

  const addFundItem = useAsyncAction(async () => {
    await createFundUsageItem(id, {
      category: newFundItem.category,
      amount: Number(newFundItem.amount),
      description: newFundItem.description || undefined,
    });
    setNewFundItem({ category: '', amount: '', description: '' });
    await refresh();
  });

  const removeFundItem = useAsyncAction(async (itemId) => {
    await deleteFundUsageItem(itemId);
    await refresh();
  });

  async function handleAddFundItem(e) {
    e.preventDefault();
    if (!newFundItem.category || !newFundItem.amount) {
      addFundItem.setError('Le poste et le montant sont requis.');
      return;
    }
    const res = await addFundItem.run();
    if (res.ok) toast.success('Poste ajouté.');
  }

  function updateTier(index, field, value) {
    setTiers((rows) => rows.map((row, i) => (i === index ? { ...row, [field]: value } : row)));
  }

  function tierMinFor(index, rows) {
    if (index === 0) return PLATFORM_MIN_INVESTMENT;
    const prevMax = rows[index - 1].tier_max_amount;
    return prevMax === '' ? null : Number(prevMax) + 1;
  }

  function addTierRow() {
    const lastMax = tiers[tiers.length - 1].tier_max_amount;
    if (lastMax === '') {
      setTierAddError(
        "Renseignez le montant maximum du dernier palier avant d'en ajouter un nouveau."
      );
      return;
    }
    setTierAddError('');
    setTiers((rows) => [...rows, { ...emptyTier }]);
  }

  function removeTierRow(index) {
    setTiers((rows) => rows.filter((_, i) => i !== index));
  }

  function toggleTierHistory(tierId) {
    setExpandedTiers((prev) => ({ ...prev, [tierId]: !prev[tierId] }));
  }

  // Tant que le projet n'est pas financé, l'identité des investisseurs n'est
  // jamais révélée (cf. backend) : on affiche juste un décompte plutôt que
  // de répéter "coordonnées non partagées" sur chaque échéance. Une fois
  // financé, les investisseurs n'ayant pas consenti restent groupés en un
  // seul décompte plutôt que listés un par un.
  function renderBeneficiaries(installment, unit, financed) {
    if (installment.allocations.length === 0) {
      return <span className="field-hint">Aucun investisseur alloué pour l'instant.</span>;
    }
    if (!financed) {
      const count = installment.allocations.length;
      return (
        <span className="field-hint">
          {count} investisseur{count > 1 ? 's' : ''} alloué{count > 1 ? 's' : ''}
        </span>
      );
    }
    const named = installment.allocations.filter((a) => a.investor_name);
    const unnamedCount = installment.allocations.length - named.length;
    return (
      <ul style={{ margin: 0, paddingLeft: 16 }}>
        {named.map((a) => (
          <li key={a.id}>{a.investor_name} — {a.quantity_allocated} {unit}</li>
        ))}
        {unnamedCount > 0 && (
          <li className="field-hint">
            {unnamedCount} investisseur{unnamedCount > 1 ? 's' : ''} n'{unnamedCount > 1 ? 'ont' : 'a'} pas
            consenti au partage
          </li>
        )}
      </ul>
    );
  }

  const createPlan = useAsyncAction(async () => {
    const payload = {
      start_date: startDate,
      tiers: tiers.map((t, i) => ({
        tier_min_amount: tierMinFor(i, tiers),
        tier_max_amount: t.tier_max_amount === '' ? null : Number(t.tier_max_amount),
        product_description: t.product_description,
        unit: t.unit,
        quantity_per_occurrence: Number(t.quantity_per_occurrence),
        frequency: t.frequency,
        installments_count: Number(t.installments_count),
        estimated_unit_value: t.estimated_unit_value === '' ? null : Number(t.estimated_unit_value),
      })),
    };
    const created = await createRefundPlan(id, payload);
    setRefundPlan(created);
    setCoverageWarnings(created.coverage_warnings || []);
  });

  const deliver = useAsyncAction(async (installmentId) => {
    await deliverInstallment(installmentId);
    const [updatedPlan, updatedProject] = await Promise.all([getRefundPlan(id), getProject(id)]);
    setRefundPlan(updatedPlan);
    setProject(updatedProject);
  });

  async function handleCreateRefundPlan(e) {
    e.preventDefault();
    const res = await createPlan.run();
    if (res.ok) toast.success('Plan de remboursement créé.');
  }

  async function handleDeliver(installmentId) {
    const res = await deliver.run(installmentId);
    if (res.ok) toast.success('Échéance marquée livrée.');
    else toast.error(res.message);
  }

  if (loading) {
    return (
      <>
        <Navbar />
        <div className="wrap form-page"><p>Chargement du dossier...</p></div>
        <Footer />
      </>
    );
  }

  if (loadError || !project) {
    return (
      <>
        <Navbar />
        <div className="wrap form-page">
          <div className="form-error">{loadError || 'Dossier introuvable.'}</div>
        </div>
        <Footer />
      </>
    );
  }

  const isDraft = project.status === 'brouillon';
  const fundTotal = fundItems.reduce((sum, item) => sum + Number(item.amount), 0);
  const amountRequested = Number(project.amount_requested);
  const showRefundSection = REFUND_STATUSES.includes(project.status);
  // Le plan de remboursement ne se définit que pendant que le dossier est
  // en brouillon : il fait partie du dépôt du projet et n'est plus
  // modifiable une fois soumis (cf. PLAN_CREATABLE_STATUSES côté backend,
  // refunds.py, qui doit rester synchronisé avec cette liste).
  const PLAN_CREATABLE_STATUSES = ['brouillon'];
  const canBuildRefundPlan =
    PLAN_CREATABLE_STATUSES.includes(project.status) && refundPlanChecked && !refundPlan;

  const TABS = [
    { key: 'documents', label: 'Documents' },
    { key: 'fonds', label: 'Utilisation des fonds' },
    { key: 'infos', label: 'Informations complémentaires' },
    ...(project.status !== 'brouillon' ? [{ key: 'investisseurs', label: 'Investisseurs' }] : []),
    { key: 'remboursement', label: 'Plan de remboursement' },
  ];

  return (
    <>
      <Navbar />
      <div className="wrap form-page">
        <div className="dossier-header">
          <div>
            <h1 className="page-title">{project.title}</h1>
            <p className="page-subtitle" style={{ marginBottom: 0 }}>
              {amountRequested.toLocaleString('fr-FR')} MAD demandés
              {(() => {
                const remaining = daysRemaining(project.funding_deadline);
                if (project.status === 'finance') return ' · objectif atteint';
                if (remaining == null) return '';
                return remaining > 0
                  ? ` · ${remaining} j restants pour la collecte`
                  : ' · collecte terminée';
              })()}
            </p>
          </div>
          <StatusBadge status={project.status} />
        </div>

        <div className="dossier-tabs">
          {TABS.map((tab) => (
            <button
              key={tab.key} type="button"
              className={`dossier-tab${activeTab === tab.key ? ' active' : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'documents' && (
        <div className="dossier-tab-panel">
        <div className="dossier-grid">
          <div>
            <div className="upload-box">
              <h3 style={{ marginBottom: 14 }}>Documents du dossier</h3>

              {documents.length > 0 ? (
                <ul className="doc-list">
                  {documents.map((doc) => (
                    <li key={doc.id}>
                      <div className="doc-meta">
                        <span>{doc.original_name}</span>
                        <span className="doc-type">{DOCUMENT_TYPE_LABELS[doc.doc_type]}</span>
                      </div>
                      {isDraft && (
                        <button
                          className="doc-remove"
                          onClick={() => setConfirm({
                            title: 'Retirer ce document ?',
                            message: doc.original_name,
                            confirmLabel: 'Retirer',
                            danger: true,
                            successMessage: 'Document retiré.',
                            action: () => removeDoc.run(doc.id),
                          })}
                        >
                          Retirer
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="field-hint" style={{ marginTop: 0 }}>Aucun document ajouté pour l'instant.</p>
              )}

              {isDraft && (
                <form onSubmit={handleUpload} style={{ marginTop: 18 }}>
                  <Alert variant="error">{upload.error}</Alert>
                  <div className="upload-row">
                    <Field
                      as="select" id="doc_type" label="Type de document"
                      value={docType} onChange={(e) => setDocType(e.target.value)}
                    >
                      {DOC_TYPES.map((t) => (
                        <option key={t} value={t}>{DOCUMENT_TYPE_LABELS[t]}</option>
                      ))}
                    </Field>
                    <Field
                      id="file" label="Fichier" type="file" accept=".jpg,.jpeg,.png,.webp,.pdf"
                      onChange={(e) => setFile(e.target.files[0])}
                    />
                    <SubmitButton className="btn-secondary" pending={upload.pending} pendingLabel="Envoi...">
                      Ajouter
                    </SubmitButton>
                  </div>
                  <p className="field-hint">Formats acceptés : JPG, PNG, WEBP, PDF — 10 Mo maximum.</p>
                </form>
              )}
            </div>
          </div>

          <div className="submit-panel">
            {submitted ? (
              <>
                <h3>Dossier soumis</h3>
                <Alert variant="success">Dossier soumis avec succès, en cours d'analyse.</Alert>
              </>
            ) : isDraft ? (
              <>
                <h3>Soumettre le dossier</h3>
                <p>
                  Une fois soumis, le dossier est verrouillé et analysé automatiquement avant
                  validation par notre équipe. Vous ne pourrez plus modifier les documents.
                </p>
                {documents.length === 0 && (
                  <Alert variant="info">
                    Aucun document ajouté. Un dossier plus complet est analysé plus favorablement.
                  </Alert>
                )}
                {refundPlanChecked && !refundPlan && (
                  <Alert variant="info">
                    Définissez votre plan de remboursement en nature (onglet "Plan de remboursement")
                    avant de soumettre — il ne sera plus possible d'en ajouter un après la soumission.
                  </Alert>
                )}
                <SubmitButton
                  type="button" className="btn-primary btn-block"
                  pending={submitDossier.pending} pendingLabel="Envoi..."
                  disabled={!refundPlanChecked || !refundPlan}
                  onClick={() => setConfirm({
                    title: 'Soumettre le dossier pour analyse ?',
                    message: 'Une fois soumis, le dossier est verrouillé : vous ne pourrez plus modifier '
                      + 'les documents, la répartition des fonds ni le plan de remboursement.',
                    confirmLabel: 'Soumettre',
                    successMessage: 'Dossier soumis pour analyse.',
                    action: () => submitDossier.run(),
                  })}
                >
                  Soumettre pour analyse
                </SubmitButton>
              </>
            ) : (
              <>
                <h3>Statut du dossier</h3>
                <p>Ce dossier a déjà été soumis et ne peut plus être modifié depuis cette page.</p>
              </>
            )}
          </div>
        </div>
        </div>
        )}

        {activeTab === 'fonds' && (
        <div className="dossier-tab-panel">
        {/* --- Section B : utilisation des fonds --- */}
        <div className="form-panel form-panel-wide">
          <h3 style={{ marginBottom: 6 }}>Utilisation des fonds</h3>
          <p className="field-hint" style={{ marginTop: 0, marginBottom: 18 }}>
            Répartition du montant demandé ({amountRequested.toLocaleString('fr-FR')} MAD).
          </p>

          {fundItems.length > 0 ? (
            <table className="allocation-table">
              <thead>
                <tr><th>Poste</th><th>Montant (MAD)</th><th>Détail</th>{isDraft && <th></th>}</tr>
              </thead>
              <tbody>
                {fundItems.map((item) => (
                  <tr key={item.id}>
                    <td>{item.category}</td>
                    <td className="mono">{Number(item.amount).toLocaleString('fr-FR')}</td>
                    <td>{item.description || '—'}</td>
                    {isDraft && (
                      <td>
                        <button
                          className="doc-remove"
                          onClick={() => setConfirm({
                            title: 'Retirer ce poste de dépense ?',
                            message: `${item.category} — ${Number(item.amount).toLocaleString('fr-FR')} MAD`,
                            confirmLabel: 'Retirer',
                            danger: true,
                            successMessage: 'Poste retiré.',
                            action: () => removeFundItem.run(item.id),
                          })}
                        >
                          Retirer
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="field-hint" style={{ marginTop: 0 }}>Aucun poste renseigné pour l'instant.</p>
          )}

          <p className="field-hint" style={{ marginTop: 14 }}>
            Réparti : <span className="mono">{fundTotal.toLocaleString('fr-FR')}</span> /{' '}
            <span className="mono">{amountRequested.toLocaleString('fr-FR')}</span> MAD
            {fundTotal !== amountRequested && (
              <> — écart de <span className="mono">{Math.abs(amountRequested - fundTotal).toLocaleString('fr-FR')}</span> MAD</>
            )}
          </p>

          {isDraft && (
            <form onSubmit={handleAddFundItem} style={{ marginTop: 18 }}>
              <Alert variant="error">{addFundItem.error}</Alert>
              <div className="field-row">
                <Field
                  id="fund_category" label="Poste de dépense" value={newFundItem.category}
                  onChange={(e) => setNewFundItem((f) => ({ ...f, category: e.target.value }))}
                />
                <Field
                  id="fund_amount" label="Montant (MAD)" type="number" min="0" step="1"
                  value={newFundItem.amount}
                  onChange={(e) => setNewFundItem((f) => ({ ...f, amount: e.target.value }))}
                />
              </div>
              <Field
                id="fund_description" label="Détail / justificatif (optionnel)"
                value={newFundItem.description}
                onChange={(e) => setNewFundItem((f) => ({ ...f, description: e.target.value }))}
              />
              <SubmitButton className="btn-secondary" pending={addFundItem.pending} pendingLabel="Ajout...">
                + Ajouter un poste
              </SubmitButton>
            </form>
          )}
        </div>
        </div>
        )}

        {activeTab === 'infos' && (
        <div className="dossier-tab-panel">
        {/* --- Sections A/D/E/F : statut juridique, impact, confiance, présentation --- */}
        <div className="form-panel form-panel-wide">
          <h3 style={{ marginBottom: 18 }}>Informations complémentaires</h3>

          <div className="field-row">
            <Field
              as="select" id="legal_status" label="Statut juridique"
              value={profile.legal_status} disabled={!isDraft}
              onChange={(e) => updateProfile('legal_status', e.target.value)}
            >
              <option value="">—</option>
              {LEGAL_STATUSES.map((s) => (
                <option key={s} value={s}>{LEGAL_STATUS_LABELS[s]}</option>
              ))}
            </Field>
            <Field
              id="legal_id_number" label="Numéro ICE / RC"
              value={profile.legal_id_number} disabled={!isDraft}
              onChange={(e) => updateProfile('legal_id_number', e.target.value)}
            />
            <Field
              id="activity_start_year" label="Année de début d'activité" type="number" min="1900"
              value={profile.activity_start_year} disabled={!isDraft}
              onChange={(e) => updateProfile('activity_start_year', e.target.value)}
            />
          </div>

          <div className="field">
            <label>Public bénéficiaire</label>
            <div className="chip-row">
              {BENEFICIARIES.map((key) => (
                <span
                  key={key}
                  className={`chip-toggle${profile.target_beneficiaries.includes(key) ? ' active' : ''}`}
                  onClick={() => isDraft && toggleBeneficiary(key)}
                >
                  {BENEFICIARY_LABELS[key]}
                </span>
              ))}
            </div>
          </div>

          <div className="field-row">
            <Field
              id="jobs_created" label="Emplois créés" type="number" min="0"
              value={profile.jobs_created} disabled={!isDraft}
              onChange={(e) => updateProfile('jobs_created', e.target.value)}
            />
            <Field
              id="jobs_maintained" label="Emplois maintenus" type="number" min="0"
              value={profile.jobs_maintained} disabled={!isDraft}
              onChange={(e) => updateProfile('jobs_maintained', e.target.value)}
            />
          </div>

          <Field
            as="textarea" id="social_impact_description" label="Description de l'impact"
            value={profile.social_impact_description} disabled={!isDraft}
            onChange={(e) => updateProfile('social_impact_description', e.target.value)}
          />

          <div className="field">
            <label>Financement(s) antérieur(s) ?</label>
            <div className="chip-row">
              <span
                className={`chip-toggle${profile.previous_funding ? ' active' : ''}`}
                onClick={() => isDraft && updateProfile('previous_funding', true)}
              >
                Oui
              </span>
              <span
                className={`chip-toggle${!profile.previous_funding ? ' active' : ''}`}
                onClick={() => isDraft && updateProfile('previous_funding', false)}
              >
                Non
              </span>
            </div>
          </div>

          {profile.previous_funding && (
            <Field
              as="textarea" id="previous_funding_details" label="Détails (montant, source, remboursé ?)"
              value={profile.previous_funding_details} disabled={!isDraft}
              onChange={(e) => updateProfile('previous_funding_details', e.target.value)}
            />
          )}

          <Field
            as="textarea" id="risk_factors" label="Facteurs de risque identifiés"
            value={profile.risk_factors} disabled={!isDraft}
            onChange={(e) => updateProfile('risk_factors', e.target.value)}
          />

          <Field
            id="pitch_summary" label="Résumé en une phrase" maxLength={140}
            value={profile.pitch_summary} disabled={!isDraft}
            hint={`${profile.pitch_summary.length} / 140`}
            onChange={(e) => updateProfile('pitch_summary', e.target.value)}
          />

          <Field
            as="textarea" id="references_text" label="Références (clients, partenaires...)"
            value={profile.references_text} disabled={!isDraft}
            onChange={(e) => updateProfile('references_text', e.target.value)}
          />

          {isDraft && (
            <>
              <Alert variant="error">{saveProfile.error}</Alert>
              <SubmitButton
                type="button" className="btn-secondary"
                pending={saveProfile.pending} pendingLabel="Enregistrement..."
                onClick={handleSaveProfile}
              >
                Enregistrer les informations complémentaires
              </SubmitButton>
            </>
          )}
        </div>
        </div>
        )}

        {activeTab === 'investisseurs' && project.status !== 'brouillon' && (
        <div className="dossier-tab-panel">
        {/* --- Investisseurs --- */}
          <div className="form-panel form-panel-wide">
            <h3 style={{ marginBottom: 6 }}>Investisseurs</h3>
            <p className="field-hint" style={{ marginTop: 0, marginBottom: 18 }}>
              {project.status === 'en_remboursement'
                ? "Coordonnées visibles uniquement pour les investisseurs ayant accepté de les partager, afin d'organiser la livraison."
                : "Les coordonnées ne sont révélées qu'une fois le projet passé en remboursement."}
            </p>

            <Alert variant="error">{investmentsError}</Alert>

            {investments.length > 0 ? (
              <table className="allocation-table">
                <thead>
                  <tr><th>Montant (MAD)</th><th>Statut</th><th>Contact</th></tr>
                </thead>
                <tbody>
                  {investments.map((inv) => (
                    <tr key={inv.id}>
                      <td className="mono">{Number(inv.amount).toLocaleString('fr-FR')}</td>
                      <td>{INVESTMENT_STATUS_LABELS[inv.status] || inv.status}</td>
                      <td>
                        {inv.investor_name ? (
                          <>
                            {inv.investor_name}
                            {inv.investor_phone && <> — {inv.investor_phone}</>}
                            {inv.investor_city && <> ({inv.investor_city}{inv.investor_region ? `, ${inv.investor_region}` : ''})</>}
                          </>
                        ) : inv.share_contact_consent ? (
                          <span className="field-hint">Partagées dès le début du remboursement</span>
                        ) : (
                          <span className="field-hint">Non partagées</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="field-hint" style={{ marginTop: 0 }}>Aucun investissement pour l'instant.</p>
            )}
          </div>
        </div>
        )}

        {activeTab === 'remboursement' && (
        <div className="dossier-tab-panel">
        {/* --- Section C : plan de remboursement en nature --- */}
        <div className="form-panel form-panel-wide">
          <h3 style={{ marginBottom: 6 }}>Plan de remboursement en nature</h3>

          {!showRefundSection ? (
            <p className="field-hint" style={{ marginTop: 0 }}>
              Ce dossier a été rejeté, le plan de remboursement ne peut plus être défini.
            </p>
          ) : (
          <>
            {coverageWarnings.length > 0 && (
              <div className="info-banner">
                {coverageWarnings.map((w, i) => <p key={i} style={{ margin: i ? '6px 0 0' : 0 }}>{w}</p>)}
              </div>
            )}

            {refundPlan ? (
              <>
                <p className="field-hint" style={{ marginTop: 0 }}>
                  Démarré le {new Date(refundPlan.start_date).toLocaleDateString('fr-FR')}.
                </p>
                {project.status !== 'en_remboursement' && (
                  <div className="info-banner">
                    Les échéances ne pourront être marquées livrées, et les coordonnées des
                    investisseurs ayant consenti au partage ne seront affichées, qu'une fois le
                    projet entièrement financé et passé en remboursement.
                  </div>
                )}
                {refundPlan.tiers.map((tier) => {
                  const tierInstallments = refundPlan.installments
                    .filter((installment) => installment.refund_tier_id === tier.id)
                    .sort((a, b) => a.installment_number - b.installment_number);
                  const currentInstallment =
                    tierInstallments.find((installment) => installment.status !== 'livre')
                    || tierInstallments[tierInstallments.length - 1];
                  const expanded = !!expandedTiers[tier.id];
                  const visibleInstallments = expanded
                    ? tierInstallments
                    : [currentInstallment].filter(Boolean);
                  const financed = project.status === 'en_remboursement';

                  return (
                    <div key={tier.id} className="card" style={{ marginBottom: 16 }}>
                      <div>
                        <strong>{tier.product_description}</strong> — {tier.quantity_per_occurrence} {tier.unit}{' '}
                        / {REPAYMENT_FREQUENCY_LABELS[tier.frequency].toLowerCase()}, pour les investissements de{' '}
                        {Number(tier.tier_min_amount).toLocaleString('fr-FR')} MAD
                        {tier.tier_max_amount != null
                          ? ` à ${Number(tier.tier_max_amount).toLocaleString('fr-FR')} MAD`
                          : ' et plus'}
                        .
                      </div>
                      <table className="allocation-table">
                        <thead>
                          <tr><th>#</th><th>Échéance</th><th>Quantité due</th><th>Bénéficiaires</th><th>Statut</th><th></th></tr>
                        </thead>
                        <tbody>
                          {visibleInstallments.map((installment) => (
                            <tr key={installment.id}>
                              <td>{installment.installment_number}</td>
                              <td>{new Date(installment.due_date).toLocaleDateString('fr-FR')}</td>
                              <td className="mono">{installment.quantity_due}</td>
                              <td>{renderBeneficiaries(installment, tier.unit, financed)}</td>
                              <td>{INSTALLMENT_STATUS_LABELS[installment.status]}</td>
                              <td>
                                {installment.status !== 'livre' && financed && (
                                  <button
                                    className="doc-remove"
                                    disabled={deliver.pending}
                                    onClick={() => handleDeliver(installment.id)}
                                  >
                                    Marquer livré
                                  </button>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {tierInstallments.length > 1 && (
                        <button
                          type="button" className="btn-secondary" style={{ marginTop: 10 }}
                          onClick={() => toggleTierHistory(tier.id)}
                        >
                          {expanded ? 'Réduire' : `Voir l'historique complet (${tierInstallments.length} échéances)`}
                        </button>
                      )}
                    </div>
                  );
                })}
              </>
            ) : canBuildRefundPlan ? (
              <form onSubmit={handleCreateRefundPlan}>
                <p className="field-hint" style={{ marginTop: 0 }}>
                  Le remboursement se fait uniquement en nature. Le montant minimum d'investissement de la
                  plateforme ({PLATFORM_MIN_INVESTMENT} MAD) fixe le premier palier ; chaque palier suivant
                  démarre automatiquement au lendemain du plafond du précédent.
                </p>

                <Field
                  id="start_date" label="Date de départ" type="date" required value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />

                {tiers.map((tier, index) => {
                  const min = tierMinFor(index, tiers);
                  return (
                    <div key={index} className="card" style={{ marginBottom: 14 }}>
                      <div className="dossier-header" style={{ marginBottom: 0 }}>
                        <strong>Palier {index + 1}</strong>
                        {tiers.length > 1 && (
                          <button type="button" className="doc-remove" onClick={() => removeTierRow(index)}>
                            ✕ Retirer
                          </button>
                        )}
                      </div>
                      <div className="field-row">
                        <div className="field">
                          <label>Min investi (MAD)</label>
                          <input className="mono" value={min ?? ''} disabled readOnly />
                        </div>
                        <Field
                          id={`tier_max_${index}`} label="Max investi (MAD)" type="number" min={min || 0}
                          placeholder="∞ (dernier palier)" value={tier.tier_max_amount}
                          onChange={(e) => updateTier(index, 'tier_max_amount', e.target.value)}
                        />
                        <Field
                          as="select" id={`tier_freq_${index}`} label="Fréquence" value={tier.frequency}
                          onChange={(e) => updateTier(index, 'frequency', e.target.value)}
                        >
                          {FREQUENCIES.map((f) => (
                            <option key={f} value={f}>{REPAYMENT_FREQUENCY_LABELS[f]}</option>
                          ))}
                        </Field>
                      </div>
                      <div className="field-row">
                        <Field
                          id={`tier_product_${index}`} label="Nature du bien" required
                          value={tier.product_description}
                          onChange={(e) => updateTier(index, 'product_description', e.target.value)}
                        />
                        <Field
                          id={`tier_unit_${index}`} label="Unité" required value={tier.unit}
                          onChange={(e) => updateTier(index, 'unit', e.target.value)}
                        />
                        <Field
                          id={`tier_qty_${index}`} label="Quantité / échéance" type="number" min="0"
                          step="0.01" required value={tier.quantity_per_occurrence}
                          onChange={(e) => updateTier(index, 'quantity_per_occurrence', e.target.value)}
                        />
                      </div>
                      <div className="field-row">
                        <Field
                          id={`tier_count_${index}`} label="Nombre d'échéances" type="number" min="1"
                          max="60" required value={tier.installments_count}
                          onChange={(e) => updateTier(index, 'installments_count', e.target.value)}
                        />
                        <Field
                          id={`tier_value_${index}`} label="Valeur unitaire estimée (MAD)" type="number"
                          min="0" value={tier.estimated_unit_value}
                          hint="Facultatif — sert uniquement à un avertissement de couverture."
                          onChange={(e) => updateTier(index, 'estimated_unit_value', e.target.value)}
                        />
                      </div>
                    </div>
                  );
                })}

                <Alert variant="error">{tierAddError}</Alert>
                <button type="button" className="btn-secondary" onClick={addTierRow} style={{ marginBottom: 18 }}>
                  + Ajouter un palier
                </button>

                <Alert variant="error">{createPlan.error}</Alert>

                <SubmitButton className="btn-primary btn-block" pending={createPlan.pending} pendingLabel="Création...">
                  Créer le plan de remboursement
                </SubmitButton>
              </form>
            ) : (
              <p className="field-hint" style={{ marginTop: 0 }}>
                Le plan de remboursement ne peut être défini que pendant que le dossier est en
                brouillon, avant sa soumission pour analyse.
              </p>
            )}
          </>
          )}
        </div>
        </div>
        )}
      </div>

      <ConfirmDialog
        open={!!confirm}
        danger={!!confirm?.danger}
        title={confirm?.title}
        message={confirm?.message}
        confirmLabel={confirm?.confirmLabel}
        pending={confirmPending}
        onConfirm={handleConfirm}
        onCancel={() => setConfirm(null)}
      />

      <Footer />
    </>
  );
}
