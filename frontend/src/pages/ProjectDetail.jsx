import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import StatusBadge from '../components/StatusBadge';
import ZelligeProgressRing from '../components/ZelligeProgressRing';
import { useAuth } from '../context/AuthContext';
import { getProject, investInProject, listFundUsageItems, listSectors } from '../api/projects';
import { getRefundPlan } from '../api/refunds';
import { API_URL } from '../api/client';
import {
  BENEFICIARY_LABELS, LEGAL_STATUS_LABELS, PROJECT_STAGE_LABELS, REPAYMENT_FREQUENCY_LABELS,
} from '../utils/labels';
import { deadlineBadge } from '../utils/funding';

const INVESTABLE_STATUSES = ['valide', 'en_financement'];
const PLATFORM_MIN_INVESTMENT = 100;

export default function ProjectDetail() {
  const { id } = useParams();
  const { user } = useAuth();

  const [project, setProject] = useState(null);
  const [sectorsById, setSectorsById] = useState({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [refundPlan, setRefundPlan] = useState(null);
  const [fundItems, setFundItems] = useState([]);

  const [amount, setAmount] = useState('');
  const [investError, setInvestError] = useState('');
  const [investing, setInvesting] = useState(false);
  const [investSuccess, setInvestSuccess] = useState(false);
  const [showConsentModal, setShowConsentModal] = useState(false);

  async function refresh() {
    const [p, sectors] = await Promise.all([getProject(id), listSectors()]);
    setProject(p);
    setSectorsById(Object.fromEntries(sectors.map((s) => [s.id, s.name])));
  }

  useEffect(() => {
    refresh().catch((err) => setLoadError(err.message)).finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    // Le plan (s'il existe déjà) est public : un investisseur potentiel doit
    // pouvoir voir les contreparties avant d'investir. 404 = pas encore
    // défini par le porteur, on l'ignore simplement.
    getRefundPlan(id).then(setRefundPlan).catch(() => setRefundPlan(null));
  }, [id]);

  useEffect(() => {
    listFundUsageItems(id).then(setFundItems).catch(() => setFundItems([]));
  }, [id]);

  function handleInvest(e) {
    e.preventDefault();
    setInvestError('');
    setInvestSuccess(false);

    const value = Number(amount);
    if (!value || value < PLATFORM_MIN_INVESTMENT || value % PLATFORM_MIN_INVESTMENT !== 0) {
      setInvestError(
        `Le montant doit être un multiple de ${PLATFORM_MIN_INVESTMENT} MAD (minimum ${PLATFORM_MIN_INVESTMENT} MAD).`
      );
      return;
    }

    setShowConsentModal(true);
  }

  async function confirmInvest(shareContactConsent) {
    const value = Number(amount);
    setShowConsentModal(false);
    setInvesting(true);
    try {
      await investInProject(id, value, shareContactConsent);
      setAmount('');
      setInvestSuccess(true);
      await refresh();
    } catch (err) {
      setInvestError(err.message);
    } finally {
      setInvesting(false);
    }
  }

  if (loading) {
    return (
      <>
        <Navbar />
        <div className="wrap section"><p>Chargement du projet...</p></div>
        <Footer />
      </>
    );
  }

  if (loadError || !project) {
    return (
      <>
        <Navbar />
        <div className="wrap section"><div className="form-error">{loadError || 'Projet introuvable.'}</div></div>
        <Footer />
      </>
    );
  }

  const percent = project.amount_requested > 0
    ? (project.amount_raised / project.amount_requested) * 100
    : 0;
  const remaining = Math.max(0, project.amount_requested - project.amount_raised);
  const isInvestable = INVESTABLE_STATUSES.includes(project.status);
  const badge = deadlineBadge(project.status, project.funding_deadline);

  return (
    <>
      <Navbar />
      <div className="wrap section">
        {project.photo_url && (
          <div className="detail-image">
            <img src={`${API_URL}${project.photo_url}`} alt={project.title} />
          </div>
        )}

        <div className="dossier-header">
          <div>
            <h1 className="page-title">{project.title}</h1>
            <div className="detail-meta">
              <span>{sectorsById[project.sector_id] || 'Projet'}</span>
              {project.city && <span>· {project.city}{project.region ? `, ${project.region}` : ''}</span>}
            </div>
          </div>
          <StatusBadge status={project.status} />
        </div>

        <div className="detail-grid">
          <div>
            {project.pitch_summary && (
              <p className="field-hint" style={{ marginTop: 0, fontSize: 15.5, fontStyle: 'italic' }}>
                « {project.pitch_summary} »
              </p>
            )}
            <p className="detail-description">{project.description}</p>

            {(project.legal_status || project.legal_id_number || project.project_stage || project.activity_start_year) && (
              <div className="upload-box">
                <h3 style={{ marginBottom: 14 }}>Statut juridique et identité</h3>
                <ul className="kv-list">
                  <li><span>Statut juridique</span><strong>{LEGAL_STATUS_LABELS[project.legal_status] || '—'}</strong></li>
                  <li><span>N° d'identification légale</span><strong>{project.legal_id_number || '—'}</strong></li>
                  <li><span>Stade du projet</span><strong>{PROJECT_STAGE_LABELS[project.project_stage] || '—'}</strong></li>
                  <li><span>Début d'activité</span><strong>{project.activity_start_year || '—'}</strong></li>
                </ul>
              </div>
            )}

            {(project.target_beneficiaries?.length > 0 || project.jobs_created > 0 || project.jobs_maintained > 0 || project.social_impact_description) && (
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
            )}

            {(project.previous_funding || project.risk_factors) && (
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
            )}

            {project.references_text && (
              <div className="upload-box">
                <h3 style={{ marginBottom: 14 }}>Références</h3>
                <p className="detail-description" style={{ marginBottom: 0 }}>{project.references_text}</p>
              </div>
            )}

            {fundItems.length > 0 && (
              <div className="upload-box">
                <h3 style={{ marginBottom: 14 }}>Utilisation des fonds</h3>
                <ul className="doc-list-readonly">
                  {fundItems.map((it) => (
                    <li key={it.id}>
                      {it.category} — <span style={{ color: 'var(--cedre-clair)' }}>
                        {Number(it.amount).toLocaleString('fr-FR')} MAD
                      </span>
                      {it.description ? ` — ${it.description}` : ''}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {refundPlan && refundPlan.tiers.length > 0 && (
              <div className="form-panel" style={{ marginTop: 24 }}>
                <h3 style={{ marginBottom: 6 }}>Ce que vous recevrez en retour</h3>
                <p className="field-hint" style={{ marginTop: 0 }}>
                  Remboursement en nature, selon le montant investi :
                </p>
                {refundPlan.tiers.map((tier) => (
                  <div key={tier.id} className="card" style={{ marginBottom: 12 }}>
                    <strong>{tier.product_description}</strong> — {tier.quantity_per_occurrence} {tier.unit}{' '}
                    / {REPAYMENT_FREQUENCY_LABELS[tier.frequency].toLowerCase()}, pour les investissements de{' '}
                    {Number(tier.tier_min_amount).toLocaleString('fr-FR')} MAD
                    {tier.tier_max_amount != null
                      ? ` à ${Number(tier.tier_max_amount).toLocaleString('fr-FR')} MAD`
                      : ' et plus'}
                    .
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="invest-panel">
            <div className="invest-ring-row">
              <ZelligeProgressRing percent={percent} size={100} />
              <div className="invest-figures">
                <div className="amount-big">{Number(project.amount_raised).toLocaleString('fr-FR')} MAD</div>
                <div className="amount-sub">collectés sur {Number(project.amount_requested).toLocaleString('fr-FR')} MAD</div>
              </div>
            </div>

            {badge && (
              <div className={`deadline-tag ${badge.state}`} style={{ marginBottom: 4 }}>
                <span className="num">{badge.num}</span>
                <span className="unit">{badge.unit}</span>
              </div>
            )}

            <hr />

            {project.status === 'echoue' && (
              <p className="invest-cta-text">
                La collecte s'est terminée sans atteindre l'objectif de financement. Ce projet n'est
                plus ouvert aux investissements.
              </p>
            )}

            {project.status !== 'echoue' && !isInvestable && (
              <p className="invest-cta-text">
                Ce projet n'est pas (ou plus) ouvert au financement pour le moment.
              </p>
            )}

            {isInvestable && !user && (
              <>
                <p className="invest-cta-text">Connectez-vous en tant qu'investisseur pour financer ce projet.</p>
                <Link className="btn-primary btn-block" to="/connexion">Se connecter</Link>
              </>
            )}

            {isInvestable && user && user.role !== 'investisseur' && (
              <p className="invest-cta-text">
                Seuls les comptes investisseurs peuvent financer un projet.
              </p>
            )}

            {isInvestable && user && user.role === 'investisseur' && (
              <form onSubmit={handleInvest}>
                {investError && <div className="form-error">{investError}</div>}
                {investSuccess && <div className="success-banner">Investissement confirmé, merci !</div>}
                <div className="field">
                  <label htmlFor="amount">Montant à investir (MAD)</label>
                  <input
                    id="amount" type="number" min={PLATFORM_MIN_INVESTMENT} max={remaining}
                    step={PLATFORM_MIN_INVESTMENT} required
                    value={amount} onChange={(e) => setAmount(e.target.value)}
                    placeholder={`Reste ${remaining.toLocaleString('fr-FR')} MAD à financer`}
                  />
                  <p className="field-hint">
                    Montant minimum : {PLATFORM_MIN_INVESTMENT} MAD, par multiples de {PLATFORM_MIN_INVESTMENT}.
                  </p>
                </div>
                <button className="btn-primary btn-block" type="submit" disabled={investing}>
                  {investing ? 'Envoi...' : 'Investir'}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>

      {showConsentModal && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal-card">
            <h3>Partager vos coordonnées ?</h3>
            <p>
              Ce projet rembourse en nature (pas en argent). Pour vous livrer votre contrepartie, le
              porteur a besoin de connaître votre nom, votre téléphone et votre ville — uniquement
              une fois le remboursement démarré, et uniquement pour ce projet.
            </p>
            <div className="modal-warning">
              Si vous refusez, le porteur n'aura aucun moyen de vous identifier ni de vous contacter :
              vous ne recevrez pas votre contrepartie.
            </div>
            <div className="modal-actions">
              <button className="btn-primary btn-block" onClick={() => confirmInvest(true)} disabled={investing}>
                J'accepte de partager mes coordonnées
              </button>
              <button className="btn-secondary btn-block" onClick={() => confirmInvest(false)} disabled={investing}>
                Je refuse (je n'aurai pas ma contrepartie)
              </button>
              <button
                className="btn-secondary btn-block"
                style={{ border: 'none' }}
                onClick={() => setShowConsentModal(false)}
                disabled={investing}
              >
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}

      <Footer />
    </>
  );
}
