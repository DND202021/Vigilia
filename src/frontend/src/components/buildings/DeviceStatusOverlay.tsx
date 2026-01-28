/**
 * DeviceStatusOverlay Component
 *
 * Renders device icons on a floor plan with real-time status indicators.
 */

import { useMemo } from 'react';
import { useDevicePositionStore } from '../../stores/devicePositionStore';
import type { DeviceStatus, DeviceType } from '../../types';
import { cn } from '../../utils';

const STATUS_COLORS: Record<DeviceStatus, { bg: string; ring: string; pulse?: boolean }> = {
  online: { bg: 'bg-green-500', ring: 'ring-green-300' },
  offline: { bg: 'bg-gray-400', ring: 'ring-gray-200' },
  alert: { bg: 'bg-red-500', ring: 'ring-red-300', pulse: true },
  maintenance: { bg: 'bg-yellow-500', ring: 'ring-yellow-300' },
  error: { bg: 'bg-red-600', ring: 'ring-red-400', pulse: true },
};

const DEVICE_ICONS: Record<DeviceType, string> = {
  microphone: '\u{1F399}\uFE0F',
  camera: '\u{1F4F9}',
  sensor: '\u{1F4E1}',
  gateway: '\u{1F5A7}',
  other: '\u{1F4BB}',
};

interface DeviceStatusOverlayProps {
  floorPlanId: string;
  containerWidth: number;
  containerHeight: number;
  devices?: Array<{
    id: string;
    name: string;
    device_type: DeviceType;
    position_x?: number;
    position_y?: number;
    status: DeviceStatus;
    last_seen?: string;
  }>;
  onDeviceClick?: (deviceId: string) => void;
  showLabels?: boolean;
  className?: string;
}

function DeviceMarker({
  device,
  position,
  containerWidth,
  containerHeight,
  onClick,
  showLabel,
}: {
  device: { id: string; name: string; device_type: DeviceType; status: DeviceStatus; last_seen?: string };
  position: { x: number; y: number };
  containerWidth: number;
  containerHeight: number;
  onClick?: () => void;
  showLabel?: boolean;
}) {
  const statusStyle = STATUS_COLORS[device.status] || STATUS_COLORS.offline;
  const icon = DEVICE_ICONS[device.device_type] || DEVICE_ICONS.other;

  // Convert percentage to pixels
  const left = (position.x / 100) * containerWidth;
  const top = (position.y / 100) * containerHeight;

  return (
    <div
      className="absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer group"
      style={{ left: `${left}px`, top: `${top}px` }}
      onClick={onClick}
    >
      {/* Marker */}
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center text-sm',
          'ring-2 shadow-md transition-transform hover:scale-110',
          statusStyle.bg,
          statusStyle.ring,
          statusStyle.pulse && 'animate-pulse'
        )}
      >
        <span className="drop-shadow-sm">{icon}</span>
      </div>

      {/* Label */}
      {showLabel && (
        <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 px-1.5 py-0.5 bg-white rounded text-[10px] font-medium text-gray-700 shadow-sm whitespace-nowrap">
          {device.name}
        </div>
      )}

      {/* Tooltip on hover */}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1.5 bg-gray-900 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20 whitespace-nowrap">
        <div className="font-medium">{device.name}</div>
        <div className="text-gray-300">{device.device_type}</div>
        <div className={cn(
          'mt-0.5',
          device.status === 'online' && 'text-green-400',
          device.status === 'alert' && 'text-red-400',
          device.status === 'offline' && 'text-gray-400',
          device.status === 'maintenance' && 'text-yellow-400',
          device.status === 'error' && 'text-red-400'
        )}>
          Status: {device.status}
        </div>
        {device.last_seen && (
          <div className="text-gray-400 text-[10px] mt-0.5">
            Last seen: {new Date(device.last_seen).toLocaleString()}
          </div>
        )}
      </div>
    </div>
  );
}

export function DeviceStatusOverlay({
  floorPlanId,
  containerWidth,
  containerHeight,
  devices: externalDevices,
  onDeviceClick,
  showLabels = false,
  className,
}: DeviceStatusOverlayProps) {
  const storePositions = useDevicePositionStore((state) => state.positions);

  // Merge external devices with store positions
  const devicesWithPositions = useMemo(() => {
    if (externalDevices) {
      return externalDevices
        .filter(d => d.position_x != null && d.position_y != null)
        .map(device => {
          const storePos = storePositions[device.id];
          return {
            device,
            position: {
              x: storePos?.position_x ?? device.position_x!,
              y: storePos?.position_y ?? device.position_y!,
            },
            status: storePos?.status ?? device.status,
          };
        });
    }

    // Use store positions only
    return Object.values(storePositions)
      .filter(pos => pos.floor_plan_id === floorPlanId)
      .map(pos => ({
        device: {
          id: pos.device_id,
          name: `Device ${pos.device_id.slice(0, 8)}`,
          device_type: 'other' as DeviceType,
          status: pos.status,
          last_seen: pos.last_seen,
        },
        position: { x: pos.position_x, y: pos.position_y },
        status: pos.status,
      }));
  }, [externalDevices, storePositions, floorPlanId]);

  if (containerWidth === 0 || containerHeight === 0) {
    return null;
  }

  return (
    <div className={cn('absolute inset-0 pointer-events-none', className)}>
      {devicesWithPositions.map(({ device, position, status }) => (
        <div key={device.id} className="pointer-events-auto">
          <DeviceMarker
            device={{ ...device, status }}
            position={position}
            containerWidth={containerWidth}
            containerHeight={containerHeight}
            onClick={() => onDeviceClick?.(device.id)}
            showLabel={showLabels}
          />
        </div>
      ))}
    </div>
  );
}

export default DeviceStatusOverlay;
