/**
 * Main Layout Component
 */

import { Navbar } from './Navbar';
import { useAuthStore } from '../../stores/authStore';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { isAuthenticated } = useAuthStore();

  return (
    <div className="min-h-screen bg-gray-100">
      {isAuthenticated && <Navbar />}
      <main className="flex-1">{children}</main>
    </div>
  );
}
