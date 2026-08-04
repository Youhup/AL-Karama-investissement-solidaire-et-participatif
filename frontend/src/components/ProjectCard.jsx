import { Link } from 'react-router-dom';
import ZelligeProgressRing from './ZelligeProgressRing';
import { deadlineBadge } from '../utils/funding';

export default function ProjectCard({
  id, tag, title, location, percent, amount, repayment, photoUrl, status, fundingDeadline,
}) {
  const badge = deadlineBadge(status, fundingDeadline);

  const content = (
    <>
      {badge && (
        <div className={`deadline-tag deadline-tag--corner ${badge.state}`}>
          <span className="num">{badge.num}</span>
          <span className="unit">{badge.unit}</span>
        </div>
      )}
      {photoUrl && (
        <div className="card-image">
          <img src={photoUrl} alt={title} loading="lazy" />
        </div>
      )}
      <span className="card-tag">{tag}</span>
      <h3>{title}</h3>
      <p className="card-loc">{location}</p>
      <div className="card-bottom">
        <ZelligeProgressRing percent={percent} />
        <div className="card-stats">
          <div>
            <span className="amount">{amount.toLocaleString('fr-FR')}</span> MAD collectés
          </div>
          <div className="card-repay">Remboursement : {repayment}</div>
        </div>
      </div>
    </>
  );

  if (id) {
    return (
      <Link to={`/projets/${id}`} className="card card-link">
        {content}
      </Link>
    );
  }

  return <div className="card">{content}</div>;
}
