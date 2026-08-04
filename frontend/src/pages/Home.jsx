import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import ZelligeRosette from '../components/ZelligeRosette';
import ProjectCard from '../components/ProjectCard';
import { listProjects, listSectors } from '../api/projects';
import { API_URL } from '../api/client';

const STEPS = [
  {
    title: 'Déposez votre dossier',
    description:
      "Agriculteurs, éleveurs, artisans et commerçants présentent leur projet et un plan de remboursement en nature réaliste.",
  },
  {
    title: 'La communauté finance',
    description:
      'Des investisseurs solidaires soutiennent le projet par petites participations, à plusieurs.',
  },
  {
    title: 'Vous êtes remboursés en nature',
    description:
      "Huile d'argan, safran, poteries, tapis... livrés directement selon l'échéancier convenu.",
  },
];

export default function Home() {
  const location = useLocation();
  const [featuredProjects, setFeaturedProjects] = useState([]);
  const [sectorsById, setSectorsById] = useState({});

  // React Router ne scrolle pas automatiquement vers un fragment #hash
  // (ni au clic sur un <Link to="/#projets"> depuis une autre page, ni
  // depuis la page d'accueil elle-même) : on le fait à la main.
  useEffect(() => {
    if (!location.hash) return;
    const el = document.querySelector(location.hash);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  }, [location]);

  useEffect(() => {
    Promise.all([listProjects(), listSectors()])
      .then(([projectsData, sectorsData]) => {
        setFeaturedProjects(projectsData.slice(0, 3));
        setSectorsById(Object.fromEntries(sectorsData.map((s) => [s.id, s.name])));
      })
      .catch(() => {});
  }, []);

  return (
    <>
      <Navbar />

      <header className="wrap hero">
        <div>
          <span className="eyebrow">Investissement solidaire et participatif</span>
          <h1>Investir dans la terre, le savoir-faire et la parole donnée.</h1>
          <p className="lead">
            Financez le projet d'un agriculteur, d'un éleveur ou d'un artisan marocain, et soyez
            remboursé en nature : huile, safran, laine, poterie — le fruit direct de ce que vous
            avez aidé à faire naître.
          </p>
          <div className="hero-ctas">
            <Link className="btn-primary" to="/deposer">Déposer un projet</Link>
            <a className="btn-secondary" href="#projets">Découvrir les projets</a>
          </div>
        </div>
        <div className="hero-visual">
          <ZelligeRosette />
        </div>
      </header>

      <section className="steps-band" id="comment">
        <div className="wrap">
          <h2>Trois étapes, une confiance partagée</h2>
          <div className="steps">
            {STEPS.map((step, i) => (
              <div className="step" key={step.title}>
                <div className="step-num">{String(i + 1).padStart(2, '0')}</div>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section wrap" id="projets">
        <div className="section-head">
          <div>
            <h2>Projets à la une</h2>
            <p>Une sélection de dossiers validés, ouverts au financement.</p>
          </div>
          <Link to="/projets">Voir tous les projets →</Link>
        </div>
        <div className="cards">
          {featuredProjects.map((p) => (
            <ProjectCard
              key={p.id}
              id={p.id}
              tag={`${sectorsById[p.sector_id] || 'Projet'}${p.city ? ` · ${p.city}` : ''}`}
              title={p.title}
              location={p.description.length > 90 ? `${p.description.slice(0, 90)}…` : p.description}
              percent={p.amount_requested > 0 ? (p.amount_raised / p.amount_requested) * 100 : 0}
              amount={p.amount_raised}
              repayment="voir le détail du projet"
              photoUrl={p.photo_url ? `${API_URL}${p.photo_url}` : null}
              status={p.status}
              fundingDeadline={p.funding_deadline}
            />
          ))}
        </div>
      </section>

      <section className="ess" id="ess">
        <div className="wrap ess-inner">
          <h2>Qu'est-ce que l'économie sociale et solidaire ?</h2>
          <p>
            L'ESS place l'utilité collective avant le seul profit financier. Ici, investir ne
            rapporte pas des intérêts, mais le fruit concret du travail d'un producteur local —
            un modèle plus proche du troc solidaire que du placement financier classique.
          </p>
          <p className="field-hint" style={{ marginTop: -8 }}>
            Une question ? L'assistant en bas à droite peut vous expliquer le fonctionnement de
            la plateforme, à tout moment.
          </p>
        </div>
      </section>

      <Footer />
    </>
  );
}
