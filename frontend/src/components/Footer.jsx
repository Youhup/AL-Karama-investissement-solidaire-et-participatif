import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="wrap">
        <span className="brand-small">Al Karama</span>
        <div className="foot-links">
          <Link to="/mentions-legales">Mentions légales</Link>
          <Link to="/#comment">Comment ça marche</Link>
          <Link to="/contact">Contact</Link>
        </div>
      </div>
    </footer>
  );
}
