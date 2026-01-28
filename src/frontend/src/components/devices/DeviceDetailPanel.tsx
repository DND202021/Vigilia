/**
 * Device Detail Panel - Full device information display.
 *
 * Shows complete device details including identity, status, location,
 * capabilities, and configuration. Provides action buttons for edit,
 * configure, and delete operations.
 */

import type { IoTDevice, DeviceType, DeviceStatus } from '../../types';

interface DeviceDetailPanelProps {
  device: IoTDevice;
  onEdit?: () => void;
  onConfigure?: () => void;
  onDelete?: () => void;
  onClose?: () => void;
  className?: string;
}

// Helper functions for device type icons
function getDeviceIcon(type: DeviceType): string {
  switch (type) {
    case 'microphone': return '🎙️';
    case 'camera': return '📷';
    case 'sensor': return '📡';
    case 'gateway': return '🔌';
    default: return '📱';
  }
}

// Helper functions for status display
function getStatusColor(status: DeviceStatus): string {
  switch (status) {
    case 'online': return 'bg-green-100 text-green-800';
    case 'alert': return 'bg-red-100 text-red-800';
    case 'offline': return 'bg-gray-100 text-gray-800';
    case 'maintenance': return 'bg-yellow-100 text-yellow-800';
    case 'error': return 'bg-orange-100 text-orange-800';
    default: return 'bg-gray-100 text-gray-800';
  }
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

function getStatusIcon(status: DeviceStatus): string {
  switch (status) {
    case 'online': return '✓';
    case 'alert': return '⚠';
    case 'offline': return '○';
    case 'maintenance': return '🔧';
    case 'error': return '✕';
    default: return '?';
  }
}

// Format relative time
function formatRelativeTime(dateString?: string): string {
  if (!dateString) return 'Never';

  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) return 'Just now';
  if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;

  return date.toLocaleDateString();
}

// Section component for consistent styling
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="py-4 border-b border-gray-200 last:border-b-0">
      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
        {title}
      </h4>
      {children}
    </div>
  );
}

// Info row component
function InfoRow({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className="flex justify-between py-1.5">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm text-gray-900 font-medium">{value}</span>
    </div>
  );
}

