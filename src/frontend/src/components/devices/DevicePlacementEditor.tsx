/**
 * Device Placement Editor - Drag-and-drop device positioning on floor plans.
 *
 * Extends the floor plan viewer with edit mode for positioning devices.
 * Supports custom device icons and colors for first responders and tactical teams.
 */

import { useRef, useState, useCallback } from 'react';
import type { IoTDevice, DeviceType, DeviceIconType } from '../../types';
import { getDeviceIconConfig, getDefaultIconForDeviceType, DEVICE_ICON_COLORS } from '../../types';

interface DevicePlacementEditorProps {
  floorPlanUrl: string;
  floorPlanId?: string;
  devices: IoTDevice[];
  unplacedDevices: IoTDevice[];
  onSavePosition: (deviceId: string, positionX: number, positionY: number, floorPlanId: string) => Promise<void>;
  onCancel: () => void;
  className?: string;
}

function getDeviceColor(status: string, customColor?: string): string {
  // Use custom color if provided
  if (customColor) {
    // If it's a Tailwind class, convert to hex
    const colorConfig = DEVICE_ICON_COLORS.find((c) => c.value === customColor);
    if (colorConfig) return colorConfig.hex;
    // If it's already a hex color, use it
    if (customColor.startsWith('#')) return customColor;
  }

  // Fall back to status-based colors
  switch (status) {
    case 'online': return '#22c55e';
    case 'alert': return '#ef4444';
    case 'offline': return '#9ca3af';
    default: return '#6b7280';
  }
}

function getDeviceIcon(
  deviceType: DeviceType,
  iconType?: DeviceIconType | string
): string {
  // Use custom icon if provided
  if (iconType) {
    const config = getDeviceIconConfig(iconType);
    if (config) return config.icon;
  }

  // Fall back to default for device type
  const defaultConfig = getDefaultIconForDeviceType(deviceType);
  return defaultConfig?.icon || '📱';
}

export function DevicePlacementEditor({
  floorPlanUrl,
  floorPlanId,
  devices,
  unplacedDevices,
  onSavePosition,
  onCancel,
  className = '',
}: DevicePlacementEditorProps) {
  const imageRef = useRef<HTMLImageElement>(null);
  const [draggingDevice, setDraggingDevice] = useState<IoTDevice | null>(null);
  const [pendingPositions, setPendingPositions] = useState<
    Record<string, { x: number; y: number }>
  >({});
  const [saving, setSaving] = useState(false);

  // All devices with their positions (placed + pending)
  const allDevices = [
    ...devices.map((d) => ({
      ...d,
      position_x: pendingPositions[d.id]?.x ?? d.position_x,
      position_y: pendingPositions[d.id]?.y ?? d.position_y,
    })),
    ...unplacedDevices.map((d) => ({
      ...d,
      position_x: pendingPositions[d.id]?.x ?? d.position_x,
      position_y: pendingPositions[d.id]?.y ?? d.position_y,
    })),
  ];

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!draggingDevice || !imageRef.current) return;

    const rect = imageRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    // Clamp to 0-100
    const clampedX = Math.min(Math.max(x, 0), 100);
    const clampedY = Math.min(Math.max(y, 0), 100);

    setPendingPositions((prev) => ({
      ...prev,
      [draggingDevice.id]: { x: clampedX, y: clampedY },
    }));

    setDraggingDevice(null);
  }, [draggingDevice]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleSave = async () => {
    if (!floorPlanId) return;
    setSaving(true);
    try {
      for (const [deviceId, pos] of Object.entries(pendingPositions)) {
        await onSavePosition(deviceId, pos.x, pos.y, floorPlanId);
      }
      setPendingPositions({});
    } finally {
      setSaving(false);
    }
  };

  const hasPendingChanges = Object.keys(pendingPositions).length > 0;

  return (
    <div className={`flex gap-4 ${className}`}>
      {/* Unplaced devices sidebar */}
      <div className="w-56 bg-white border rounded-lg p-3 flex-shrink-0">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Unplaced Devices</h3>
        <p className="text-xs text-gray-400 mb-3">Drag devices onto the floor plan</p>

        <div className="space-y-2 max-h-96 overflow-y-auto">
          {unplacedDevices
            .filter((d) => !pendingPositions[d.id])
            .map((device) => (
              <div
                key={device.id}
                draggable
                onDragStart={() => setDraggingDevice(device)}
                className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg cursor-grab hover:bg-gray-100 border border-transparent hover:border-blue-200"
              >
                <span>{getDeviceIcon(device.device_type, device.icon_type)}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-800 truncate">{device.name}</div>
                  <div className="text-xs text-gray-500 capitalize">{device.device_type}</div>
                </div>
              </div>
            ))}

          {unplacedDevices.filter((d) => !pendingPositions[d.id]).length === 0 && (
            <p className="text-xs text-gray-400 text-center py-4">All devices placed</p>
          )}
        </div>
      </div>

      {/* Floor plan with drop zone */}
      <div className="flex-1">
        <div
          className="relative bg-gray-100 rounded-lg border-2 border-dashed border-gray-300 overflow-hidden"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
        >
          <img
            ref={imageRef}
            src={floorPlanUrl}
            alt="Floor plan"
            className="w-full"
            draggable={false}
          />

          {/* Placed device icons */}
          {allDevices.map((device) => {
            if (device.position_x == null || device.position_y == null) return null;
            const isPending = !!pendingPositions[device.id];

            return (
              <div
                key={device.id}
                draggable
                onDragStart={() => setDraggingDevice(device)}
                className="absolute cursor-grab"
                style={{
                  left: `${device.position_x}%`,
                  top: `${device.position_y}%`,
                  transform: 'translate(-50%, -50%)',
                  zIndex: 10,
                }}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-lg ${
                    isPending ? 'ring-2 ring-blue-400 ring-offset-1' : ''
                  }`}
                  style={{ backgroundColor: getDeviceColor(device.status, device.icon_color) }}
                  title={`${device.name} (${device.device_type})`}
                >
                  {getDeviceIcon(device.device_type, device.icon_type)}
                </div>
                <div className="absolute top-full mt-1 left-1/2 -translate-x-1/2 whitespace-nowrap bg-gray-900 text-white text-[10px] px-1.5 py-0.5 rounded">
                  {device.name}
                </div>
              </div>
            );
          })}

          {/* Drop hint */}
          {draggingDevice && (
            <div className="absolute inset-0 bg-blue-50/50 flex items-center justify-center pointer-events-none">
              <div className="bg-white px-4 py-2 rounded-lg shadow-lg text-sm text-blue-600 font-medium">
                Drop {draggingDevice.name} here
              </div>
            </div>
          )}
        </div>

        {/* Action bar */}
        <div className="flex justify-end gap-3 mt-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 border rounded-lg text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!hasPendingChanges || saving}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : `Save Positions${hasPendingChanges ? ` (${Object.keys(pendingPositions).length})` : ''}`}
          </button>
        </div>
      </div>
    </div>
  );
}
