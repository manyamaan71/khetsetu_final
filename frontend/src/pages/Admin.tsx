import { useEffect, useState } from 'react';
import Card from '../components/Card';

interface AdminStats {
  total_scans: number;
  healthy_count: number;
  disease_count: number;
  low_confidence_count: number;
  disease_distribution: Record<string, number>;
  crop_distribution: Record<string, number>;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export default function Admin() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/admin/stats`)
      .then((r) => {
        if (!r.ok) throw new Error('failed');
        return r.json();
      })
      .then(setStats)
      .catch(() => setError(true));
  }, []);

  return (
    <div className="space-y-4 pt-2">
      <h1 className="text-2xl font-extrabold text-gray-800">Admin — Aggregate Insights</h1>
      <p className="text-sm text-gray-500">
        For extension workers. Shows aggregate scan statistics only — no individual farmer data.
      </p>

      {error && (
        <Card className="text-center py-8 text-gray-500">Admin data is unavailable right now.</Card>
      )}

      {stats && (
        <>
          <div className="grid grid-cols-2 gap-3">
            <Card>
              <p className="text-xs text-gray-500">Total Scans</p>
              <p className="text-2xl font-extrabold text-gray-800">{stats.total_scans}</p>
            </Card>
            <Card>
              <p className="text-xs text-gray-500">Healthy Leaves</p>
              <p className="text-2xl font-extrabold text-leaf-600">{stats.healthy_count}</p>
            </Card>
            <Card>
              <p className="text-xs text-gray-500">Disease Detections</p>
              <p className="text-2xl font-extrabold text-amber-600">{stats.disease_count}</p>
            </Card>
            <Card>
              <p className="text-xs text-gray-500">Low-Confidence Scans</p>
              <p className="text-2xl font-extrabold text-red-500">{stats.low_confidence_count}</p>
            </Card>
          </div>

          <Card>
            <p className="font-semibold text-gray-700 mb-3">Disease Distribution</p>
            <div className="space-y-2">
              {Object.entries(stats.disease_distribution).map(([name, count]) => (
                <div key={name}>
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>{name}</span>
                    <span>{count}</span>
                  </div>
                  <div className="h-2 bg-leaf-50 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-leaf-600 rounded-full"
                      style={{ width: `${(count / Math.max(1, stats.total_scans)) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <p className="font-semibold text-gray-700 mb-3">Crop Distribution</p>
            <div className="space-y-2">
              {Object.entries(stats.crop_distribution).map(([name, count]) => (
                <div key={name}>
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>{name}</span>
                    <span>{count}</span>
                  </div>
                  <div className="h-2 bg-wheat-400/20 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-wheat-500 rounded-full"
                      style={{ width: `${(count / Math.max(1, stats.total_scans)) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
