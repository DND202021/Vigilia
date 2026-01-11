import { Routes, Route } from 'react-router-dom';

function App() {
  return (
    <div className="min-h-screen bg-gray-100">
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/incidents/:id" element={<IncidentDetailPage />} />
        <Route path="/resources" element={<ResourcesPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/login" element={<LoginPage />} />
      </Routes>
    </div>
  );
}

// Placeholder components - to be implemented
function Dashboard() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900">ERIOP Dashboard</h1>
      <p className="mt-4 text-gray-600">Emergency Response IoT Platform</p>
      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold">Active Incidents</h2>
          <p className="text-4xl font-bold text-red-600 mt-2">--</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold">Available Units</h2>
          <p className="text-4xl font-bold text-green-600 mt-2">--</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold">Pending Alerts</h2>
          <p className="text-4xl font-bold text-yellow-600 mt-2">--</p>
        </div>
      </div>
    </div>
  );
}

function IncidentsPage() {
  return <div className="p-8"><h1 className="text-2xl font-bold">Incidents</h1></div>;
}

function IncidentDetailPage() {
  return <div className="p-8"><h1 className="text-2xl font-bold">Incident Details</h1></div>;
}

function ResourcesPage() {
  return <div className="p-8"><h1 className="text-2xl font-bold">Resources</h1></div>;
}

function AlertsPage() {
  return <div className="p-8"><h1 className="text-2xl font-bold">Alerts</h1></div>;
}

function MapPage() {
  return <div className="p-8"><h1 className="text-2xl font-bold">Tactical Map</h1></div>;
}

function LoginPage() {
  return <div className="p-8"><h1 className="text-2xl font-bold">Login</h1></div>;
}

export default App;
