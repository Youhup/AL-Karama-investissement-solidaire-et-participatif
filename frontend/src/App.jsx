import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import RequireAuth from './components/RequireAuth';
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import DeposerProjet from './pages/DeposerProjet';
import ProjectManage from './pages/ProjectManage';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import MyProjects from './pages/MyProjects';
import MyPortfolio from './pages/MyPortfolio';
import AdminDashboard from './pages/AdminDashboard';
import AdminProjectReview from './pages/AdminProjectReview';
import EnConstruction from './pages/EnConstruction';
import ChatWidget from './components/ChatWidget';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/connexion" element={<Login />} />
          <Route path="/inscription" element={<Register />} />
          <Route path="/projets" element={<Projects />} />
          <Route path="/projets/:id" element={<ProjectDetail />} />
          <Route
            path="/deposer"
            element={<RequireAuth roles={['porteur']}><DeposerProjet /></RequireAuth>}
          />
          <Route
            path="/mes-projets"
            element={<RequireAuth roles={['porteur']}><MyProjects /></RequireAuth>}
          />
          <Route
            path="/mes-projets/:id"
            element={<RequireAuth roles={['porteur']}><ProjectManage /></RequireAuth>}
          />
          <Route
            path="/mon-portefeuille"
            element={<RequireAuth roles={['investisseur']}><MyPortfolio /></RequireAuth>}
          />
          <Route
            path="/admin"
            element={<RequireAuth roles={['admin']}><AdminDashboard /></RequireAuth>}
          />
          <Route
            path="/admin/projects/:id"
            element={<RequireAuth roles={['admin']}><AdminProjectReview /></RequireAuth>}
          />
          <Route path="*" element={<EnConstruction />} />
        </Routes>
        <ChatWidget />
      </AuthProvider>
    </BrowserRouter>
  );
}
