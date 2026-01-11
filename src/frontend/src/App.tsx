/**
 * ERIOP Main Application
 */

import { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import { useWebSocket } from './hooks/useWebSocket';
import { Layout, ProtectedRoute } from './components/layout';
import {
  DashboardPage,
  IncidentsPage,
  IncidentDetailPage,
  AlertsPage,
  ResourcesPage,
  MapPage,
  LoginPage,
} from './pages';
import { Spinner } from './components/ui';

function App() {
  const { checkAuth, isLoading, isAuthenticated } = useAuthStore();
  const { connect, disconnect } = useWebSocket();

  // Check authentication on mount
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // Connect WebSocket when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      connect();
    } else {
      disconnect();
    }
  }, [isAuthenticated, connect, disconnect]);

  // Show loading while checking auth
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <Spinner size="lg" />
          <p className="mt-4 text-gray-600">Loading ERIOP...</p>
        </div>
      </div>
    );
  }

  return (
    <Layout>
      <Routes>
        {/* Public routes */}
        <Route
          path="/login"
          element={
            isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />
          }
        />

        {/* Protected routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/incidents"
          element={
            <ProtectedRoute>
              <IncidentsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/incidents/:id"
          element={
            <ProtectedRoute>
              <IncidentDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/alerts"
          element={
            <ProtectedRoute>
              <AlertsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/resources"
          element={
            <ProtectedRoute>
              <ResourcesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/map"
          element={
            <ProtectedRoute>
              <MapPage />
            </ProtectedRoute>
          }
        />

        {/* Catch all - redirect to dashboard or login */}
        <Route
          path="*"
          element={<Navigate to={isAuthenticated ? '/' : '/login'} replace />}
        />
      </Routes>
    </Layout>
  );
}

export default App;
