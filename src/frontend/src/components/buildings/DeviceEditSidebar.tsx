/**
 * DeviceEditSidebar Component
 *
 * Sidebar showing unplaced devices that can be dragged onto floor plans.
 * Also shows placed devices with option to reposition or remove.
 */

import { useState, useEffect, useMemo } from 'react';
import { iotDevicesApi } from '../../services/api';
import type { IoTDevice, DeviceType, DeviceStatus } from '../../types';
import { cn } from '../../utils';

const DEVICE_ICONS: Record<DeviceType, string> = {
  microphone: '🎙️',
  camera: '📹',
  sensor: '📡',
  gateway: '🖧',
  other: '💻',
};

const STATUS_COLORS: Record<DeviceStatus, string> = {
  online: 'bg-green-500',
  offline: 'bg-gray-400',
  alert: 'bg-red-500',
  maintenance: 'bg-yellow-500',
  error: 'bg-red-600',
};

interface DeviceEditSidebarProps {
  buildingId: string;
  floorPlanId: string;
  placedDeviceIds: string[];
  onDragStart: (device: IoTDevice) => void;
  onDragEnd: () => void;
  isFullscreen?: boolean;
  className?: string;
}

export function DeviceEditSidebar({
  buildingId,
  floorPlanId,
  placedDeviceIds,
  onDragStart,
  onDragEnd,
  isFullscreen = false,
  className,
}: DeviceEditSidebarProps) {
  const [devices, setDevices] = useState<IoTDevice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'unplaced' | 'placed'>('unplaced');

  // Load all devices for this building
  useEffect(() => {
    const loadDevices = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await iotDevicesApi.list({ building_id: buildingId, page_size: 100 });
        setDevices(response.items);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load devices');
      } finally {
        setIsLoading(false);
      }
    };

    loadDevices();
  }, [buildingId]);

  // Filter devices
  const filteredDevices = useMemo(() => {
    const placedSet = new Set(placedDeviceIds);

    switch (filter) {
      case 'unplaced':
        return devices.filter(d => !placedSet.has(d.id) && d.floor_plan_id !== floorPlanId);
      case 'placed':
        return devices.filter(d => placedSet.has(d.id) || d.floor_plan_id === floorPlanId);
      default:
        return devices;
    }
  }, [devices, placedDeviceIds, floorPlanId, filter]);

  const unplacedCount = devices.filter(d => !placedDeviceIds.includes(d.id) && d.floor_plan_id !== floorPlanId).length;
  const placedCount = devices.filter(d => placedDeviceIds.includes(d.id) || d.floor_plan_id === floorPlanId).length;

  return (
    <div className={cn(
      'flex flex-col border-l',
      isFullscreen ? 'bg-gray-800 border-gray-700 w-64' : 'bg-white w-56',
      className
    )}>
      {/* Header */}
      <div className={cn(
        'p-3 border-b',
        isFullscreen ? 'border-gray-700' : ''
      )}>
        <h3 className={cn(
          'text-sm font-semibold',
          isFullscreen ? 'text-gray-100' : 'text-gray-700'
        )}>
          Devices
        </h3>
        <p className={cn(
          'text-xs mt-1',
          isFullscreen ? 'text-gray-400' : 'text-gray-500'
        )}>
          Drag to position on floor plan
        </p>
      </div>

      {/* Filter tabs */}
      <div className={cn(
        'flex border-b',
        isFullscreen ? 'border-gray-700' : ''
      )}>
        <button
          onClick={() => setFilter('unplaced')}
          className={cn(
            'flex-1 px-2 py-1.5 text-xs font-medium transition-colors',
            filter === 'unplaced'
              ? isFullscreen ? 'bg-blue-600 text-white' : 'bg-blue-100 text-blue-700'
              : isFullscreen ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:bg-gray-50'
          )}
        >
          Unplaced ({unplacedCount})
        </button>
        <button
          onClick={() => setFilter('placed')}
          className={cn(
            'flex-1 px-2 py-1.5 text-xs font-medium transition-colors',
            filter === 'placed'
              ? isFullscreen ? 'bg-blue-600 text-white' : 'bg-blue-100 text-blue-700'
              : isFullscreen ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:bg-gray-50'
          )}
        >
          Placed ({placedCount})
        </button>
      </div>

      {/* Device list */}
      <div className="flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <div className={cn(
            'text-xs text-center py-4',
            isFullscreen ? 'text-gray-400' : 'text-gray-500'
          )}>
            Loading devices...
          </div>
        ) : error ? (
          <div className="text-xs text-center py-4 text-red-500">
            {error}
          </div>
        ) : filteredDevices.length === 0 ? (
          <div className={cn(
            'text-xs text-center py-4',
            isFullscreen ? 'text-gray-400' : 'text-gray-500'
          )}>
            {filter === 'unplaced' ? 'All devices placed' : 'No devices placed'}
          </div>
        ) : (
          <div className="space-y-1.5">
            {filteredDevices.map((device) => (
              <div
                key={device.id}
                draggable
                onDragStart={() => onDragStart(device)}
                onDragEnd={onDragEnd}
                className={cn(
                  'flex items-center gap-2 p-2 rounded-lg cursor-grab active:cursor-grabbing',
                  'border transition-colors',
                  isFullscreen
                    ? 'bg-gray-700 border-gray-600 hover:border-blue-500'
                    : 'bg-gray-50 border-transparent hover:border-blue-200 hover:bg-gray-100'
                )}
              >
                {/* Device icon with status */}
                <div className="relative">
                  <span className="text-lg">{DEVICE_ICONS[device.device_type] || DEVICE_ICONS.other}</span>
                  <span className={cn(
                    'absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2',
                    isFullscreen ? 'border-gray-700' : 'border-gray-50',
                    STATUS_COLORS[device.status] || STATUS_COLORS.offline
                  )} />
                </div>

                {/* Device info */}
                <div className="flex-1 min-w-0">
                  <div className={cn(
                    'text-sm font-medium truncate',
                    isFullscreen ? 'text-gray-100' : 'text-gray-800'
                  )}>
                    {device.name}
                  </div>
                  <div className={cn(
                    'text-xs capitalize truncate',
                    isFullscreen ? 'text-gray-400' : 'text-gray-500'
                  )}>
                    {device.device_type}
                  </div>
                </div>

                {/* Drag handle */}
                <svg
                  className={cn(
                    'w-4 h-4 flex-shrink-0',
                    isFullscreen ? 'text-gray-500' : 'text-gray-400'
                  )}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 8h16M4 16h16"
                  />
                </svg>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Help text */}
      <div className={cn(
        'p-2 border-t text-xs',
        isFullscreen ? 'border-gray-700 text-gray-400' : 'text-gray-500'
      )}>
        <div className="flex items-center gap-1 mb-1">
          <span>💡</span>
          <span className="font-medium">Tips:</span>
        </div>
        <ul className="space-y-0.5 ml-4">
          <li>• Drag device to position</li>
          <li>• Right-click to remove</li>
          <li>• Drag placed device to move</li>
        </ul>
      </div>
    </div>
  );
}

export default DeviceEditSidebar;
