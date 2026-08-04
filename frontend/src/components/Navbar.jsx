import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <nav className="navbar wrap">
      <div className="logo">
        <svg width="30" height="30" viewBox="0 0 40 40" aria-hidden="true">
          <polygon
            points="20,3 24,16 37,16 26,24 30,37 20,29 10,37 14,24 3,16 16,16"
            fill="none" stroke="var(--vert)" strokeWidth="2"
          />
        </svg>
        Al Karama
      </div>
      <div className="nav-links">
        <Link to="/#projets">Explorer les projets</Link>
        <Link to="/#comment">Comment ça marche</Link>
        <Link to="/#ess">L'ESS en bref</Link>
      </div>

      {user ? (
        <div className="user-menu">
          {user.role === 'porteur' && <Link to="/mes-projets">Mes projets</Link>}
          {user.role === 'investisseur' && <Link to="/mon-portefeuille">Mon portefeuille</Link>}
          {user.role === 'admin' && <Link to="/admin">Espace admin</Link>}
          <span className="user-name">{user.full_name}</span>
          <button className="btn-link-logout" onClick={logout}>Déconnexion</button>
        </div>
      ) : (
        <Link className="btn-nav" to="/connexion">Connexion</Link>
      )}
    </nav>
  );
}
