/**
 * UnifiedFloorPlanViewer Component
 *
 * Merges functionality from FloorPlanViewer (auth image loading, location markers,
 * touch support, legend) and InteractiveFloorPlan (device icons with status colors,
 * SVG icons, alert pulse, device click/select) into a single viewer.
 *
 * Also adds placement mode: when active, cursor becomes crosshair, pan is disabled,
 * and clicking the floor plan calculates percentage coordinates for device positioning.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { cn } from '../../utils';
import { tokenStorage } from '../../services/api';
import type { FloorPlan, FloorKeyLocation, IoTDevice, DeviceType, DeviceStatus } from '../../types';

// --- Marker types (from FloorPlanViewer) ---

export type MarkerType =
  | 'stairwell'
  | 'elevator'
  | 'emergency_exit'
  | 'fire_extinguisher'
  | 'fire_alarm'
  | 'aed'
  | 'electrical_panel'
  | 'gas_shutoff'
  | 'water_shutoff'
  | 'hazard'
  | 'custom';

export interface LocationMarker {
  type: MarkerType;
  name: string;
  x: number;
  y: number;
  description?: string;
}

// --- Device helpers (from InteractiveFloorPlan) ---

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

// --- Marker config ---

const markerConfig: Record<MarkerType, { icon: string; color: string; label: string }> = {
  stairwell: { icon: '\u{1F6B6}', color: 'bg-blue-500', label: 'Stairwell' },
  elevator: { icon: '\u{1F6D7}', color: 'bg-blue-400', label: 'Elevator' },
  emergency_exit: { icon: '\u{1F6AA}', color: 'bg-green-500', label: 'Emergency Exit' },
  fire_extinguisher: { icon: '\u{1F9EF}', color: 'bg-red-500', label: 'Fire Extinguisher' },
  fire_alarm: { icon: '\u{1F514}', color: 'bg-red-400', label: 'Fire Alarm Pull' },
  aed: { icon: '\u{1F493}', color: 'bg-pink-500', label: 'AED' },
  electrical_panel: { icon: '\u26A1', color: 'bg-yellow-500', label: 'Electrical Panel' },
  gas_shutoff: { icon: '\u{1F525}', color: 'bg-orange-500', label: 'Gas Shutoff' },
  water_shutoff: { icon: '\u{1F4A7}', color: 'bg-cyan-500', label: 'Water Shutoff' },
  hazard: { icon: '\u26A0\uFE0F', color: 'bg-amber-500', label: 'Hazard' },
  custom: { icon: '\u{1F4CD}', color: 'bg-gray-500', label: 'Location' },
};

// --- Props ---

interface UnifiedFloorPlanViewerProps {
  floorPlan: FloorPlan;
  // Location markers (accepts FloorKeyLocation from API, casts type internally)
  keyLocations?: FloorKeyLocation[];
  emergencyExits?: FloorKeyLocation[];
  fireEquipment?: FloorKeyLocation[];
  hazards?: FloorKeyLocation[];
  // Devices
  devices?: IoTDevice[];
  selectedDeviceId?: string | null;
  alertingDeviceIds?: string[];
  onDeviceClick?: (device: IoTDevice) => void;
  // Placement mode
  isPlacementMode?: boolean;
  onPlaceDevice?: (posX: number, posY: number) => void;
  // Options
  showControls?: boolean;
  showLegend?: boolean;
  className?: string;
}

export function UnifiedFloorPlanViewer({
  floorPlan,
  keyLocations = [],
  emergencyExits = [],
  fireEquipment = [],
  hazards = [],
  devices = [],
  selectedDeviceId,
  alertingDeviceIds = [],
  onDeviceClick,
  isPlacementMode = false,
  onPlaceDevice,
  showControls = true,
  showLegend = true,
  className,
}: UnifiedFloorPlanViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [selectedMarker, setSelectedMarker] = useState<LocationMarker | null>(null);
  const [hoveredDevice, setHoveredDevice] = useState<string | null>(null);

  // Combine location markers (cast FloorKeyLocation.type string to MarkerType)
  const toMarker = (loc: FloorKeyLocation, fallbackType: MarkerType): LocationMarker => ({
    type: (loc.type as MarkerType) || fallbackType,
    name: loc.name,
    x: loc.x ?? 0,
    y: loc.y ?? 0,
    description: loc.description,
  });

  const allMarkers: LocationMarker[] = [
    ...keyLocations.map((m) => toMarker(m, (m.type as MarkerType) || 'custom')),
    ...emergencyExits.map((m) => toMarker(m, 'emergency_exit')),
    ...fireEquipment.map((m) => toMarker(m, 'fire_extinguisher')),
    ...hazards.map((m) => toMarker(m, 'hazard')),
  ];

  // --- Auth image loading ---
  const [authImageUrl, setAuthImageUrl] = useState<string | null>(null);
  const rawImgSrc = floorPlan.plan_file_url || floorPlan.plan_thumbnail_url;

  useEffect(() => {
    if (!rawImgSrc) return;

    let revoked = false;
    const token = tokenStorage.getAccessToken();

    setImageLoaded(false);
    setImageError(false);

    fetch(rawImgSrc, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.blob();
      })
      .then((blob) => {
        if (!revoked) {
          setAuthImageUrl(URL.createObjectURL(blob));
          setImageError(false);
        }
      })
      .catch(() => {
        if (!revoked) {
          setImageError(true);
        }
      });

    return () => {
      revoked = true;
      if (authImageUrl) {
        URL.revokeObjectURL(authImageUrl);
      }
    };
  }, [rawImgSrc]); // eslint-disable-line react-hooks/exhaustive-deps

  // --- Zoom controls ---
  const zoomIn = useCallback(() => setScale((s) => Math.min(s * 1.2, 5)), []);
  const zoomOut = useCallback(() => setScale((s) => Math.max(s / 1.2, 0.5)), []);
  const resetView = useCallback(() => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setScale((s) => Math.min(Math.max(s * delta, 0.5), 5));
  }, []);

  // --- Pan handlers (disabled in placement mode) ---
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button !== 0) return;
      if (isPlacementMode) return; // Don't pan in placement mode
      setIsDragging(true);
      setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
    },
    [position, isPlacementMode]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging) return;
      setPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    },
    [isDragging, dragStart]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // --- Touch handlers ---
  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      if (isPlacementMode) return;
      if (e.touches.length === 1) {
        setIsDragging(true);
        setDragStart({
          x: e.touches[0].clientX - position.x,
          y: e.touches[0].clientY - position.y,
        });
      }
    },
    [position, isPlacementMode]
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (!isDragging || e.touches.length !== 1) return;
      setPosition({
        x: e.touches[0].clientX - dragStart.x,
        y: e.touches[0].clientY - dragStart.y,
      });
    },
    [isDragging, dragStart]
  );

  const handleTouchEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  // --- Placement click handler ---
  const handlePlacementClick = useCallback(
    (e: React.MouseEvent) => {
      if (!isPlacementMode || !onPlaceDevice || !imageRef.current) return;

      const rect = imageRef.current.getBoundingClientRect();
      const posX = ((e.clientX - rect.left) / rect.width) * 100;
      const posY = ((e.clientY - rect.top) / rect.height) * 100;

      // Clamp to 0-100
      const clampedX = Math.max(0, Math.min(100, posX));
      const clampedY = Math.max(0, Math.min(100, posY));

      onPlaceDevice(clampedX, clampedY);
    },
    [isPlacementMode, onPlaceDevice]
  );

  // --- Marker click ---
  const handleMarkerClick = useCallback(
    (marker: LocationMarker, e: React.MouseEvent) => {
      e.stopPropagation();
      setSelectedMarker(marker);
    },
    []
  );

  const activeMarkerTypes = new Set(allMarkers.map((m) => m.type));

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Controls */}
      {showControls && (
        <div className="flex items-center justify-between p-2 bg-gray-100 border-b">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">
              {floorPlan.floor_name || `Floor ${floorPlan.floor_number}`}
            </span>
            {floorPlan.floor_area_sqm && (
              <span className="text-xs text-gray-500">
                ({floorPlan.floor_area_sqm.toFixed(0)} m\u00B2)
              </span>
            )}
            {isPlacementMode && (
              <span className="text-xs font-medium text-orange-600 bg-orange-100 px-2 py-0.5 rounded">
                Click to place device
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={zoomOut}
              className="p-1.5 rounded hover:bg-gray-200 transition-colors"
              title="Zoom Out"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
              </svg>
            </button>
            <span className="text-xs text-gray-600 w-12 text-center">
              {Math.round(scale * 100)}%
            </span>
            <button
              onClick={zoomIn}
              className="p-1.5 rounded hover:bg-gray-200 transition-colors"
              title="Zoom In"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </button>
            <button
              onClick={resetView}
              className="p-1.5 rounded hover:bg-gray-200 transition-colors ml-2"
              title="Reset View"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
                />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Viewer Container */}
      <div
        ref={containerRef}
        className={cn(
          'flex-1 overflow-hidden bg-gray-50 relative',
          isPlacementMode
            ? 'cursor-crosshair'
            : 'cursor-grab active:cursor-grabbing'
        )}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <div
          className="absolute inset-0 flex items-center justify-center"
          style={{
            transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
            transformOrigin: 'center center',
            transition: isDragging ? 'none' : 'transform 0.1s ease-out',
          }}
        >
          {authImageUrl ? (
            <div className="relative" onClick={handlePlacementClick}>
              <img
                ref={imageRef}
                src={authImageUrl}
                alt={`Floor plan - ${floorPlan.floor_name || `Floor ${floorPlan.floor_number}`}`}
                className={cn(
                  'max-w-full max-h-full object-contain',
                  imageLoaded ? 'opacity-100' : 'opacity-0'
                )}
                onLoad={() => setImageLoaded(true)}
                onError={() => setImageError(true)}
                draggable={false}
              />

              {/* Location markers overlay */}
              {imageLoaded &&
                allMarkers.map((marker, index) => (
                  <button
                    key={`marker-${marker.type}-${index}`}
                    className={cn(
                      'absolute w-6 h-6 -ml-3 -mt-3 rounded-full flex items-center justify-center',
                      'text-white text-xs shadow-lg border-2 border-white',
                      'hover:scale-125 transition-transform cursor-pointer',
                      markerConfig[marker.type]?.color || 'bg-gray-500'
                    )}
                    style={{
                      left: `${marker.x}%`,
                      top: `${marker.y}%`,
                    }}
                    onClick={(e) => handleMarkerClick(marker, e)}
                    title={marker.name}
                  >
                    {markerConfig[marker.type]?.icon || '\u{1F4CD}'}
                  </button>
                ))}

              {/* Device icons overlay */}
              {imageLoaded &&
                devices.map((device) => {
                  if (device.position_x == null || device.position_y == null) return null;

                  const isAlerting = alertingDeviceIds.includes(device.id);
                  const isSelected = selectedDeviceId === device.id;
                  const isHovered = hoveredDevice === device.id;
                  const color = getDeviceColor(device.status);

                  return (
                    <div
                      key={`device-${device.id}`}
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
                        className={cn(
                          'rounded-full flex items-center justify-center cursor-pointer transition-transform',
                          isSelected && 'ring-2 ring-blue-500 ring-offset-2 scale-125',
                          isHovered && !isSelected && 'scale-110'
                        )}
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

                      {/* Tooltip */}
                      {isHovered && (
                        <div className="absolute top-full mt-1 left-1/2 -translate-x-1/2 whitespace-nowrap bg-gray-900 text-white text-xs px-2 py-1 rounded shadow-lg z-30">
                          {device.name}
                          <div className="text-gray-300">
                            {device.device_type} &middot; {device.status}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
            </div>
          ) : (
            <div className="text-center text-gray-500 p-8">
              <svg
                className="w-16 h-16 mx-auto mb-4 text-gray-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
                />
              </svg>
              <p>No floor plan image available</p>
              <p className="text-sm mt-2">Upload a floor plan to view it here</p>
            </div>
          )}

          {/* Loading indicator */}
          {authImageUrl && !imageLoaded && !imageError && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          )}

          {/* Error state - only show if there was a URL to load that failed */}
          {imageError && rawImgSrc && (
            <div className="text-center text-red-500 p-8">
              <svg
                className="w-16 h-16 mx-auto mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <p>Failed to load floor plan image</p>
            </div>
          )}
        </div>

        {/* Selected marker tooltip */}
        {selectedMarker && (
          <div
            className="absolute bottom-4 left-4 right-4 bg-white rounded-lg shadow-lg p-3 z-10"
            onClick={() => setSelectedMarker(null)}
          >
            <div className="flex items-start gap-3">
              <span
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center text-white',
                  markerConfig[selectedMarker.type]?.color || 'bg-gray-500'
                )}
              >
                {markerConfig[selectedMarker.type]?.icon || '\u{1F4CD}'}
              </span>
              <div className="flex-1">
                <h4 className="font-medium text-gray-900">{selectedMarker.name}</h4>
                <p className="text-sm text-gray-500">
                  {markerConfig[selectedMarker.type]?.label || 'Location'}
                </p>
                {selectedMarker.description && (
                  <p className="text-sm text-gray-600 mt-1">{selectedMarker.description}</p>
                )}
              </div>
              <button className="text-gray-400 hover:text-gray-600">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      {showLegend && (activeMarkerTypes.size > 0 || devices.length > 0) && (
        <div className="p-2 bg-gray-50 border-t">
          <div className="flex flex-wrap gap-3">
            {/* Location marker legend */}
            {Array.from(activeMarkerTypes).map((type) => (
              <div key={type} className="flex items-center gap-1 text-xs text-gray-600">
                <span
                  className={cn(
                    'w-4 h-4 rounded-full flex items-center justify-center text-white text-[10px]',
                    markerConfig[type]?.color || 'bg-gray-500'
                  )}
                >
                  {markerConfig[type]?.icon || '\u{1F4CD}'}
                </span>
                <span>{markerConfig[type]?.label || type}</span>
              </div>
            ))}
            {/* Device legend */}
            {devices.length > 0 && (
              <>
                {activeMarkerTypes.size > 0 && (
                  <span className="text-gray-300">|</span>
                )}
                <div className="flex items-center gap-1 text-xs text-gray-600">
                  <span className="w-3 h-3 rounded-full bg-green-500" />
                  <span>Online</span>
                </div>
                <div className="flex items-center gap-1 text-xs text-gray-600">
                  <span className="w-3 h-3 rounded-full bg-red-500" />
                  <span>Alert</span>
                </div>
                <div className="flex items-center gap-1 text-xs text-gray-600">
                  <span className="w-3 h-3 rounded-full bg-gray-400" />
                  <span>Offline</span>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
