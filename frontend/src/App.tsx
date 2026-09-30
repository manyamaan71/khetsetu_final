import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Scan from './pages/Scan';
import Result from './pages/Result';
import HistoryPage from './pages/History';
import Market from './pages/Market';
import Advisory from './pages/Advisory';
import Settings from './pages/Settings';
import Admin from './pages/Admin';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/scan" element={<Scan />} />
        <Route path="/result" element={<Result />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/market" element={<Market />} />
        <Route path="/advisory" element={<Advisory />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/admin" element={<Admin />} />
      </Routes>
    </Layout>
  );
}
