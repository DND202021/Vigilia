/**
 * DeviceConfigEditor Component
 *
 * Configuration editor for IoT devices with type-specific settings.
 * Supports microphone, camera, sensor, and gateway device types.
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import { cn } from '../../utils';
import type { IoTDevice, DeviceType } from '../../types';

// --- Props ---

export interface DeviceConfigEditorProps {
  device: IoTDevice;
  onSave: (config: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
  className?: string;
}

// --- Config Schemas ---

interface MicrophoneConfig {
  [key: string]: unknown;
  sensitivity: number;
  frequencyRange: { min: number; max: number };
  noiseThreshold: number;
  detectionTypes: string[];
}

interface CameraConfig {
  [key: string]: unknown;
  resolution: string;
  fps: number;
  nightVision: boolean;
  motionDetection: boolean;
  motionSensitivity: number;
}

interface SensorConfig {
  [key: string]: unknown;
  type: string;
  threshold: number;
  alertDelay: number;
  cooldownPeriod: number;
}

interface GatewayConfig {
  [key: string]: unknown;
  maxDevices: number;
  heartbeatInterval: number;
  retryAttempts: number;
}

// --- Default Configs ---

const DEFAULT_MICROPHONE_CONFIG: MicrophoneConfig = {
  sensitivity: 50,
  frequencyRange: { min: 20, max: 20000 },
  noiseThreshold: 30,
  detectionTypes: ['gunshot'],
};

const DEFAULT_CAMERA_CONFIG: CameraConfig = {
  resolution: '1080p',
  fps: 30,
  nightVision: false,
  motionDetection: true,
  motionSensitivity: 50,
};

const DEFAULT_SENSOR_CONFIG: SensorConfig = {
  type: 'motion',
  threshold: 50,
  alertDelay: 5,
  cooldownPeriod: 60,
};

const DEFAULT_GATEWAY_CONFIG: GatewayConfig = {
  maxDevices: 32,
  heartbeatInterval: 30,
  retryAttempts: 3,
};

// --- Options ---

const DETECTION_TYPES = [
  { value: 'gunshot', label: 'Gunshot' },
  { value: 'glass_break', label: 'Glass Break' },
  { value: 'scream', label: 'Scream' },
  { value: 'explosion', label: 'Explosion' },
];

const RESOLUTION_OPTIONS = ['720p', '1080p', '4K'];
const FPS_OPTIONS = [15, 30, 60];
const SENSOR_TYPES = [
  { value: 'motion', label: 'Motion' },
  { value: 'temperature', label: 'Temperature' },
  { value: 'humidity', label: 'Humidity' },
  { value: 'smoke', label: 'Smoke' },
  { value: 'door', label: 'Door/Window' },
];

// --- Helper Functions ---

function getDeviceIcon(type: DeviceType): string {
  switch (type) {
    case 'microphone':
      return 'M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z';
    case 'camera':
      return 'M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z';
    case 'sensor':
      return 'M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z';
    case 'gateway':
      return 'M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01';
    default:
      return 'M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z';
  }
}

function getDefaultConfig(type: DeviceType): Record<string, unknown> {
  switch (type) {
    case 'microphone':
      return DEFAULT_MICROPHONE_CONFIG;
    case 'camera':
      return DEFAULT_CAMERA_CONFIG;
    case 'sensor':
      return DEFAULT_SENSOR_CONFIG;
    case 'gateway':
      return DEFAULT_GATEWAY_CONFIG;
    default:
      return {};
  }
}

// --- Slider Component ---

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  onChange: (value: number) => void;
}

function Slider({ label, value, min, max, step = 1, unit = '', onChange }: SliderProps) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <label className="text-sm font-medium text-gray-700">{label}</label>
        <span className="text-sm text-gray-500">
          {value}
          {unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
      />
      <div className="flex justify-between text-xs text-gray-400">
        <span>
          {min}
          {unit}
        </span>
        <span>
          {max}
          {unit}
        </span>
      </div>
    </div>
  );
}

// --- Checkbox Component ---

interface CheckboxProps {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

function Checkbox({ label, description, checked, onChange }: CheckboxProps) {
  return (
    <label className="flex items-start gap-3 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
      />
      <div>
        <span className="text-sm font-medium text-gray-700">{label}</span>
        {description && <p className="text-xs text-gray-500">{description}</p>}
      </div>
    </label>
  );
}

// --- Multi-Select Component ---

interface MultiSelectProps {
  label: string;
  options: { value: string; label: string }[];
  selected: string[];
  onChange: (selected: string[]) => void;
}

function MultiSelect({ label, options, selected, onChange }: MultiSelectProps) {
  const toggleOption = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-gray-700">{label}</label>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => {
          const isSelected = selected.includes(option.value);
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => toggleOption(option.value)}
              className={cn(
                'px-3 py-1.5 text-sm rounded-full border transition-colors',
                isSelected
                  ? 'bg-blue-100 border-blue-300 text-blue-700'
                  : 'bg-white border-gray-300 text-gray-600 hover:border-gray-400'
              )}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// --- Config Editors per Device Type ---

interface MicrophoneEditorProps {
  config: MicrophoneConfig;
  onChange: (config: MicrophoneConfig) => void;
}

function MicrophoneEditor({ config, onChange }: MicrophoneEditorProps) {
  return (
    <div className="space-y-6">
      <Slider
        label="Sensitivity"
        value={config.sensitivity}
        min={0}
        max={100}
        unit="%"
        onChange={(value) => onChange({ ...config, sensitivity: value })}
      />

      <div className="space-y-3">
        <label className="text-sm font-medium text-gray-700">Frequency Range</label>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-500">Min (Hz)</label>
            <input
              type="number"
              min={20}
              max={config.frequencyRange.max}
              value={config.frequencyRange.min}
              onChange={(e) =>
                onChange({
                  ...config,
                  frequencyRange: { ...config.frequencyRange, min: Number(e.target.value) },
                })
              }
              className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500">Max (Hz)</label>
            <input
              type="number"
              min={config.frequencyRange.min}
              max={20000}
              value={config.frequencyRange.max}
              onChange={(e) =>
                onChange({
                  ...config,
                  frequencyRange: { ...config.frequencyRange, max: Number(e.target.value) },
                })
              }
              className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
      </div>

      <Slider
        label="Noise Threshold"
        value={config.noiseThreshold}
        min={0}
        max={100}
        unit="%"
        onChange={(value) => onChange({ ...config, noiseThreshold: value })}
      />

      <MultiSelect
        label="Detection Types"
        options={DETECTION_TYPES}
        selected={config.detectionTypes}
        onChange={(detectionTypes) => onChange({ ...config, detectionTypes })}
      />
    </div>
  );
}

interface CameraEditorProps {
  config: CameraConfig;
  onChange: (config: CameraConfig) => void;
}

function CameraEditor({ config, onChange }: CameraEditorProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">Resolution</label>
        <div className="flex gap-2">
          {RESOLUTION_OPTIONS.map((res) => (
            <button
              key={res}
              type="button"
              onClick={() => onChange({ ...config, resolution: res })}
              className={cn(
                'px-4 py-2 text-sm rounded-lg border transition-colors',
                config.resolution === res
                  ? 'bg-blue-100 border-blue-300 text-blue-700'
                  : 'bg-white border-gray-300 text-gray-600 hover:border-gray-400'
              )}
            >
              {res}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">Frame Rate (FPS)</label>
        <div className="flex gap-2">
          {FPS_OPTIONS.map((fps) => (
            <button
              key={fps}
              type="button"
              onClick={() => onChange({ ...config, fps })}
              className={cn(
                'px-4 py-2 text-sm rounded-lg border transition-colors',
                config.fps === fps
                  ? 'bg-blue-100 border-blue-300 text-blue-700'
                  : 'bg-white border-gray-300 text-gray-600 hover:border-gray-400'
              )}
            >
              {fps}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        <Checkbox
          label="Night Vision"
          description="Enable infrared mode in low-light conditions"
          checked={config.nightVision}
          onChange={(nightVision) => onChange({ ...config, nightVision })}
        />

        <Checkbox
          label="Motion Detection"
          description="Trigger alerts when motion is detected"
          checked={config.motionDetection}
          onChange={(motionDetection) => onChange({ ...config, motionDetection })}
        />
      </div>

      {config.motionDetection && (
        <Slider
          label="Motion Sensitivity"
          value={config.motionSensitivity}
          min={0}
          max={100}
          unit="%"
          onChange={(value) => onChange({ ...config, motionSensitivity: value })}
        />
      )}
    </div>
  );
}

interface SensorEditorProps {
  config: SensorConfig;
  onChange: (config: SensorConfig) => void;
}

function SensorEditor({ config, onChange }: SensorEditorProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">Sensor Type</label>
        <select
          value={config.type}
          onChange={(e) => onChange({ ...config, type: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          {SENSOR_TYPES.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </select>
      </div>

      <Slider
        label="Threshold"
        value={config.threshold}
        min={0}
        max={100}
        unit="%"
        onChange={(value) => onChange({ ...config, threshold: value })}
      />

      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">Alert Delay</label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            max={300}
            value={config.alertDelay}
            onChange={(e) => onChange({ ...config, alertDelay: Number(e.target.value) })}
            className="w-24 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <span className="text-sm text-gray-500">seconds</span>
        </div>
        <p className="text-xs text-gray-400">
          Time to wait before triggering an alert after detection
        </p>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">Cooldown Period</label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            max={3600}
            value={config.cooldownPeriod}
            onChange={(e) => onChange({ ...config, cooldownPeriod: Number(e.target.value) })}
            className="w-24 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <span className="text-sm text-gray-500">seconds</span>
        </div>
        <p className="text-xs text-gray-400">
          Minimum time between consecutive alerts
        </p>
      </div>
    </div>
  );
}

interface GatewayEditorProps {
  config: GatewayConfig;
  onChange: (config: GatewayConfig) => void;
}

function GatewayEditor({ config, onChange }: GatewayEditorProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">Max Connected Devices</label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={1}
            max={256}
            value={config.maxDevices}
            onChange={(e) => onChange({ ...config, maxDevices: Number(e.target.value) })}
            className="w-24 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <span className="text-sm text-gray-500">devices</span>
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">Heartbeat Interval</label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={5}
            max={300}
            value={config.heartbeatInterval}
            onChange={(e) => onChange({ ...config, heartbeatInterval: Number(e.target.value) })}
            className="w-24 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <span className="text-sm text-gray-500">seconds</span>
        </div>
        <p className="text-xs text-gray-400">
          How often to check device connections
        </p>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">Retry Attempts</label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            max={10}
            value={config.retryAttempts}
            onChange={(e) => onChange({ ...config, retryAttempts: Number(e.target.value) })}
            className="w-24 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <span className="text-sm text-gray-500">attempts</span>
        </div>
        <p className="text-xs text-gray-400">
          Number of reconnection attempts before marking device offline
        </p>
      </div>
    </div>
  );
}

// --- Main Component ---

export function DeviceConfigEditor({
  device,
  onSave,
  onCancel,
  className,
}: DeviceConfigEditorProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize config from device or defaults
  const initialConfig = useMemo(() => {
    const defaults = getDefaultConfig(device.device_type);
    return { ...defaults, ...(device.config || {}) };
  }, [device.device_type, device.config]);

  const [config, setConfig] = useState<Record<string, unknown>>(initialConfig);

  // Reset config when device changes
  useEffect(() => {
    const defaults = getDefaultConfig(device.device_type);
    setConfig({ ...defaults, ...(device.config || {}) });
  }, [device.id, device.device_type, device.config]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      await onSave(config);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  }, [config, onSave]);

  const handleResetDefaults = useCallback(() => {
    setConfig(getDefaultConfig(device.device_type));
  }, [device.device_type]);

  const hasChanges = useMemo(() => {
    return JSON.stringify(config) !== JSON.stringify(initialConfig);
  }, [config, initialConfig]);

  // Render device-specific editor
  const renderEditor = () => {
    switch (device.device_type) {
      case 'microphone':
        return (
          <MicrophoneEditor
            config={config as MicrophoneConfig}
            onChange={(c) => setConfig(c as Record<string, unknown>)}
          />
        );
      case 'camera':
        return (
          <CameraEditor
            config={config as CameraConfig}
            onChange={(c) => setConfig(c as Record<string, unknown>)}
          />
        );
      case 'sensor':
        return (
          <SensorEditor
            config={config as SensorConfig}
            onChange={(c) => setConfig(c as Record<string, unknown>)}
          />
        );
      case 'gateway':
        return (
          <GatewayEditor
            config={config as GatewayConfig}
            onChange={(c) => setConfig(c as Record<string, unknown>)}
          />
        );
      default:
        return (
          <div className="text-center py-8 text-gray-500">
            <p>No configuration options available for this device type.</p>
          </div>
        );
    }
  };

  return (
    <div className={cn('bg-white rounded-lg border border-gray-200 shadow-sm', className)}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center gap-3">
        <div className="p-2 bg-gray-100 rounded-lg">
          <svg
            className="w-5 h-5 text-gray-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d={getDeviceIcon(device.device_type)}
            />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-gray-900 truncate">{device.name}</h3>
          <p className="text-xs text-gray-500 capitalize">{device.device_type} Configuration</p>
        </div>
        {hasChanges && (
          <span className="text-xs font-medium text-amber-600 bg-amber-100 px-2 py-0.5 rounded">
            Unsaved
          </span>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="px-4 py-2 bg-red-50 border-b border-red-200 text-sm text-red-700 flex items-center gap-2">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          {error}
        </div>
      )}

      {/* Config editor */}
      <div className="p-4">{renderEditor()}</div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
        <button
          type="button"
          onClick={handleResetDefaults}
          className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
        >
          Reset to defaults
        </button>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
              'bg-blue-600 text-white hover:bg-blue-700',
              'disabled:bg-blue-400 disabled:cursor-not-allowed'
            )}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default DeviceConfigEditor;
