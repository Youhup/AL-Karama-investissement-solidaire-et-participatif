import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { useToast } from '../components/ui/ToastProvider';
import Alert from '../components/ui/Alert';
import Field from '../components/ui/Field';
import SubmitButton from '../components/ui/SubmitButton';

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
  const toast = useToast();

  const [form, setForm] = useState({
    full_name: '', email: '', phone: '', password: '', confirmPassword: '', role: 'investisseur',
  });
  const registerAction = useAsyncAction(() => register({
    full_name: form.full_name,
    email: form.email,
    phone: form.phone || undefined,
    password: form.password,
    role: form.role,
  }));

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();

    if (form.password !== form.confirmPassword) {
      registerAction.setError('Les mots de passe ne correspondent pas.');
      return;
    }
    if (form.password.length < 8) {
      registerAction.setError('Le mot de passe doit contenir au moins 8 caractères.');
      return;
    }

    const res = await registerAction.run();
    if (res.ok) {
      toast.success('Compte créé, bienvenue !');
      navigate(res.data.role === 'porteur' ? '/mes-projets' : '/projets', { replace: true });
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Créer un compte</h1>
        <p className="auth-subtitle">Rejoignez la communauté d'investissement solidaire.</p>

        <Alert variant="error">{registerAction.error}</Alert>

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

          <Field
            id="full_name" label="Nom complet" required value={form.full_name}
            onChange={(e) => update('full_name', e.target.value)}
          />
          <Field
            id="email" label="Adresse email" type="email" required autoComplete="email"
            value={form.email} onChange={(e) => update('email', e.target.value)}
          />
          <Field
            id="phone" label="Téléphone (optionnel)" type="tel" value={form.phone}
            onChange={(e) => update('phone', e.target.value)}
          />
          <Field
            id="password" label="Mot de passe" type="password" required autoComplete="new-password"
            hint="8 caractères minimum."
            value={form.password} onChange={(e) => update('password', e.target.value)}
          />
          <Field
            id="confirmPassword" label="Confirmer le mot de passe" type="password" required
            autoComplete="new-password" value={form.confirmPassword}
            onChange={(e) => update('confirmPassword', e.target.value)}
          />

          <SubmitButton className="btn-primary btn-block" pending={registerAction.pending} pendingLabel="Création...">
            Créer mon compte
          </SubmitButton>
        </form>

        <p className="auth-switch">
          Déjà inscrit ? <Link to="/connexion">Se connecter</Link>
        </p>
      </div>
    </div>
  );
}
