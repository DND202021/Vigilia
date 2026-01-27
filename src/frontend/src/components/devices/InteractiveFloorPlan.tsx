/**
 * Interactive Floor Plan Viewer with device icon overlay.
 *
 * Renders a floor plan image with IoT device icons positioned at their
 * stored X/Y coordinates (percentages). Supports pan/zoom and device
 * click interaction.
 */

import { useRef, useState, useCallback } from 'react';
import type { IoTDevice, DeviceType, DeviceStatus } from '../../types';

interface InteractiveFloorPlanProps {
  floorPlanUrl: string;
  devices: IoTDevice[];
  selectedDeviceId?: string | null;
  alertingDeviceIds?: string[];
  onDeviceClick?: (device: IoTDevice) => void;
  showLabels?: boolean;
  className?: string;
}

const DEVICE_ICON_SIZE = 32;

function getDeviceColor(status: DeviceStatus): string {
  switch (status) {
    case 'online': return '#22c55e';
    case 'alert': return '#ef4444';
    case 'offline': return '#9ca3af';
    case 'maintenance': return '#eab308';
    case 'error': return '#f97316';
    default: return '#6b7280';
  }
}

function getDeviceIconPath(type: DeviceType): string {
  switch (type) {
    case 'microphone':
      return 'M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3zM8 12a4 4 0 0 0 8 0h2a6 6 0 0 1-5 5.91V21h-2v-3.09A6 6 0 0 1 6 12h2z';
    case 'camera':
      return 'M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2zM12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z';
    default:
      return 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z';
  }
}

export function InteractiveFloorPlan({
  floorPlanUrl,
  devices,
  selectedDeviceId,
  alertingDeviceIds = [],
  onDeviceClick,
  showLabels = false,
  className = '',
}: InteractiveFloorPlanProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [hoveredDevice, setHoveredDevice] = useState<string | null>(null);
  const [imageLoaded, setImageLoaded] = useState(false);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setScale((prev) => Math.min(Math.max(prev * delta, 0.5), 4));
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  }, [offset]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging) return;
    setOffset({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  }, [isDragging, dragStart]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const resetView = useCallback(() => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  }, []);

  return (
    <div className={`relative overflow-hidden bg-gray-100 rounded-lg border ${className}`}>
      {/* Controls */}
      <div className="absolute top-2 right-2 z-10 flex gap-1">
        <button
          onClick={() => setScale((s) => Math.min(s * 1.2, 4))}
          className="w-8 h-8 bg-white rounded shadow flex items-center justify-center text-gray-700 hover:bg-gray-50"
          title="Zoom in"
        >
          +
        </button>
        <button
          onClick={() => setScale((s) => Math.max(s * 0.8, 0.5))}
          className="w-8 h-8 bg-white rounded shadow flex items-center justify-center text-gray-700 hover:bg-gray-50"
          title="Zoom out"
        >
          -
        </button>
        <button
          onClick={resetView}
          className="w-8 h-8 bg-white rounded shadow flex items-center justify-center text-gray-700 hover:bg-gray-50 text-xs"
          title="Reset view"
        >
          ⟲
        </button>
      </div>

      {/* Floor plan + devices */}
      <div
        ref={containerRef}
        className="relative cursor-grab active:cursor-grabbing"
        style={{
          transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`,
          transformOrigin: 'center center',
          transition: isDragging ? 'none' : 'transform 0.2s ease',
        }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <img
          src={floorPlanUrl}
          alt="Floor plan"
          className="max-w-full"
          onLoad={() => setImageLoaded(true)}
          draggable={false}
        />

        {/* Device overlay */}
        {imageLoaded && devices.map((device) => {
          if (device.position_x == null || device.position_y == null) return null;

          const isAlerting = alertingDeviceIds.includes(device.id);
          const isSelected = selectedDeviceId === device.id;
          const isHovered = hoveredDevice === device.id;
          const color = getDeviceColor(device.status);

          return (
            <div
              key={device.id}
              className="absolute"
              style={{
                left: `${device.position_x}%`,
                top: `${device.position_y}%`,
                transform: 'translate(-50%, -50%)',
                zIndex: isSelected ? 20 : isHovered ? 15 : 10,
              }}
              onMouseEnter={() => setHoveredDevice(device.id)}
              onMouseLeave={() => setHoveredDevice(null)}
              onClick={(e) => {
                e.stopPropagation();
                onDeviceClick?.(device);
              }}
            >
              {/* Alert pulse ring */}
              {isAlerting && (
                <div
                  className="absolute rounded-full animate-ping"
                  style={{
                    width: DEVICE_ICON_SIZE + 16,
                    height: DEVICE_ICON_SIZE + 16,
                    left: -(DEVICE_ICON_SIZE + 16) / 2 + DEVICE_ICON_SIZE / 2,
                    top: -(DEVICE_ICON_SIZE + 16) / 2 + DEVICE_ICON_SIZE / 2,
                    backgroundColor: 'rgba(239, 68, 68, 0.3)',
                  }}
                />
              )}

              {/* Device icon */}
              <div
                className={`rounded-full flex items-center justify-center cursor-pointer transition-transform ${
                  isSelected ? 'ring-2 ring-blue-500 ring-offset-2 scale-125' : ''
                } ${isHovered ? 'scale-110' : ''}`}
                style={{
                  width: DEVICE_ICON_SIZE,
                  height: DEVICE_ICON_SIZE,
                  backgroundColor: color,
                }}
              >
                <svg
                  width={16}
                  height={16}
                  viewBox="0 0 24 24"
                  fill="white"
                  className="pointer-events-none"
                >
                  <path d={getDeviceIconPath(device.device_type)} />
                </svg>
              </div>

              {/* Label */}
              {(showLabels || isHovered) && (
                <div className="absolute top-full mt-1 left-1/2 -translate-x-1/2 whitespace-nowrap bg-gray-900 text-white text-xs px-2 py-1 rounded shadow-lg">
                  {device.name}
                  {isHovered && (
                    <div className="text-gray-300">
                      {device.device_type} &middot; {device.status}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Empty state */}
      {!floorPlanUrl && (
        <div className="flex items-center justify-center h-64 text-gray-400">
          No floor plan uploaded
        </div>
      )}
    </div>
  );
}
