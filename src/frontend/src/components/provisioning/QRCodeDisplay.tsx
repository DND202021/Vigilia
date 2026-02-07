/**
 * QR Code Display Component
 *
 * Renders a QR code for mobile provisioning of devices with access tokens.
 */

import QRCode from 'react-qr-code';

interface QRCodeDisplayProps {
  deviceId: string;
  accessToken: string;
}

export function QRCodeDisplay({ deviceId, accessToken }: QRCodeDisplayProps) {
  const qrData = JSON.stringify({
    device_id: deviceId,
    access_token: accessToken,
    type: 'mqtt_access_token',
  });

  return (
    <div className="flex flex-col items-center p-4 border-2 border-gray-200 rounded-lg bg-white">
      <QRCode value={qrData} size={200} />
      <p className="text-sm text-gray-600 mt-3">Scan with device to configure</p>
    </div>
  );
}
