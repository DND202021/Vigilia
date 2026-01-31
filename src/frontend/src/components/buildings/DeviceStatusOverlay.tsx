/**
 * DeviceStatusOverlay Component
 *
 * Renders device icons on a floor plan with real-time status indicators.
 * Supports customizable icon types and colors for first responders and tactical teams.
 */

import { useMemo, useState, useEffect } from 'react';
import { useDevicePositionStore } from '../../stores/devicePositionStore';
import type { DeviceStatus, DeviceType, DeviceIconType } from '../../types';
import { getDeviceIconConfig, getDefaultIconForDeviceType } from '../../types';
import { cn } from '../../utils';

const STATUS_COLORS: Record<DeviceStatus, { bg: string; ring: string; pulse?: boolean }> = {
  online: { bg: 'bg-green-500', ring: 'ring-green-300' },
  offline: { bg: 'bg-gray-400', ring: 'ring-gray-200' },
  alert: { bg: 'bg-red-500', ring: 'ring-red-300', pulse: true },
  maintenance: { bg: 'bg-yellow-500', ring: 'ring-yellow-300' },
  error: { bg: 'bg-red-600', ring: 'ring-red-400', pulse: true },
};

// Fallback icons for legacy devices without icon_type
const DEVICE_ICONS: Record<DeviceType, string> = {
  microphone: '\u{1F399}\uFE0F',
  camera: '\u{1F4F9}',
  sensor: '\u{1F4E1}',
  gateway: '\u{1F5A7}',
  other: '\u{1F4BB}',
};

/**
 * Get icon and color for a device based on its icon_type/icon_color or device_type fallback
 */
function getDeviceVisuals(
  deviceType: DeviceType,
  iconType?: DeviceIconType | string,
  iconColor?: string
): { icon: string; color: string } {
  // If device has a custom icon_type, use it
  if (iconType) {
    const config = getDeviceIconConfig(iconType);
    if (config) {
      return {
        icon: config.icon,
        color: iconColor || config.color,
      };
    }
  }

  // Fall back to default icon for device type
  const defaultConfig = getDefaultIconForDeviceType(deviceType);
  return {
    icon: defaultConfig?.icon || DEVICE_ICONS[deviceType] || DEVICE_ICONS.other,
    color: iconColor || defaultConfig?.color || 'bg-gray-500',
  };
}

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
    icon_type?: DeviceIconType | string;
    icon_color?: string;
    status: DeviceStatus;
    last_seen?: string;
  }>;
  onDeviceClick?: (deviceId: string) => void;
  onDeviceDragStart?: (deviceId: string) => void;
  onDeviceDragEnd?: (deviceId: string, x: number, y: number) => void;
  onDeviceRemove?: (deviceId: string) => void;
  isEditable?: boolean;
  showLabels?: boolean;
  className?: string;
}

