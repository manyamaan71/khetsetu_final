import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function AdminRoute({ children }: { children: JSX.Element }) {
  const { loading, user } = useAuth();
  if (loading) {
    return <div className="flex min-h-[50vh] items-center justify-center text-sm font-semibold text-gray-500">Loading KhetSetu...</div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  if (user.app_metadata?.role !== 'admin') return <Navigate to="/home" replace />;
  return children;
}
