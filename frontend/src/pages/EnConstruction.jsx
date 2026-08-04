import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

export default function EnConstruction() {
  return (
    <>
      <Navbar />
      <div className="auth-page">
        <div className="auth-card" style={{ textAlign: 'center' }}>
          <h1>Bientôt disponible</h1>
          <p className="auth-subtitle">Cette page fait partie d'un prochain module.</p>
          <Link className="btn-primary" to="/">Retour à l'accueil</Link>
        </div>
      </div>
      <Footer />
    </>
  );
}
