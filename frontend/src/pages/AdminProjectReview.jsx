import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import StatusBadge from '../components/StatusBadge';
import {
  downloadDocument, getProject, getProjectAnalysis, listDocuments, listFundUsageItems, listSectors,
  submitAdminDecision,
} from '../api/projects';
import { getRefundPlan } from '../api/refunds';
import {
  DOCUMENT_TYPE_LABELS, VERDICT_LABELS, SEVERITY_LABELS, PROJECT_STAGE_LABELS,
  LEGAL_STATUS_LABELS, BENEFICIARY_LABELS, PROJECT_STATUS_LABELS, REPAYMENT_FREQUENCY_LABELS,
} from '../utils/labels';

export default function AdminProjectReview() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [fundUsageItems, setFundUsageItems] = useState([]);
  const [sectorsById, setSectorsById] = useState({});
  const [analysis, setAnalysis] = useState(null);
  const [analysisError, setAnalysisError] = useState('');
  const [refundPlan, setRefundPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [downloadingId, setDownloadingId] = useState(null);
  const [downloadError, setDownloadError] = useState('');

  const [decision, setDecision] = useState('valide');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    async function load() {
      const [p, docs, items, sectors] = await Promise.all([
        getProject(id), listDocuments(id), listFundUsageItems(id), listSectors(),
      ]);
      setProject(p);
      setDocuments(docs);
      setFundUsageItems(items);
      setSectorsById(Object.fromEntries(sectors.map((s) => [s.id, s.name])));
      try {
        const report = await getProjectAnalysis(id);
        setAnalysis(report);
      } catch (err) {
        setAnalysisError(err.message); // ex: "Aucune analyse disponible" si pas encore traité
      }
      try {
        setRefundPlan(await getRefundPlan(id));
      } catch {
        setRefundPlan(null); // pas encore défini par le porteur
      }
    }
    load().catch((err) => setLoadError(err.message)).finally(() => setLoading(false));
  }, [id]);

  async function handleDownload(doc) {
    setDownloadError('');
    setDownloadingId(doc.id);
    try {
      await downloadDocument(doc.id, doc.original_name);
    } catch (err) {
      setDownloadError(err.message);
    } finally {
      setDownloadingId(null);
    }
  }

  async function handleDecision(e) {
    e.preventDefault();
    setSubmitError('');
    setSubmitting(true);
    try {
      await submitAdminDecision(id, decision, notes);
      setSubmitted(true);
      setTimeout(() => navigate('/admin'), 1200);
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (<><Navbar /><div className="wrap form-page"><p>Chargement...</p></div><Footer /></>);
  }
  if (loadError || !project) {
    return (<><Navbar /><div className="wrap form-page"><div className="form-error">{loadError || 'Introuvable.'}</div></div><Footer /></>);
  }

  return (
    <>
      <Navbar />
      <div className="wrap form-page">
        <div className="dossier-header">
          <div>
            <h1 className="page-title">{project.title}</h1>
            <p className="page-subtitle" style={{ marginBottom: 0 }}>
              {sectorsById[project.sector_id] || 'Secteur inconnu'}
              {' · '}{Number(project.amount_requested).toLocaleString('fr-FR')} MAD demandés
              {project.city ? ` · ${project.city}${project.region ? `, ${project.region}` : ''}` : ''}
              {project.funding_duration_days ? ` · collecte sur ${project.funding_duration_days} j` : ''}
            </p>
          </div>
          <StatusBadge status={project.status} />
        </div>

        <div className="dossier-grid">
          <div>
            <div className="upload-box">
              <h3 style={{ marginBottom: 14 }}>Description</h3>
              <p className="detail-description" style={{ marginBottom: 0 }}>{project.description}</p>
              {project.pitch_summary && (
                <p className="field-hint" style={{ marginTop: 10 }}>« {project.pitch_summary} »</p>
              )}
            </div>

            <div className="upload-box">
              <h3 style={{ marginBottom: 14 }}>Statut juridique et identité</h3>
              <ul className="kv-list">
                <li><span>Statut juridique</span><strong>{LEGAL_STATUS_LABELS[project.legal_status] || '—'}</strong></li>
                <li><span>N° d'identification légale</span><strong>{project.legal_id_number || '—'}</strong></li>
                <li><span>Stade du projet</span><strong>{PROJECT_STAGE_LABELS[project.project_stage] || '—'}</strong></li>
                <li><span>Début d'activité</span><strong>{project.activity_start_year || '—'}</strong></li>
              </ul>
            </div>

            <div className="upload-box">
              <h3 style={{ marginBottom: 14 }}>Impact social</h3>
              <ul className="kv-list">
                <li>
                  <span>Bénéficiaires ciblés</span>
                  <strong>
                    {project.target_beneficiaries?.length
                      ? project.target_beneficiaries.map((b) => BENEFICIARY_LABELS[b] || b).join(', ')
                      : '—'}
                  </strong>
                </li>
                <li><span>Emplois créés</span><strong>{project.jobs_created ?? 0}</strong></li>
                <li><span>Emplois maintenus</span><strong>{project.jobs_maintained ?? 0}</strong></li>
              </ul>
              {project.social_impact_description && (
                <p className="detail-description" style={{ marginTop: 12, marginBottom: 0 }}>
                  {project.social_impact_description}
                </p>
              )}
            </div>

            <div className="upload-box">
              <h3 style={{ marginBottom: 14 }}>Confiance et historique</h3>
              <ul className="kv-list">
                <li><span>Financement antérieur</span><strong>{project.previous_funding ? 'Oui' : 'Non'}</strong></li>
              </ul>
              {project.previous_funding_details && (
                <p className="detail-description" style={{ marginTop: 4 }}>{project.previous_funding_details}</p>
              )}
              {project.risk_factors && (
                <>
                  <p className="field-hint" style={{ marginBottom: 2 }}>Facteurs de risque déclarés :</p>
                  <p className="detail-description" style={{ marginBottom: 0 }}>{project.risk_factors}</p>
                </>
              )}
            </div>

            {project.references_text && (
              <div className="upload-box">
                <h3 style={{ marginBottom: 14 }}>Références</h3>
                <p className="detail-description" style={{ marginBottom: 0 }}>{project.references_text}</p>
              </div>
            )}

            <div className="upload-box">
              <h3 style={{ marginBottom: 14 }}>Utilisation des fonds</h3>
              {fundUsageItems.length === 0 ? (
                <p className="field-hint" style={{ marginTop: 0 }}>Aucune répartition fournie.</p>
              ) : (
                <ul className="doc-list-readonly">
                  {fundUsageItems.map((it) => (
                    <li key={it.id}>
                      {it.category} — <span style={{ color: 'var(--cedre-clair)' }}>
                        {Number(it.amount).toLocaleString('fr-FR')} MAD
                      </span>
                      {it.description ? ` — ${it.description}` : ''}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="upload-box">
              <h3 style={{ marginBottom: 14 }}>Plan de remboursement en nature</h3>
              {!refundPlan ? (
                <p className="field-hint" style={{ marginTop: 0 }}>Pas encore défini par le porteur.</p>
              ) : (
                <ul className="doc-list-readonly">
                  {refundPlan.tiers.map((tier) => (
                    <li key={tier.id}>
                      <strong>{tier.product_description}</strong> — {tier.quantity_per_occurrence} {tier.unit}{' '}
                      / {REPAYMENT_FREQUENCY_LABELS[tier.frequency].toLowerCase()}, pour les investissements de{' '}
                      {Number(tier.tier_min_amount).toLocaleString('fr-FR')} MAD
                      {tier.tier_max_amount != null
                        ? ` à ${Number(tier.tier_max_amount).toLocaleString('fr-FR')} MAD`
                        : ' et plus'}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="upload-box">
              <h3 style={{ marginBottom: 14 }}>Documents fournis</h3>
              {downloadError && <div className="form-error">{downloadError}</div>}
              {documents.length === 0 ? (
                <p className="field-hint" style={{ marginTop: 0 }}>Aucun document fourni.</p>
              ) : (
                <ul className="doc-list-readonly">
                  {documents.map((d) => (
                    <li key={d.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
                      <span>
                        {d.original_name} — <span style={{ color: 'var(--cedre-clair)' }}>{DOCUMENT_TYPE_LABELS[d.doc_type]}</span>
                      </span>
                      <button
                        type="button"
                        className="btn-secondary"
                        style={{ padding: '6px 14px', fontSize: 13, whiteSpace: 'nowrap' }}
                        onClick={() => handleDownload(d)}
                        disabled={downloadingId === d.id}
                      >
                        {downloadingId === d.id ? 'Ouverture...' : 'Voir / Télécharger'}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div>
            <div className="submit-panel" style={{ marginBottom: 20 }}>
              <h3>Analyse IA</h3>
              {analysisError && <p className="field-hint" style={{ marginTop: 0 }}>{analysisError}</p>}
              {analysis && (
                <>
                  <span className={`verdict-badge ${analysis.verdict}`}>
                    {VERDICT_LABELS[analysis.verdict] || analysis.verdict}
                  </span>
                  <div className="score-grid">
                    <div className="score-block">
                      <div className="score-value">{analysis.relevance_score ?? '—'}</div>
                      <div className="score-label">Pertinence / 100</div>
                    </div>
                    <div className="score-block">
                      <div className="score-value">{analysis.fraud_risk_score ?? '—'}</div>
                      <div className="score-label">Risque de fraude / 100</div>
                    </div>
                  </div>
                  {analysis.findings?.length > 0 && (
                    <ul className="findings-list">
                      {analysis.findings.map((f, i) => (
                        <li key={i} className={`finding-item ${f.severite}`}>
                          <span className="finding-type">{f.type} · {SEVERITY_LABELS[f.severite] || f.severite}</span>
                          {f.description}
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              )}
            </div>

            <div className="submit-panel">
              <h3>Décision</h3>
              {submitError && <div className="form-error">{submitError}</div>}
              {submitted ? (
                <div className="success-banner">Décision enregistrée.</div>
              ) : project.status !== 'a_valider' ? (
                <p className="field-hint" style={{ marginTop: 0 }}>
                  Ce dossier a déjà été traité — statut actuel :{' '}
                  <strong>{PROJECT_STATUS_LABELS[project.status] || project.status}</strong>.
                  Il ne peut plus être validé ou rejeté depuis cette page.
                </p>
              ) : (
                <form onSubmit={handleDecision}>
                  <div className="decision-radio">
                    <div
                      className={`decision-option ${decision === 'valide' ? 'active valide' : ''}`}
                      onClick={() => setDecision('valide')}
                    >
                      Valider
                    </div>
                    <div
                      className={`decision-option ${decision === 'rejete' ? 'active rejete' : ''}`}
                      onClick={() => setDecision('rejete')}
                    >
                      Rejeter
                    </div>
                  </div>
                  <div className="field">
                    <label htmlFor="notes">Note (optionnel)</label>
                    <textarea id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
                  </div>
                  <button
                    className={`btn-block ${decision === 'rejete' ? 'btn-danger' : 'btn-primary'}`}
                    type="submit"
                    disabled={submitting}
                  >
                    {submitting ? 'Envoi...' : decision === 'rejete' ? 'Confirmer le rejet' : 'Confirmer la validation'}
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      </div>
      <Footer />
    </>
  );
}
