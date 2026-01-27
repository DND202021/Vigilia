/**
 * FloorPlanViewer Component
 * Interactive viewer for floor plan images with pan, zoom, and marker overlay.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { cn } from '../../utils';
import { tokenStorage } from '../../services/api';
import type { FloorPlan } from '../../types';

// Marker types for different location categories
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
  x: number; // Percentage 0-100
  y: number; // Percentage 0-100
  description?: string;
}

interface FloorPlanViewerProps {
  floorPlan: FloorPlan;
  imageUrl?: string;
  keyLocations?: LocationMarker[];
  emergencyExits?: LocationMarker[];
  fireEquipment?: LocationMarker[];
  hazards?: LocationMarker[];
  onMarkerClick?: (marker: LocationMarker) => void;
  className?: string;
  showControls?: boolean;
  showLegend?: boolean;
}

// Marker icon configurations
const markerConfig: Record<MarkerType, { icon: string; color: string; label: string }> = {
  stairwell: { icon: '🚶', color: 'bg-blue-500', label: 'Stairwell' },
  elevator: { icon: '🛗', color: 'bg-blue-400', label: 'Elevator' },
  emergency_exit: { icon: '🚪', color: 'bg-green-500', label: 'Emergency Exit' },
  fire_extinguisher: { icon: '🧯', color: 'bg-red-500', label: 'Fire Extinguisher' },
  fire_alarm: { icon: '🔔', color: 'bg-red-400', label: 'Fire Alarm Pull' },
  aed: { icon: '💓', color: 'bg-pink-500', label: 'AED' },
  electrical_panel: { icon: '⚡', color: 'bg-yellow-500', label: 'Electrical Panel' },
  gas_shutoff: { icon: '🔥', color: 'bg-orange-500', label: 'Gas Shutoff' },
  water_shutoff: { icon: '💧', color: 'bg-cyan-500', label: 'Water Shutoff' },
  hazard: { icon: '⚠️', color: 'bg-amber-500', label: 'Hazard' },
  custom: { icon: '📍', color: 'bg-gray-500', label: 'Location' },
};

export function FloorPlanViewer({
  floorPlan,
  imageUrl,
  keyLocations = [],
  emergencyExits = [],
  fireEquipment = [],
  hazards = [],
  onMarkerClick,
  className,
  showControls = true,
  showLegend = true,
}: FloorPlanViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [selectedMarker, setSelectedMarker] = useState<LocationMarker | null>(null);

  // Combine all markers
  const allMarkers: LocationMarker[] = [
    ...keyLocations,
    ...emergencyExits.map((m) => ({ ...m, type: 'emergency_exit' as MarkerType })),
    ...fireEquipment.map((m) => ({ ...m, type: m.type || ('fire_extinguisher' as MarkerType) })),
    ...hazards.map((m) => ({ ...m, type: 'hazard' as MarkerType })),
  ];

  // Zoom controls
  const zoomIn = useCallback(() => {
    setScale((s) => Math.min(s * 1.2, 5));
  }, []);

  const zoomOut = useCallback(() => {
    setScale((s) => Math.max(s / 1.2, 0.5));
  }, []);

  const resetView = useCallback(() => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  }, []);

  // Mouse wheel zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setScale((s) => Math.min(Math.max(s * delta, 0.5), 5));
  }, []);

  // Pan handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return; // Only left click
    setIsDragging(true);
    setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
  }, [position]);

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

  // Touch handlers for mobile
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (e.touches.length === 1) {
      setIsDragging(true);
      setDragStart({
        x: e.touches[0].clientX - position.x,
        y: e.touches[0].clientY - position.y,
      });
    }
  }, [position]);

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

  // Handle marker click
  const handleMarkerClick = useCallback(
    (marker: LocationMarker, e: React.MouseEvent) => {
      e.stopPropagation();
      setSelectedMarker(marker);
      onMarkerClick?.(marker);
    },
    [onMarkerClick]
  );

  // Fetch image with auth header since <img> tags don't send Authorization headers
  const [authImageUrl, setAuthImageUrl] = useState<string | null>(null);
  const rawImgSrc = imageUrl || floorPlan.plan_file_url || floorPlan.plan_thumbnail_url;

  useEffect(() => {
    if (!rawImgSrc) return;

    let revoked = false;
    const token = tokenStorage.getAccessToken();

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

  const imgSrc = authImageUrl;

  // Get unique marker types for legend
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
                ({floorPlan.floor_area_sqm.toFixed(0)} m²)
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
        className="flex-1 overflow-hidden bg-gray-50 relative cursor-grab active:cursor-grabbing"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* Image and markers container */}
        <div
          className="absolute inset-0 flex items-center justify-center"
          style={{
            transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
            transformOrigin: 'center center',
            transition: isDragging ? 'none' : 'transform 0.1s ease-out',
          }}
        >
          {imgSrc ? (
            <div className="relative">
              <img
                src={imgSrc}
                alt={`Floor plan - ${floorPlan.floor_name || `Floor ${floorPlan.floor_number}`}`}
                className={cn(
                  'max-w-full max-h-full object-contain',
                  imageLoaded ? 'opacity-100' : 'opacity-0'
                )}
                onLoad={() => setImageLoaded(true)}
                onError={() => setImageError(true)}
                draggable={false}
              />

              {/* Markers overlay */}
              {imageLoaded && allMarkers.map((marker, index) => (
                <button
                  key={`${marker.type}-${marker.name}-${index}`}
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
                  {markerConfig[marker.type]?.icon || '📍'}
                </button>
              ))}
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
          {imgSrc && !imageLoaded && !imageError && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          )}

          {/* Error state */}
          {imageError && (
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
                {markerConfig[selectedMarker.type]?.icon || '📍'}
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
      {showLegend && activeMarkerTypes.size > 0 && (
        <div className="p-2 bg-gray-50 border-t">
          <div className="flex flex-wrap gap-2">
            {Array.from(activeMarkerTypes).map((type) => (
              <div key={type} className="flex items-center gap-1 text-xs text-gray-600">
                <span
                  className={cn(
                    'w-4 h-4 rounded-full flex items-center justify-center text-white text-[10px]',
                    markerConfig[type]?.color || 'bg-gray-500'
                  )}
                >
                  {markerConfig[type]?.icon || '📍'}
                </span>
                <span>{markerConfig[type]?.label || type}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default FloorPlanViewer;
