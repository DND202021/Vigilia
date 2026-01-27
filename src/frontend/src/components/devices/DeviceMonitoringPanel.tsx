/**
 * Device Monitoring Panel - Right sidebar showing device list with status.
 *
 * Displays a compact list of devices on a given floor with real-time
 * status indicators. Click a device to center the floor plan on it.
 */

import type { IoTDevice, DeviceType, DeviceStatus } from '../../types';

interface DeviceMonitoringPanelProps {
  devices: IoTDevice[];
  selectedDeviceId?: string | null;
  onDeviceClick?: (device: IoTDevice) => void;
  className?: string;
}

function getStatusDot(status: DeviceStatus): string {
  switch (status) {
    case 'online': return 'bg-green-500';
    case 'alert': return 'bg-red-500 animate-pulse';
    case 'offline': return 'bg-gray-400';
    case 'maintenance': return 'bg-yellow-500';
    case 'error': return 'bg-orange-500';
    default: return 'bg-gray-400';
  }
}

function getDeviceIcon(type: DeviceType): string {
  switch (type) {
    case 'microphone': return '🎙️';
    case 'camera': return '📷';
    case 'sensor': return '📡';
    case 'gateway': return '🔌';
    default: return '📱';
  }
}

function getStatusRowBg(status: DeviceStatus): string {
  if (status === 'alert') return 'bg-red-50 hover:bg-red-100';
  return 'hover:bg-gray-50';
}

export function DeviceMonitoringPanel({
  devices,
  selectedDeviceId,
  onDeviceClick,
  className = '',
}: DeviceMonitoringPanelProps) {
  const onlineCount = devices.filter((d) => d.status === 'online').length;
  const alertCount = devices.filter((d) => d.status === 'alert').length;
  const offlineCount = devices.filter((d) => d.status === 'offline').length;

  // Sort: alert first, then online, then the rest
  const sortedDevices = [...devices].sort((a, b) => {
    const order: Record<string, number> = { alert: 0, online: 1, error: 2, maintenance: 3, offline: 4 };
    return (order[a.status] ?? 5) - (order[b.status] ?? 5);
  });

  return (
    <div className={`bg-white border rounded-lg ${className}`}>
      <div className="p-3 border-b">
        <h3 className="text-sm font-semibold text-gray-800">Device Monitoring</h3>
        <div className="flex gap-3 mt-2 text-xs">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            {onlineCount} online
          </span>
          {alertCount > 0 && (
            <span className="flex items-center gap-1 text-red-600 font-medium">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              {alertCount} alert
            </span>
          )}
          <span className="flex items-center gap-1 text-gray-400">
            <span className="w-2 h-2 rounded-full bg-gray-400" />
            {offlineCount} offline
          </span>
        </div>
      </div>

      <div className="max-h-96 overflow-y-auto divide-y divide-gray-100">
        {sortedDevices.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-400">No devices on this floor</div>
        ) : (
          sortedDevices.map((device) => (
            <button
              key={device.id}
              onClick={() => onDeviceClick?.(device)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors ${getStatusRowBg(device.status)} ${
                selectedDeviceId === device.id ? 'ring-2 ring-inset ring-blue-400' : ''
              }`}
            >
              <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${getStatusDot(device.status)}`} />
              <span className="text-lg flex-shrink-0">{getDeviceIcon(device.device_type)}</span>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-800 truncate">{device.name}</div>
                <div className="text-xs text-gray-500 capitalize">
                  {device.device_type}
                  {device.location_name && ` \u2022 ${device.location_name}`}
                </div>
              </div>
              {device.connection_quality != null && (
                <div className="text-xs text-gray-400 flex-shrink-0">
                  {device.connection_quality}%
                </div>
              )}
            </button>
          ))
        )}
      </div>
    </div>
  );
}
