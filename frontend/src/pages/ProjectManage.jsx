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

  const [project, setProject] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [fundItems, setFundItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [activeTab, setActiveTab] = useState('documents');

  const [docType, setDocType] = useState(DOC_TYPES[0]);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [submitted, setSubmitted] = useState(false);

  // --- Section A/D/E/F : profil du dossier (statut juridique, impact,
  // confiance, présentation) — un seul formulaire, un seul PATCH.
  const [profile, setProfile] = useState(emptyProfile);
  const [profileInitialized, setProfileInitialized] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileError, setProfileError] = useState('');
  const [profileSaved, setProfileSaved] = useState(false);

  // --- Section B : utilisation des fonds ---
  const [newFundItem, setNewFundItem] = useState({ category: '', amount: '', description: '' });
  const [fundItemError, setFundItemError] = useState('');
  const [fundItemSubmitting, setFundItemSubmitting] = useState(false);

  // --- Investisseurs (qui a financé, coordonnées si consenties) ---
  const [investments, setInvestments] = useState([]);
  const [investmentsError, setInvestmentsError] = useState('');

  // --- Section C : plan de remboursement en nature (paliers) ---
  const [refundPlan, setRefundPlan] = useState(null);
  const [refundPlanChecked, setRefundPlanChecked] = useState(false);
  const [tiers, setTiers] = useState([{ ...emptyTier, tier_max_amount: '' }]);
  const [startDate, setStartDate] = useState('');
  const [tierAddError, setTierAddError] = useState('');
  const [refundSubmitting, setRefundSubmitting] = useState(false);
  const [refundCreateError, setRefundCreateError] = useState('');
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

  async function handleUpload(e) {
    e.preventDefault();
    if (!file) {
      setUploadError('Choisissez un fichier.');
      return;
    }
    setUploadError('');
    setUploading(true);
    try {
      await uploadDocument(id, file, docType);
      setFile(null);
      e.target.reset();
      await refresh();
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(documentId) {
    try {
      await deleteDocument(documentId);
      await refresh();
    } catch (err) {
      setUploadError(err.message);
    }
  }

  async function handleSubmitDossier() {
    setSubmitError('');
    setSubmitting(true);
    try {
      const updated = await submitProject(id);
      setProject(updated);
      setSubmitted(true);
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  function updateProfile(field, value) {
    setProfileSaved(false);
    setProfile((p) => ({ ...p, [field]: value }));
  }

  function toggleBeneficiary(key) {
    setProfileSaved(false);
    setProfile((p) => ({
      ...p,
      target_beneficiaries: p.target_beneficiaries.includes(key)
        ? p.target_beneficiaries.filter((b) => b !== key)
        : [...p.target_beneficiaries, key],
    }));
  }

  async function handleSaveProfile() {
    setProfileError('');
    setProfileSaving(true);
    try {
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
      setProfileSaved(true);
    } catch (err) {
      setProfileError(err.message);
    } finally {
      setProfileSaving(false);
    }
  }

  async function handleAddFundItem(e) {
    e.preventDefault();
    if (!newFundItem.category || !newFundItem.amount) {
      setFundItemError('Le poste et le montant sont requis.');
      return;
    }
    setFundItemError('');
    setFundItemSubmitting(true);
    try {
      await createFundUsageItem(id, {
        category: newFundItem.category,
        amount: Number(newFundItem.amount),
        description: newFundItem.description || undefined,
      });
      setNewFundItem({ category: '', amount: '', description: '' });
      await refresh();
    } catch (err) {
      setFundItemError(err.message);
    } finally {
      setFundItemSubmitting(false);
    }
  }

  async function handleDeleteFundItem(itemId) {
    try {
      await deleteFundUsageItem(itemId);
      await refresh();
    } catch (err) {
      setFundItemError(err.message);
    }
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

  async function handleCreateRefundPlan(e) {
    e.preventDefault();
    setRefundCreateError('');
    setRefundSubmitting(true);
    try {
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
    } catch (err) {
      setRefundCreateError(err.message);
    } finally {
      setRefundSubmitting(false);
    }
  }

  async function handleDeliver(installmentId) {
    try {
      await deliverInstallment(installmentId);
      const [updatedPlan, updatedProject] = await Promise.all([getRefundPlan(id), getProject(id)]);
      setRefundPlan(updatedPlan);
      setProject(updatedProject);
    } catch (err) {
      setRefundCreateError(err.message);
    }
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
                        <button className="doc-remove" onClick={() => handleDelete(doc.id)}>
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
                  {uploadError && <div className="form-error">{uploadError}</div>}
                  <div className="upload-row">
                    <div className="field">
                      <label htmlFor="doc_type">Type de document</label>
                      <select id="doc_type" value={docType} onChange={(e) => setDocType(e.target.value)}>
                        {DOC_TYPES.map((t) => (
                          <option key={t} value={t}>{DOCUMENT_TYPE_LABELS[t]}</option>
                        ))}
                      </select>
                    </div>
                    <div className="field">
                      <label htmlFor="file">Fichier</label>
                      <input
                        id="file" type="file" accept=".jpg,.jpeg,.png,.webp,.pdf"
                        onChange={(e) => setFile(e.target.files[0])}
                      />
                    </div>
                    <button className="btn-secondary" type="submit" disabled={uploading}>
                      {uploading ? 'Envoi...' : 'Ajouter'}
                    </button>
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
                <div className="success-banner">Dossier soumis avec succès, en cours d'analyse.</div>
              </>
            ) : isDraft ? (
              <>
                <h3>Soumettre le dossier</h3>
                <p>
                  Une fois soumis, le dossier est verrouillé et analysé automatiquement avant
                  validation par notre équipe. Vous ne pourrez plus modifier les documents.
                </p>
                {documents.length === 0 && (
                  <div className="info-banner">
                    Aucun document ajouté. Un dossier plus complet est analysé plus favorablement.
                  </div>
                )}
                {refundPlanChecked && !refundPlan && (
                  <div className="info-banner">
                    Définissez votre plan de remboursement en nature (onglet "Plan de remboursement")
                    avant de soumettre — il ne sera plus possible d'en ajouter un après la soumission.
                  </div>
                )}
                {submitError && <div className="form-error">{submitError}</div>}
                <button
                  className="btn-primary btn-block" onClick={handleSubmitDossier}
                  disabled={submitting || !refundPlanChecked || !refundPlan}
                >
                  {submitting ? 'Envoi...' : 'Soumettre pour analyse'}
                </button>
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
                        <button className="doc-remove" onClick={() => handleDeleteFundItem(item.id)}>
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
              {fundItemError && <div className="form-error">{fundItemError}</div>}
              <div className="field-row">
                <div className="field">
                  <label htmlFor="fund_category">Poste de dépense</label>
                  <input
                    id="fund_category" value={newFundItem.category}
                    onChange={(e) => setNewFundItem((f) => ({ ...f, category: e.target.value }))}
                  />
                </div>
                <div className="field">
                  <label htmlFor="fund_amount">Montant (MAD)</label>
                  <input
                    id="fund_amount" type="number" min="0" step="1" value={newFundItem.amount}
                    onChange={(e) => setNewFundItem((f) => ({ ...f, amount: e.target.value }))}
                  />
                </div>
              </div>
              <div className="field">
                <label htmlFor="fund_description">Détail / justificatif (optionnel)</label>
                <input
                  id="fund_description" value={newFundItem.description}
                  onChange={(e) => setNewFundItem((f) => ({ ...f, description: e.target.value }))}
                />
              </div>
              <button className="btn-secondary" type="submit" disabled={fundItemSubmitting}>
                {fundItemSubmitting ? 'Ajout...' : '+ Ajouter un poste'}
              </button>
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
            <div className="field">
              <label htmlFor="legal_status">Statut juridique</label>
              <select
                id="legal_status" value={profile.legal_status} disabled={!isDraft}
                onChange={(e) => updateProfile('legal_status', e.target.value)}
              >
                <option value="">—</option>
                {LEGAL_STATUSES.map((s) => (
                  <option key={s} value={s}>{LEGAL_STATUS_LABELS[s]}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="legal_id_number">Numéro ICE / RC</label>
              <input
                id="legal_id_number" value={profile.legal_id_number} disabled={!isDraft}
                onChange={(e) => updateProfile('legal_id_number', e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="activity_start_year">Année de début d'activité</label>
              <input
                id="activity_start_year" type="number" min="1900" value={profile.activity_start_year}
                disabled={!isDraft}
                onChange={(e) => updateProfile('activity_start_year', e.target.value)}
              />
            </div>
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
            <div className="field">
              <label htmlFor="jobs_created">Emplois créés</label>
              <input
                id="jobs_created" type="number" min="0" value={profile.jobs_created} disabled={!isDraft}
                onChange={(e) => updateProfile('jobs_created', e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="jobs_maintained">Emplois maintenus</label>
              <input
                id="jobs_maintained" type="number" min="0" value={profile.jobs_maintained} disabled={!isDraft}
                onChange={(e) => updateProfile('jobs_maintained', e.target.value)}
              />
            </div>
          </div>

          <div className="field">
            <label htmlFor="social_impact_description">Description de l'impact</label>
            <textarea
              id="social_impact_description" value={profile.social_impact_description} disabled={!isDraft}
              onChange={(e) => updateProfile('social_impact_description', e.target.value)}
            />
          </div>

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
            <div className="field">
              <label htmlFor="previous_funding_details">Détails (montant, source, remboursé ?)</label>
              <textarea
                id="previous_funding_details" value={profile.previous_funding_details} disabled={!isDraft}
                onChange={(e) => updateProfile('previous_funding_details', e.target.value)}
              />
            </div>
          )}

          <div className="field">
            <label htmlFor="risk_factors">Facteurs de risque identifiés</label>
            <textarea
              id="risk_factors" value={profile.risk_factors} disabled={!isDraft}
              onChange={(e) => updateProfile('risk_factors', e.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="pitch_summary">Résumé en une phrase</label>
            <input
              id="pitch_summary" maxLength={140} value={profile.pitch_summary} disabled={!isDraft}
              onChange={(e) => updateProfile('pitch_summary', e.target.value)}
            />
            <p className="field-hint">{profile.pitch_summary.length} / 140</p>
          </div>

          <div className="field">
            <label htmlFor="references_text">Références (clients, partenaires...)</label>
            <textarea
              id="references_text" value={profile.references_text} disabled={!isDraft}
              onChange={(e) => updateProfile('references_text', e.target.value)}
            />
          </div>

          {isDraft && (
            <>
              {profileError && <div className="form-error">{profileError}</div>}
              {profileSaved && <div className="success-banner">Informations enregistrées.</div>}
              <button className="btn-secondary" onClick={handleSaveProfile} disabled={profileSaving}>
                {profileSaving ? 'Enregistrement...' : 'Enregistrer les informations complémentaires'}
              </button>
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

            {investmentsError && <div className="form-error">{investmentsError}</div>}

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
                                  <button className="doc-remove" onClick={() => handleDeliver(installment.id)}>
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

                <div className="field">
                  <label htmlFor="start_date">Date de départ</label>
                  <input
                    id="start_date" type="date" required value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </div>

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
                        <div className="field">
                          <label htmlFor={`tier_max_${index}`}>Max investi (MAD)</label>
                          <input
                            id={`tier_max_${index}`} type="number" min={min || 0}
                            placeholder="∞ (dernier palier)" value={tier.tier_max_amount}
                            onChange={(e) => updateTier(index, 'tier_max_amount', e.target.value)}
                          />
                        </div>
                        <div className="field">
                          <label htmlFor={`tier_freq_${index}`}>Fréquence</label>
                          <select
                            id={`tier_freq_${index}`} value={tier.frequency}
                            onChange={(e) => updateTier(index, 'frequency', e.target.value)}
                          >
                            {FREQUENCIES.map((f) => (
                              <option key={f} value={f}>{REPAYMENT_FREQUENCY_LABELS[f]}</option>
                            ))}
                          </select>
                        </div>
                      </div>
                      <div className="field-row">
                        <div className="field">
                          <label htmlFor={`tier_product_${index}`}>Nature du bien</label>
                          <input
                            id={`tier_product_${index}`} required value={tier.product_description}
                            onChange={(e) => updateTier(index, 'product_description', e.target.value)}
                          />
                        </div>
                        <div className="field">
                          <label htmlFor={`tier_unit_${index}`}>Unité</label>
                          <input
                            id={`tier_unit_${index}`} required value={tier.unit}
                            onChange={(e) => updateTier(index, 'unit', e.target.value)}
                          />
                        </div>
                        <div className="field">
                          <label htmlFor={`tier_qty_${index}`}>Quantité / échéance</label>
                          <input
                            id={`tier_qty_${index}`} type="number" min="0" step="0.01" required
                            value={tier.quantity_per_occurrence}
                            onChange={(e) => updateTier(index, 'quantity_per_occurrence', e.target.value)}
                          />
                        </div>
                      </div>
                      <div className="field-row">
                        <div className="field">
                          <label htmlFor={`tier_count_${index}`}>Nombre d'échéances</label>
                          <input
                            id={`tier_count_${index}`} type="number" min="1" max="60" required
                            value={tier.installments_count}
                            onChange={(e) => updateTier(index, 'installments_count', e.target.value)}
                          />
                        </div>
                        <div className="field">
                          <label htmlFor={`tier_value_${index}`}>Valeur unitaire estimée (MAD)</label>
                          <input
                            id={`tier_value_${index}`} type="number" min="0" value={tier.estimated_unit_value}
                            onChange={(e) => updateTier(index, 'estimated_unit_value', e.target.value)}
                          />
                          <p className="field-hint">Facultatif — sert uniquement à un avertissement de couverture.</p>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {tierAddError && <div className="form-error">{tierAddError}</div>}
                <button type="button" className="btn-secondary" onClick={addTierRow} style={{ marginBottom: 18 }}>
                  + Ajouter un palier
                </button>

                {refundCreateError && <div className="form-error">{refundCreateError}</div>}

                <button className="btn-primary btn-block" type="submit" disabled={refundSubmitting}>
                  {refundSubmitting ? 'Création...' : 'Créer le plan de remboursement'}
                </button>
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
      <Footer />
    </>
  );
}
