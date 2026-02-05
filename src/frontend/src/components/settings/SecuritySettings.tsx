/**
 * Security Settings Component
 * MFA enable/disable with status display
 */

import { useState } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { MFASetupModal, MFADisableModal } from '../auth';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge } from '../ui';

export function SecuritySettings() {
  const { user, refreshUser } = useAuthStore();
  const [showSetupModal, setShowSetupModal] = useState(false);
  const [showDisableModal, setShowDisableModal] = useState(false);

  const mfaEnabled = user?.mfa_enabled ?? false;

  const handleMfaSuccess = async () => {
    // Refresh user data to update MFA status
    await refreshUser();
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Two-Factor Authentication</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-700 font-medium">Authenticator App</p>
              <p className="text-sm text-gray-500 mt-1">
                Use an authenticator app to generate one-time codes
              </p>
            </div>
            <div className="flex items-center gap-4">
              <Badge variant={mfaEnabled ? 'success' : 'secondary'}>
                {mfaEnabled ? 'Enabled' : 'Disabled'}
              </Badge>
              {mfaEnabled ? (
                <Button
                  variant="secondary"
                  onClick={() => setShowDisableModal(true)}
                  className="text-red-600 hover:text-red-700"
                >
                  Disable
                </Button>
              ) : (
                <Button onClick={() => setShowSetupModal(true)}>
                  Enable
                </Button>
              )}
            </div>
          </div>

          {!mfaEnabled && (
            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-sm text-yellow-800">
                <strong>Recommended:</strong> Enable two-factor authentication for an extra layer of security.
                You'll need an authenticator app like Google Authenticator or Authy.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Password</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-700 font-medium">Change Password</p>
              <p className="text-sm text-gray-500 mt-1">
                Update your password regularly to keep your account secure
              </p>
            </div>
            <Button variant="secondary" disabled>
              Change Password
            </Button>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Contact your administrator to reset your password
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Sessions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-700 font-medium">Active Sessions</p>
              <p className="text-sm text-gray-500 mt-1">
                Manage devices where you're currently logged in
              </p>
            </div>
            <Button variant="secondary" disabled>
              View Sessions
            </Button>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Session management coming soon
          </p>
        </CardContent>
      </Card>

      {/* MFA Modals */}
      <MFASetupModal
        isOpen={showSetupModal}
        onClose={() => setShowSetupModal(false)}
        onSuccess={handleMfaSuccess}
      />
      <MFADisableModal
        isOpen={showDisableModal}
        onClose={() => setShowDisableModal(false)}
        onSuccess={handleMfaSuccess}
      />
    </div>
  );
}
