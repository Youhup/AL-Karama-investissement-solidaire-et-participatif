import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * Protège une route. Usage :
 *   <RequireAuth><MesProjets /></RequireAuth>
 *   <RequireAuth roles={['porteur']}><DeposerProjet /></RequireAuth>
 */
export default function RequireAuth({ children, roles }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return null; // ou un spinner si besoin

  if (!user) {
    return <Navigate to="/connexion" state={{ from: location }} replace />;
  }

  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return children;
}
