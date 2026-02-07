/**
 * Credential Download Card Component
 *
 * Handles downloading credentials for both access token and x509 certificate types.
 * Uses Blob API for secure one-time downloads with immediate URL revocation.
 */

import { QRCodeDisplay } from './QRCodeDisplay';
import type { ProvisioningCredentials } from '../../stores/provisioningStore';

interface CredentialDownloadCardProps {
  credentials: ProvisioningCredentials;
  onDownloaded: () => void;
}

export function CredentialDownloadCard({ credentials, onDownloaded }: CredentialDownloadCardProps) {
  const handleDownloadAccessToken = () => {
    if (!credentials.accessToken || !credentials.deviceId) return;

    const blob = new Blob([credentials.accessToken], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `device_${credentials.deviceId}_access_token.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url); // Immediate cleanup

    onDownloaded();
  };

  const handleDownloadCertificate = () => {
    if (!credentials.certificatePem || !credentials.privateKeyPem || !credentials.deviceId) return;

    // Download certificate
    const certBlob = new Blob([atob(credentials.certificatePem)], { type: 'application/x-pem-file' });
    const certUrl = URL.createObjectURL(certBlob);
    const certLink = document.createElement('a');
    certLink.href = certUrl;
    certLink.download = `device_${credentials.deviceId}_certificate.pem`;
    document.body.appendChild(certLink);
    certLink.click();
    document.body.removeChild(certLink);
    URL.revokeObjectURL(certUrl);

    // Download private key
    const keyBlob = new Blob([atob(credentials.privateKeyPem)], { type: 'application/x-pem-file' });
    const keyUrl = URL.createObjectURL(keyBlob);
    const keyLink = document.createElement('a');
    keyLink.href = keyUrl;
    keyLink.download = `device_${credentials.deviceId}_private_key.pem`;
    document.body.appendChild(keyLink);
    keyLink.click();
    document.body.removeChild(keyLink);
    URL.revokeObjectURL(keyUrl);

    onDownloaded();
  };

  const isAccessToken = credentials.accessToken !== null;

  return (
    <div className="space-y-4">
      {/* Security Warning */}
      <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-4 flex items-start gap-3">
        <span className="text-yellow-600 text-xl">⚠️</span>
        <div>
          <p className="font-semibold text-yellow-800">Credentials are shown only once</p>
          <p className="text-sm text-yellow-700 mt-1">
            Download now — they cannot be retrieved later. Keep them secure.
          </p>
        </div>
      </div>

      {/* Credential Display and Download */}
      <div className="border-2 border-gray-200 rounded-lg p-6 space-y-4">
        {isAccessToken ? (
          <>
            {/* Access Token */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Access Token</label>
              <div className="bg-gray-50 p-3 rounded border font-mono text-sm break-all">
                {credentials.accessToken?.substring(0, 8)}...
                <span className="text-gray-400 ml-2">(masked for security)</span>
              </div>
            </div>

            <button
              onClick={handleDownloadAccessToken}
              className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Download Token
            </button>

            {/* QR Code */}
            {credentials.deviceId && credentials.accessToken && (
              <div className="flex justify-center pt-4 border-t">
                <QRCodeDisplay deviceId={credentials.deviceId} accessToken={credentials.accessToken} />
              </div>
            )}
          </>
        ) : (
          <>
            {/* X.509 Certificate */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">X.509 Certificate</label>
              <div className="bg-gray-50 p-3 rounded border space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">CN:</span>
                  <span className="font-mono text-gray-900">{credentials.certificateCn}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Expires:</span>
                  <span className="text-gray-900">
                    {credentials.certificateExpiry
                      ? new Date(credentials.certificateExpiry).toLocaleDateString()
                      : 'N/A'}
                  </span>
                </div>
              </div>
            </div>

            <button
              onClick={handleDownloadCertificate}
              className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Download Certificate & Key
            </button>

            <p className="text-xs text-gray-500 text-center">
              Two files will be downloaded: certificate.pem and private_key.pem
            </p>
          </>
        )}
      </div>
    </div>
  );
}
