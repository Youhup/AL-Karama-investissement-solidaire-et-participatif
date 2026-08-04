import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import StatusBadge from '../components/StatusBadge';
import { listMyInvestments, listRefundAllocations } from '../api/investments';
import { getProject } from '../api/projects';
import { INSTALLMENT_STATUS_LABELS } from '../utils/labels';

export default function MyPortfolio() {
  const [rows, setRows] = useState([]); // investissements enrichis du titre/statut du projet
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [openId, setOpenId] = useState(null);
  const [allocations, setAllocations] = useState({});
  const [allocLoading, setAllocLoading] = useState(false);

  useEffect(() => {
    async function load() {
      const investments = await listMyInvestments();
      const uniqueProjectIds = [...new Set(investments.map((inv) => inv.project_id))];
      const projects = await Promise.all(uniqueProjectIds.map((id) => getProject(id)));
      const projectsById = Object.fromEntries(projects.map((p) => [p.id, p]));

      setRows(investments.map((inv) => ({ ...inv, project: projectsById[inv.project_id] })));
    }
    load().catch((err) => setError(err.message)).finally(() => setLoading(false));
  }, []);

  const totalInvested = rows.reduce((sum, r) => sum + Number(r.amount), 0);
  const projectsCount = new Set(rows.map((r) => r.project_id)).size;

  async function toggleAllocations(investmentId) {
    if (openId === investmentId) {
      setOpenId(null);
      return;
    }
    setOpenId(investmentId);
    if (!allocations[investmentId]) {
      setAllocLoading(true);
      try {
        const data = await listRefundAllocations(investmentId);
        setAllocations((a) => ({ ...a, [investmentId]: data }));
      } catch (err) {
        setAllocations((a) => ({ ...a, [investmentId]: { error: err.message } }));
      } finally {
        setAllocLoading(false);
      }
    }
  }

  return (
    <>
      <Navbar />
      <div className="wrap form-page">
        <div className="dashboard-header">
          <div>
            <h1 className="page-title">Mon portefeuille</h1>
            <p>Vos investissements et le suivi de vos remboursements en nature.</p>
          </div>
          <Link className="btn-secondary" to="/projets">Découvrir d'autres projets</Link>
        </div>

        {loading && <p>Chargement...</p>}
        {error && <div className="form-error">{error}</div>}

        {!loading && !error && rows.length === 0 && (
          <div className="empty-state">
            Vous n'avez pas encore investi. <Link to="/projets">Explorez les projets ouverts au financement</Link>.
          </div>
        )}

        {rows.length > 0 && (
          <>
            <div className="stats-bar">
              <div className="stat-block">
                <div className="stat-value">{totalInvested.toLocaleString('fr-FR')} MAD</div>
                <div className="stat-label">Total investi</div>
              </div>
              <div className="stat-block">
                <div className="stat-value">{projectsCount}</div>
                <div className="stat-label">Projet{projectsCount > 1 ? 's' : ''} soutenu{projectsCount > 1 ? 's' : ''}</div>
              </div>
            </div>

            <div className="list-rows">
              {rows.map((r) => {
                const canTrackRefund = r.project && ['en_remboursement', 'clos'].includes(r.project.status);
                return (
                  <div key={r.id}>
                    <div className="list-row" style={{ cursor: canTrackRefund ? 'default' : 'default' }}>
                      <div className="list-row-main">
                        <h3>{r.project?.title || 'Projet'}</h3>
                        <span className="list-row-sub">
                          Investi le {new Date(r.invested_at).toLocaleDateString('fr-FR')}
                        </span>
                      </div>
                      <div className="list-row-figures">
                        {r.project && <StatusBadge status={r.project.status} />}
                        <div className="amount" style={{ marginTop: 6 }}>
                          {Number(r.amount).toLocaleString('fr-FR')} MAD
                        </div>
                      </div>
                      {canTrackRefund && (
                        <button className="btn-toggle" onClick={() => toggleAllocations(r.id)}>
                          {openId === r.id ? 'Masquer' : 'Suivi remboursement'}
                        </button>
                      )}
                    </div>

                    {openId === r.id && (
                      <div style={{ padding: '0 20px' }}>
                        {allocLoading && !allocations[r.id] && <p className="field-hint">Chargement...</p>}
                        {allocations[r.id]?.error && <div className="form-error">{allocations[r.id].error}</div>}
                        {Array.isArray(allocations[r.id]) && (
                          <table className="allocation-table">
                            <thead>
                              <tr>
                                <th>Échéance</th>
                                <th>Date prévue</th>
                                <th>Quantité à recevoir</th>
                                <th>Statut</th>
                              </tr>
                            </thead>
                            <tbody>
                              {allocations[r.id].map((a) => (
                                <tr key={a.id}>
                                  <td>#{a.installment_number}</td>
                                  <td>{new Date(a.due_date).toLocaleDateString('fr-FR')}</td>
                                  <td>{a.quantity_allocated}</td>
                                  <td>{INSTALLMENT_STATUS_LABELS[a.status] || a.status}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
      <Footer />
    </>
  );
}
