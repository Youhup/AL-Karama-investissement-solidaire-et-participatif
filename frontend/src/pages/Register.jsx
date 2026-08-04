import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const ROLES = [
  {
    value: 'porteur',
    label: 'Porteur de projet',
    hint: 'Agriculteur, éleveur, artisan ou commerçant',
  },
  {
    value: 'investisseur',
    label: 'Investisseur',
    hint: 'Je souhaite soutenir des projets locaux',
  },
];

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    full_name: '', email: '', phone: '', password: '', confirmPassword: '', role: 'investisseur',
  });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');

    if (form.password !== form.confirmPassword) {
      setError('Les mots de passe ne correspondent pas.');
      return;
    }
    if (form.password.length < 8) {
      setError('Le mot de passe doit contenir au moins 8 caractères.');
      return;
    }

    setSubmitting(true);
    try {
      const user = await register({
        full_name: form.full_name,
        email: form.email,
        phone: form.phone || undefined,
        password: form.password,
        role: form.role,
      });
      navigate(user.role === 'porteur' ? '/mes-projets' : '/projets', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Créer un compte</h1>
        <p className="auth-subtitle">Rejoignez la communauté d'investissement solidaire.</p>

        {error && <div className="form-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="role-select">
            {ROLES.map((r) => (
              <div
                key={r.value}
                className={`role-option ${form.role === r.value ? 'active' : ''}`}
                onClick={() => update('role', r.value)}
                role="button"
                tabIndex={0}
              >
                <strong>{r.label}</strong>
                <span>{r.hint}</span>
              </div>
            ))}
          </div>

          <div className="field">
            <label htmlFor="full_name">Nom complet</label>
            <input
              id="full_name" required value={form.full_name}
              onChange={(e) => update('full_name', e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="email">Adresse email</label>
            <input
              id="email" type="email" required autoComplete="email" value={form.email}
              onChange={(e) => update('email', e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="phone">Téléphone (optionnel)</label>
            <input
              id="phone" type="tel" value={form.phone}
              onChange={(e) => update('phone', e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="password">Mot de passe</label>
            <input
              id="password" type="password" required autoComplete="new-password" value={form.password}
              onChange={(e) => update('password', e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="confirmPassword">Confirmer le mot de passe</label>
            <input
              id="confirmPassword" type="password" required autoComplete="new-password"
              value={form.confirmPassword}
              onChange={(e) => update('confirmPassword', e.target.value)}
            />
          </div>

          <button className="btn-primary btn-block" type="submit" disabled={submitting}>
            {submitting ? 'Création...' : 'Créer mon compte'}
          </button>
        </form>

        <p className="auth-switch">
          Déjà inscrit ? <Link to="/connexion">Se connecter</Link>
        </p>
      </div>
    </div>
  );
}