function DeviceMarker({
  device,
  position,
  containerWidth,
  containerHeight,
  onClick,
  onDragStart,
  onDragEnd,
  onRemove,
  isEditable,
  showLabel,
}: {
  device: {
    id: string;
    name: string;
    device_type: DeviceType;
    icon_type?: DeviceIconType | string;
    icon_color?: string;
    status: DeviceStatus;
    last_seen?: string;
  };
  position: { x: number; y: number };
  containerWidth: number;
  containerHeight: number;
  onClick?: () => void;
  onDragStart?: () => void;
  onDragEnd?: (x: number, y: number) => void;
  onRemove?: () => void;
  isEditable?: boolean;
  showLabel?: boolean;
}) {
  const [showContextMenu, setShowContextMenu] = useState(false);
  const [contextMenuPos, setContextMenuPos] = useState({ x: 0, y: 0 });

  const statusStyle = STATUS_COLORS[device.status] || STATUS_COLORS.offline;
  const { icon, color: iconColor } = getDeviceVisuals(
    device.device_type,
    device.icon_type,
    device.icon_color
  );

  // Convert percentage to pixels
  const left = (position.x / 100) * containerWidth;
  const top = (position.y / 100) * containerHeight;

  const handleContextMenu = (e: React.MouseEvent) => {
    if (!isEditable) return;
    e.preventDefault();
    e.stopPropagation();
    setContextMenuPos({ x: e.clientX, y: e.clientY });
    setShowContextMenu(true);
  };

  const handleRemove = () => {
    setShowContextMenu(false);
    onRemove?.();
  };

  // Close context menu on click outside
  useEffect(() => {
    if (!showContextMenu) return;
    const handleClick = () => setShowContextMenu(false);
    window.addEventListener('click', handleClick);
    return () => window.removeEventListener('click', handleClick);
  }, [showContextMenu]);

  return (
    <>
      <div
        className={cn(
          'absolute transform -translate-x-1/2 -translate-y-1/2 group',
          isEditable ? 'cursor-grab active:cursor-grabbing' : 'cursor-pointer'
        )}
        style={{ left: `${left}px`, top: `${top}px` }}
        onClick={onClick}
        onContextMenu={handleContextMenu}
        draggable={isEditable}
        onDragStart={(e) => {
          e.dataTransfer.setData('text/plain', device.id);
          onDragStart?.();
        }}
        onDragEnd={(e) => {
          // Calculate new position based on drop location
          const parent = (e.target as HTMLElement).closest('[data-device-overlay]');
          if (parent) {
            const rect = parent.getBoundingClientRect();
            const newX = ((e.clientX - rect.left) / rect.width) * 100;
            const newY = ((e.clientY - rect.top) / rect.height) * 100;
            // Clamp to 0-100
            const clampedX = Math.max(0, Math.min(100, newX));
            const clampedY = Math.max(0, Math.min(100, newY));
            onDragEnd?.(clampedX, clampedY);
          }
        }}
      >
        {/* Marker */}
        <div
          className={cn(
            'w-8 h-8 rounded-full flex items-center justify-center text-sm',
            'ring-2 shadow-md transition-transform hover:scale-110',
            // Use custom icon color if set, otherwise use status-based color
            device.icon_color ? iconColor : statusStyle.bg,
            statusStyle.ring,
            statusStyle.pulse && 'animate-pulse',
            isEditable && 'ring-offset-1 ring-offset-blue-400'
          )}
        >
          <span className="drop-shadow-sm">{icon}</span>
        </div>

        {/* Edit indicator */}
        {isEditable && (
          <div className="absolute -top-1 -right-1 w-3 h-3 bg-blue-500 rounded-full border border-white flex items-center justify-center">
            <svg className="w-2 h-2 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M4 8h16" />
            </svg>
          </div>
        )}

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
          {isEditable && (
            <div className="text-blue-400 text-[10px] mt-1 border-t border-gray-700 pt-1">
              Drag to move • Right-click to remove
            </div>
          )}
        </div>
      </div>

      {/* Context menu */}
      {showContextMenu && (
        <div
          className="fixed bg-white rounded-lg shadow-lg border py-1 z-50"
          style={{ left: contextMenuPos.x, top: contextMenuPos.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={handleRemove}
            className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Remove from floor plan
          </button>
        </div>
      )}
    </>
  );
}

export function DeviceStatusOverlay({
  floorPlanId,
  containerWidth,
  containerHeight,
  devices: externalDevices,
  onDeviceClick,
  onDeviceDragStart,
  onDeviceDragEnd,
  onDeviceRemove,
  isEditable = false,
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
            device: {
              ...device,
              icon_type: device.icon_type,
              icon_color: device.icon_color,
            },
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
          name: pos.device_name || `Device ${pos.device_id.slice(0, 8)}`,
          device_type: pos.device_type || 'other' as DeviceType,
          icon_type: pos.icon_type,
          icon_color: pos.icon_color,
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
    <div
      className={cn('absolute inset-0', isEditable ? '' : 'pointer-events-none', className)}
      data-device-overlay
    >
      {devicesWithPositions.map(({ device, position, status }) => (
        <div key={device.id} className="pointer-events-auto">
          <DeviceMarker
            device={{ ...device, status }}
            position={position}
            containerWidth={containerWidth}
            containerHeight={containerHeight}
            onClick={() => onDeviceClick?.(device.id)}
            onDragStart={() => onDeviceDragStart?.(device.id)}
            onDragEnd={(x, y) => onDeviceDragEnd?.(device.id, x, y)}
            onRemove={() => onDeviceRemove?.(device.id)}
            isEditable={isEditable}
            showLabel={showLabels}
          />
        </div>
      ))}
    </div>
  );
}

export default DeviceStatusOverlay;
