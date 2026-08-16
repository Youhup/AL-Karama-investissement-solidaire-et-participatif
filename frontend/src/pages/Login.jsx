import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useAsyncAction } from '../hooks/useAsyncAction';
import Alert from '../components/ui/Alert';
import Field from '../components/ui/Field';
import SubmitButton from '../components/ui/SubmitButton';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const auth = useAsyncAction(() => login(email, password));

  async function handleSubmit(e) {
    e.preventDefault();
    const res = await auth.run();
    if (res.ok) {
      const redirectTo = location.state?.from?.pathname || defaultRouteForRole(res.data.role);
      navigate(redirectTo, { replace: true });
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Connexion</h1>
        <p className="auth-subtitle">Accédez à votre espace porteur de projet ou investisseur.</p>

        <Alert variant="error">{auth.error}</Alert>

        <form onSubmit={handleSubmit}>
          <Field
            id="email" label="Adresse email" type="email" required autoComplete="email"
            value={email} onChange={(e) => setEmail(e.target.value)}
          />
          <Field
            id="password" label="Mot de passe" type="password" required autoComplete="current-password"
            value={password} onChange={(e) => setPassword(e.target.value)}
          />
          <SubmitButton className="btn-primary btn-block" pending={auth.pending} pendingLabel="Connexion...">
            Se connecter
          </SubmitButton>
        </form>

        <p className="auth-switch">
          Pas encore de compte ? <Link to="/inscription">Créer un compte</Link>
        </p>
      </div>
    </div>
  );
}

function defaultRouteForRole(role) {
  if (role === 'porteur') return '/mes-projets';
  if (role === 'investisseur') return '/mon-portefeuille';
  if (role === 'admin') return '/admin';
  return '/';
}