export function DeviceDetailPanel({
  device,
  onEdit,
  onConfigure,
  onDelete,
  onClose,
  className = '',
}: DeviceDetailPanelProps) {
  const connectionQuality = device.connection_quality ?? 0;

  // Get key config values based on device type
  const getConfigSummary = () => {
    const config = device.config || {};
    const entries: { label: string; value: string }[] = [];

    // Common config keys by device type
    if (device.device_type === 'camera') {
      if (config.resolution) entries.push({ label: 'Resolution', value: String(config.resolution) });
      if (config.fps) entries.push({ label: 'FPS', value: String(config.fps) });
      if (config.recording_mode) entries.push({ label: 'Recording', value: String(config.recording_mode) });
    } else if (device.device_type === 'microphone') {
      if (config.sample_rate) entries.push({ label: 'Sample Rate', value: `${config.sample_rate} Hz` });
      if (config.sensitivity) entries.push({ label: 'Sensitivity', value: String(config.sensitivity) });
      if (config.threshold_db) entries.push({ label: 'Threshold', value: `${config.threshold_db} dB` });
    } else if (device.device_type === 'sensor') {
      if (config.sensor_type) entries.push({ label: 'Sensor Type', value: String(config.sensor_type) });
      if (config.interval) entries.push({ label: 'Interval', value: `${config.interval}s` });
      if (config.threshold) entries.push({ label: 'Threshold', value: String(config.threshold) });
    } else if (device.device_type === 'gateway') {
      if (config.protocol) entries.push({ label: 'Protocol', value: String(config.protocol) });
      if (config.connected_devices) entries.push({ label: 'Connected', value: `${config.connected_devices} devices` });
    }

    // Fallback: show first few config entries
    if (entries.length === 0) {
      Object.entries(config).slice(0, 3).forEach(([key, val]) => {
        entries.push({ label: key.replace(/_/g, ' '), value: String(val) });
      });
    }

    return entries;
  };

  const configSummary = getConfigSummary();

  return (
    <div className={`bg-white border rounded-lg shadow-lg ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{getDeviceIcon(device.device_type)}</span>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{device.name}</h3>
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(device.status)}`}>
              <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${getStatusDot(device.status)}`} />
              {device.status.charAt(0).toUpperCase() + device.status.slice(1)}
            </span>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
            aria-label="Close panel"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Content */}
      <div className="px-4 max-h-[calc(100vh-200px)] overflow-y-auto">
        {/* Identity Section */}
        <Section title="Identity">
          <div className="space-y-0.5">
            <InfoRow label="Serial Number" value={device.serial_number} />
            <InfoRow label="IP Address" value={device.ip_address} />
            <InfoRow label="MAC Address" value={device.mac_address} />
            <InfoRow label="Model" value={device.model} />
            <InfoRow label="Firmware" value={device.firmware_version} />
            <InfoRow label="Manufacturer" value={device.manufacturer} />
          </div>
        </Section>

        {/* Status Section */}
        <Section title="Status">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className={`w-6 h-6 flex items-center justify-center rounded-full text-sm ${getStatusColor(device.status)}`}>
                {getStatusIcon(device.status)}
              </span>
              <span className="text-sm text-gray-900 font-medium capitalize">{device.status}</span>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500">Last Seen</span>
              <span className="text-sm text-gray-900">{formatRelativeTime(device.last_seen)}</span>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm text-gray-500">Connection Quality</span>
                <span className="text-sm text-gray-900">{connectionQuality}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    connectionQuality >= 70 ? 'bg-green-500' :
                    connectionQuality >= 40 ? 'bg-yellow-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${connectionQuality}%` }}
                />
              </div>
            </div>
          </div>
        </Section>

        {/* Location Section */}
        <Section title="Location">
          <div className="space-y-0.5">
            {device.building_id && (
              <InfoRow label="Building" value={device.building_id} />
            )}
            {device.floor_plan_id && (
              <InfoRow label="Floor Plan" value={device.floor_plan_id} />
            )}
            <InfoRow label="Location" value={device.location_name} />
            {(device.position_x != null && device.position_y != null) && (
              <InfoRow
                label="Position"
                value={`X: ${device.position_x.toFixed(1)}, Y: ${device.position_y.toFixed(1)}`}
              />
            )}
            {(device.latitude != null && device.longitude != null) && (
              <InfoRow
                label="Coordinates"
                value={`${device.latitude.toFixed(6)}, ${device.longitude.toFixed(6)}`}
              />
            )}
          </div>
          {!device.building_id && !device.floor_plan_id && !device.location_name && (
            <p className="text-sm text-gray-400 italic">No location assigned</p>
          )}
        </Section>

        {/* Capabilities Section */}
        {device.capabilities && device.capabilities.length > 0 && (
          <Section title="Capabilities">
            <div className="flex flex-wrap gap-2">
              {device.capabilities.map((capability, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                >
                  {capability}
                </span>
              ))}
            </div>
          </Section>
        )}

        {/* Configuration Summary Section */}
        {(configSummary.length > 0 || onConfigure) && (
          <Section title="Configuration">
            {configSummary.length > 0 ? (
              <div className="space-y-0.5 mb-3">
                {configSummary.map((item, index) => (
                  <InfoRow key={index} label={item.label} value={item.value} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400 italic mb-3">No configuration set</p>
            )}
            {onConfigure && (
              <button
                onClick={onConfigure}
                className="w-full px-3 py-2 text-sm font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 rounded transition-colors"
              >
                <span className="flex items-center justify-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  Configure Device
                </span>
              </button>
            )}
          </Section>
        )}
      </div>

      {/* Action Buttons */}
      {(onEdit || onDelete) && (
        <div className="p-4 border-t border-gray-200 flex gap-2">
          {onEdit && (
            <button
              onClick={onEdit}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
              Edit
            </button>
          )}
          {onConfigure && (
            <button
              onClick={onConfigure}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Configure
            </button>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-red-700 bg-red-50 hover:bg-red-100 rounded transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Delete
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default DeviceDetailPanel;
