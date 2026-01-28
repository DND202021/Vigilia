/**
 * LocationMarker Component
 *
 * Renders an individual marker on floor plans with support for:
 * - Visual icons/emojis based on marker type
 * - Color coding by category
 * - Hover tooltips
 * - Selected state (blue ring)
 * - Editable mode with drag support
 * - Click, double-click, and delete handlers
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { cn } from '../../utils';
import type { FloorKeyLocation } from '../../types';

// --- Marker Types (aligned with UnifiedFloorPlanViewer) ---

export type MarkerType =
  | 'stairwell'
  | 'elevator'
  | 'emergency_exit'
  | 'fire_extinguisher'
  | 'fire_alarm'
  | 'alarm_pull'
  | 'sprinkler_connection'
  | 'aed'
  | 'first_aid'
  | 'electrical_panel'
  | 'gas_shutoff'
  | 'water_shutoff'
  | 'hazard'
  | 'custom';

// --- Marker Configuration ---

export const MARKER_TYPES: Record<MarkerType, { icon: string; color: string; label: string; category: MarkerCategory }> = {
  // Access (Blue)
  stairwell: { icon: '\u{1F6B6}', color: 'bg-blue-500', label: 'Stairwell', category: 'access' },
  elevator: { icon: '\u{1F6D7}', color: 'bg-blue-400', label: 'Elevator', category: 'access' },
  // Emergency Exits (Green)
  emergency_exit: { icon: '\u{1F6AA}', color: 'bg-green-500', label: 'Emergency Exit', category: 'emergency_exit' },
  // Fire Equipment (Red)
  fire_extinguisher: { icon: '\u{1F9EF}', color: 'bg-red-500', label: 'Fire Extinguisher', category: 'fire_equipment' },
  fire_alarm: { icon: '\u{1F514}', color: 'bg-red-400', label: 'Fire Alarm', category: 'fire_equipment' },
  alarm_pull: { icon: '\u{1F6A8}', color: 'bg-red-400', label: 'Alarm Pull Station', category: 'fire_equipment' },
  sprinkler_connection: { icon: '\u{1F4A6}', color: 'bg-red-300', label: 'Sprinkler Connection', category: 'fire_equipment' },
  // Medical (Pink)
  aed: { icon: '\u{1F493}', color: 'bg-pink-500', label: 'AED', category: 'medical' },
  first_aid: { icon: '\u{1FA79}', color: 'bg-pink-400', label: 'First Aid Kit', category: 'medical' },
  // Utilities (Yellow)
  electrical_panel: { icon: '\u26A1', color: 'bg-yellow-500', label: 'Electrical Panel', category: 'utilities' },
  gas_shutoff: { icon: '\u{1F525}', color: 'bg-yellow-400', label: 'Gas Shutoff', category: 'utilities' },
  water_shutoff: { icon: '\u{1F4A7}', color: 'bg-cyan-500', label: 'Water Shutoff', category: 'utilities' },
  // Hazards (Orange)
  hazard: { icon: '\u26A0\uFE0F', color: 'bg-orange-500', label: 'Hazard', category: 'hazard' },
  // Custom (Gray)
  custom: { icon: '\u{1F4CD}', color: 'bg-gray-500', label: 'Location', category: 'custom' },
};

export type MarkerCategory = 'access' | 'emergency_exit' | 'fire_equipment' | 'medical' | 'utilities' | 'hazard' | 'custom';

// Category color mapping for visual consistency
export const CATEGORY_COLORS: Record<MarkerCategory, string> = {
  access: 'bg-blue-500',
  emergency_exit: 'bg-green-500',
  fire_equipment: 'bg-red-500',
  medical: 'bg-pink-500',
  utilities: 'bg-yellow-500',
  hazard: 'bg-orange-500',
  custom: 'bg-gray-500',
};

// --- Props ---

export interface LocationMarkerProps {
  marker: FloorKeyLocation;
  isSelected?: boolean;
  isEditable?: boolean;
  scale?: number; // for zoom level adjustments
  onSelect?: (marker: FloorKeyLocation) => void;
  onDoubleClick?: (marker: FloorKeyLocation) => void;
  onDragEnd?: (marker: FloorKeyLocation, newX: number, newY: number) => void;
  onDelete?: (marker: FloorKeyLocation) => void;
}

// --- Component ---

export function LocationMarker({
  marker,
  isSelected = false,
  isEditable = false,
  scale = 1,
  onSelect,
  onDoubleClick,
  onDragEnd,
  onDelete,
}: LocationMarkerProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dragPosition, setDragPosition] = useState<{ x: number; y: number } | null>(null);
  const markerRef = useRef<HTMLDivElement>(null);
  const parentRef = useRef<HTMLElement | null>(null);

  // Get marker configuration
  const markerType = (marker.type as MarkerType) || 'custom';
  const config = MARKER_TYPES[markerType] || MARKER_TYPES.custom;

  // Calculate position (use drag position if dragging, otherwise marker position)
  const x = dragPosition?.x ?? (marker.x ?? 0);
  const y = dragPosition?.y ?? (marker.y ?? 0);

  // Handle click
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      if (!isDragging) {
        onSelect?.(marker);
      }
    },
    [marker, onSelect, isDragging]
  );

  // Handle double-click
  const handleDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      e.preventDefault();
      onDoubleClick?.(marker);
    },
    [marker, onDoubleClick]
  );

  // Handle delete
  const handleDelete = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      e.preventDefault();
      onDelete?.(marker);
    },
    [marker, onDelete]
  );

  // --- Drag handling ---

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!isEditable || e.button !== 0) return;

      e.preventDefault();
      e.stopPropagation();

      // Store parent element reference for position calculations
      if (markerRef.current) {
        parentRef.current = markerRef.current.parentElement;
      }

      setIsDragging(true);
      setDragPosition({ x: marker.x ?? 0, y: marker.y ?? 0 });
    },
    [isEditable, marker.x, marker.y]
  );

  // Handle mouse move during drag
  useEffect(() => {
    if (!isDragging || !parentRef.current) return;

    const handleMouseMove = (e: MouseEvent) => {
      const parent = parentRef.current;
      if (!parent) return;

      const rect = parent.getBoundingClientRect();
      const newX = ((e.clientX - rect.left) / rect.width) * 100;
      const newY = ((e.clientY - rect.top) / rect.height) * 100;

      // Clamp to 0-100
      const clampedX = Math.max(0, Math.min(100, newX));
      const clampedY = Math.max(0, Math.min(100, newY));

      setDragPosition({ x: clampedX, y: clampedY });
    };

    const handleMouseUp = () => {
      if (dragPosition) {
        onDragEnd?.(marker, dragPosition.x, dragPosition.y);
      }
      setIsDragging(false);
      setDragPosition(null);
      parentRef.current = null;
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragPosition, marker, onDragEnd]);

  // Scale-adjusted size (markers should appear smaller when zoomed in)
  const baseSize = 28;
  const adjustedSize = Math.max(20, Math.min(36, baseSize / Math.sqrt(scale)));

  return (
    <div
      ref={markerRef}
      className={cn(
        'absolute flex items-center justify-center',
        'transition-all duration-150 ease-out',
        isEditable ? 'cursor-move' : 'cursor-pointer',
        isDragging && 'z-50'
      )}
      style={{
        left: `${x}%`,
        top: `${y}%`,
        transform: 'translate(-50%, -50%)',
        zIndex: isSelected ? 30 : isHovered ? 20 : 10,
      }}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      onMouseDown={handleMouseDown}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Selected ring/glow */}
      {isSelected && (
        <div
          className="absolute rounded-full bg-blue-400 opacity-30 animate-pulse"
          style={{
            width: adjustedSize + 12,
            height: adjustedSize + 12,
          }}
        />
      )}

      {/* Marker icon */}
      <div
        className={cn(
          'rounded-full flex items-center justify-center',
          'text-white shadow-lg border-2 border-white',
          'transition-transform duration-150',
          config.color,
          isSelected && 'ring-2 ring-blue-500 ring-offset-2',
          (isHovered || isDragging) && !isSelected && 'scale-110',
          isDragging && 'opacity-80'
        )}
        style={{
          width: adjustedSize,
          height: adjustedSize,
          fontSize: adjustedSize * 0.5,
        }}
      >
        {config.icon}
      </div>

      {/* Delete button (when selected and editable) */}
      {isSelected && isEditable && onDelete && (
        <button
          className={cn(
            'absolute -top-1 -right-1',
            'w-5 h-5 rounded-full',
            'bg-red-500 text-white',
            'flex items-center justify-center',
            'hover:bg-red-600 transition-colors',
            'shadow-md border border-white',
            'text-xs font-bold'
          )}
          onClick={handleDelete}
          title="Delete marker"
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}

      {/* Tooltip (on hover) */}
      {isHovered && !isDragging && (
        <div
          className={cn(
            'absolute top-full mt-2 left-1/2 -translate-x-1/2',
            'whitespace-nowrap bg-gray-900 text-white',
            'text-xs px-2 py-1 rounded shadow-lg',
            'z-40 pointer-events-none'
          )}
        >
          <div className="font-medium">{marker.name}</div>
          <div className="text-gray-300">{config.label}</div>
          {marker.description && (
            <div className="text-gray-400 mt-0.5 max-w-[200px] whitespace-normal">
              {marker.description}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default LocationMarker;
