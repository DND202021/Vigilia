/**
 * FloorPlanEditor Component
 *
 * Main editing interface for floor plan markers. Extends the base floor plan
 * viewing functionality with:
 * - Edit mode toggle with toolbar
 * - Click-to-place markers
 * - Drag-to-reposition markers
 * - Marker properties modal
 * - Save/undo functionality
 * - Print support
 */

import { useState, useRef, useCallback, useEffect, lazy, Suspense } from 'react';
import { cn } from '../../utils';
import { tokenStorage } from '../../services/api';
import { LocationMarker } from './LocationMarker';
import { useMarkerStore, initializeMarkersFromFloorPlan } from '../../stores/markerStore';
import type { FloorPlan, Building, FloorKeyLocation, LocationMarkerType } from '../../types';
import { DEFAULT_MARKER_CONFIGS } from '../../types';

// Lazy load modals
const MarkerPropertiesModal = lazy(() => import('./MarkerPropertiesModal'));

// --- Props ---

export interface FloorPlanEditorProps {
  floorPlan: FloorPlan;
  building: Building;
  initialMarkers?: FloorKeyLocation[];
  onSave?: (markers: FloorKeyLocation[]) => void;
  className?: string;
}

// Grouped marker type options for the dropdown
const MARKER_TYPE_GROUPS: Record<string, { types: LocationMarkerType[]; label: string }> = {
  fire_equipment: {
    label: 'Fire Equipment',
    types: ['fire_extinguisher', 'fire_hose', 'alarm_pull', 'fire_alarm', 'sprinkler_control'],
  },
  access: {
    label: 'Access',
    types: ['stairwell', 'elevator', 'emergency_exit', 'roof_access'],
  },
  utilities: {
    label: 'Utilities',
    types: ['electrical_panel', 'gas_shutoff', 'water_shutoff'],
  },
  hazards: {
    label: 'Hazards',
    types: ['hazmat', 'hazard', 'confined_space', 'high_voltage'],
  },
  medical: {
    label: 'Medical',
    types: ['aed', 'first_aid', 'eyewash'],
  },
};

// --- Component ---

export function FloorPlanEditor({
  floorPlan,
  building,
  initialMarkers,
  onSave,
  className,
}: FloorPlanEditorProps) {
  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  // Local state
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [authImageUrl, setAuthImageUrl] = useState<string | null>(null);
  const [selectedMarkerType, setSelectedMarkerType] = useState<LocationMarkerType>('fire_extinguisher');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingMarker, setEditingMarker] = useState<FloorKeyLocation | null>(null);
  const [pendingPosition, setPendingPosition] = useState<{ x: number; y: number } | null>(null);
  const [showUnsavedWarning, setShowUnsavedWarning] = useState(false);

  // Marker store state
  const {
    markers,
    selectedMarkerId,
    isEditing,
    isDirty,
    isSaving,
    error,
    addMarker,
    updateMarker,
    deleteMarker,
    selectMarker,
    setEditing,
    saveMarkers,
  } = useMarkerStore();

  // Initialize markers on mount or when floor plan changes
  useEffect(() => {
    const markersToLoad = initialMarkers ?? floorPlan.key_locations ?? [];
    initializeMarkersFromFloorPlan(floorPlan.id, markersToLoad);
  }, [floorPlan.id, initialMarkers, floorPlan.key_locations]);

  // Warn on unsaved changes when navigating away
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty]);

  // Load authenticated image
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

  // --- Pan handlers (disabled when editing or dragging marker) ---
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button !== 0) return;
      // Don't start pan when clicking on markers in edit mode
      if (isEditing && (e.target as HTMLElement).closest('[data-marker]')) return;

      setIsDragging(true);
      setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
    },
    [position, isEditing]
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

  // --- Click-to-place handler ---
  const handleFloorPlanClick = useCallback(
    (e: React.MouseEvent) => {
      if (!isEditing || !imageRef.current) return;

      // Don't place if clicking on a marker
      if ((e.target as HTMLElement).closest('[data-marker]')) return;

      const rect = imageRef.current.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;

      // Clamp to 0-100
      const clampedX = Math.max(0, Math.min(100, x));
      const clampedY = Math.max(0, Math.min(100, y));

      // Store position and open modal for new marker
      setPendingPosition({ x: clampedX, y: clampedY });
      setEditingMarker({
        type: selectedMarkerType,
        name: '',
        x: clampedX,
        y: clampedY,
      });
      setIsModalOpen(true);
    },
    [isEditing, selectedMarkerType]
  );

  // --- Marker handlers ---
  const handleMarkerSelect = useCallback(
    (marker: FloorKeyLocation) => {
      const markerWithId = markers.find(
        (m) => m.x === marker.x && m.y === marker.y && m.type === marker.type
      );
      if (markerWithId) {
        selectMarker(markerWithId.id);
      }
    },
    [markers, selectMarker]
  );

  const handleMarkerDoubleClick = useCallback(
    (marker: FloorKeyLocation) => {
      const markerWithId = markers.find(
        (m) => m.x === marker.x && m.y === marker.y && m.type === marker.type
      );
      if (markerWithId) {
        setEditingMarker(markerWithId);
        setIsModalOpen(true);
      }
    },
    [markers]
  );

  const handleMarkerDragEnd = useCallback(
    (marker: FloorKeyLocation, newX: number, newY: number) => {
      const markerWithId = markers.find(
        (m) => m.x === marker.x && m.y === marker.y && m.type === marker.type
      );
      if (markerWithId) {
        updateMarker(markerWithId.id, { x: newX, y: newY });
      }
    },
    [markers, updateMarker]
  );

  const handleMarkerDelete = useCallback(
    (marker: FloorKeyLocation) => {
      const markerWithId = markers.find(
        (m) => m.x === marker.x && m.y === marker.y && m.type === marker.type
      );
      if (markerWithId) {
        deleteMarker(markerWithId.id);
      }
    },
    [markers, deleteMarker]
  );

  // --- Modal handlers ---
  const handleModalSave = useCallback(
    (marker: FloorKeyLocation) => {
      if (pendingPosition) {
        // New marker
        addMarker({
          ...marker,
          x: pendingPosition.x,
          y: pendingPosition.y,
        });
        setPendingPosition(null);
      } else if (editingMarker && 'id' in editingMarker && editingMarker.id) {
        // Update existing marker
        updateMarker(editingMarker.id, marker);
      }
      setIsModalOpen(false);
      setEditingMarker(null);
    },
    [pendingPosition, editingMarker, addMarker, updateMarker]
  );

  const handleModalDelete = useCallback(
    (markerId: string | undefined) => {
      if (markerId) {
        deleteMarker(markerId);
      }
      setIsModalOpen(false);
      setEditingMarker(null);
    },
    [deleteMarker]
  );

  const handleModalClose = useCallback(() => {
    setIsModalOpen(false);
    setEditingMarker(null);
    setPendingPosition(null);
  }, []);

  // --- Save handler ---
  const handleSave = useCallback(async () => {
    try {
      await saveMarkers();
      // Convert markers to FloorKeyLocation format for callback
      if (onSave) {
        const savedMarkers: FloorKeyLocation[] = markers.map((m) => ({
          type: m.type,
          name: m.name,
          x: m.x ?? 0,
          y: m.y ?? 0,
          description: m.description,
          notes: m.notes,
        }));
        onSave(savedMarkers);
      }
    } catch (err) {
      // Error is already set in store
      console.error('Failed to save markers:', err);
    }
  }, [saveMarkers, onSave, markers]);

  // --- Keyboard handlers ---
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isEditing) return;

      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedMarkerId && !isModalOpen) {
          e.preventDefault();
          deleteMarker(selectedMarkerId);
        }
      }

      if (e.key === 'Escape') {
        selectMarker(null);
        if (isModalOpen) {
          handleModalClose();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isEditing, selectedMarkerId, isModalOpen, deleteMarker, selectMarker, handleModalClose]);

  // --- Edit mode toggle with dirty check ---
  const handleToggleEditMode = useCallback(() => {
    if (isEditing && isDirty) {
      setShowUnsavedWarning(true);
    } else {
      setEditing(!isEditing);
    }
  }, [isEditing, isDirty, setEditing]);

  const handleDiscardChanges = useCallback(() => {
    const markersToLoad = initialMarkers ?? floorPlan.key_locations ?? [];
    initializeMarkersFromFloorPlan(floorPlan.id, markersToLoad);
    setEditing(false);
    setShowUnsavedWarning(false);
  }, [floorPlan.id, floorPlan.key_locations, initialMarkers, setEditing]);

  // --- Print handler ---
  const handlePrint = useCallback(() => {
    // Open print view in new window
    const printWindow = window.open('', '_blank');
    if (!printWindow) return;

    const markersList = markers
      .map((m) => {
        const config = DEFAULT_MARKER_CONFIGS.find((c) => c.type === m.type);
        return `<li>${config?.icon || ''} ${m.name} (${config?.label || m.type})</li>`;
      })
      .join('');

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Floor Plan - ${building.name} - ${floorPlan.floor_name || `Floor ${floorPlan.floor_number}`}</title>
          <style>
            body { font-family: sans-serif; margin: 20px; }
            h1 { font-size: 18px; margin-bottom: 5px; }
            h2 { font-size: 14px; font-weight: normal; color: #666; margin-top: 0; }
            img { max-width: 100%; height: auto; border: 1px solid #ccc; }
            ul { columns: 2; column-gap: 20px; }
            li { margin-bottom: 5px; }
            @media print {
              img { max-height: 70vh; }
            }
          </style>
        </head>
        <body>
          <h1>${building.name}</h1>
          <h2>${floorPlan.floor_name || `Floor ${floorPlan.floor_number}`} - ${building.full_address}</h2>
          ${authImageUrl ? `<img src="${authImageUrl}" alt="Floor Plan" />` : '<p>No floor plan image</p>'}
          <h3>Key Locations (${markers.length})</h3>
          <ul>${markersList || '<li>No markers</li>'}</ul>
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.print();
  }, [authImageUrl, building, floorPlan, markers]);

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Toolbar */}
      <div className="flex items-center justify-between p-2 bg-gray-100 border-b gap-2 flex-wrap">
        {/* Left: Floor info and edit toggle */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">
            {floorPlan.floor_name || `Floor ${floorPlan.floor_number}`}
          </span>

          {/* Edit mode toggle */}
          <button
            onClick={handleToggleEditMode}
            className={cn(
              'p-1.5 rounded transition-colors',
              isEditing
                ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                : 'hover:bg-gray-200 text-gray-600'
            )}
            title={isEditing ? 'Exit Edit Mode' : 'Enter Edit Mode'}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
              />
            </svg>
          </button>

          {/* Marker type selector (edit mode only) */}
          {isEditing && (
            <select
              value={selectedMarkerType}
              onChange={(e) => setSelectedMarkerType(e.target.value as LocationMarkerType)}
              className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {Object.entries(MARKER_TYPE_GROUPS).map(([category, group]) => (
                <optgroup key={category} label={group.label}>
                  {group.types.map((type) => {
                    const config = DEFAULT_MARKER_CONFIGS.find((c) => c.type === type);
                    return (
                      <option key={type} value={type}>
                        {config?.icon} {config?.label || type}
                      </option>
                    );
                  })}
                </optgroup>
              ))}
            </select>
          )}

          {/* Unsaved indicator */}
          {isDirty && (
            <span className="text-xs font-medium text-amber-600 bg-amber-100 px-2 py-0.5 rounded">
              Unsaved changes
            </span>
          )}

          {/* Edit mode instructions */}
          {isEditing && (
            <span className="text-xs text-gray-500 hidden sm:inline">
              Click to place, drag to move, double-click to edit
            </span>
          )}
        </div>

        {/* Right: Action buttons */}
        <div className="flex items-center gap-1">
          {/* Save button (when dirty) */}
          {isDirty && (
            <button
              onClick={handleSave}
              disabled={isSaving}
              className={cn(
                'px-3 py-1.5 text-sm font-medium rounded transition-colors',
                'bg-green-600 text-white hover:bg-green-700',
                'disabled:bg-green-400 disabled:cursor-not-allowed'
              )}
            >
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          )}

          {/* Zoom controls */}
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
            className="p-1.5 rounded hover:bg-gray-200 transition-colors ml-1"
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

          {/* Print button */}
          <button
            onClick={handlePrint}
            className="p-1.5 rounded hover:bg-gray-200 transition-colors ml-2"
            title="Print Floor Plan"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="px-3 py-2 bg-red-50 border-b border-red-200 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Unsaved changes warning */}
      {showUnsavedWarning && (
        <div className="px-3 py-2 bg-amber-50 border-b border-amber-200 flex items-center justify-between">
          <span className="text-sm text-amber-800">
            You have unsaved changes. Save before exiting edit mode?
          </span>
          <div className="flex gap-2">
            <button
              onClick={handleDiscardChanges}
              className="px-3 py-1 text-sm text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50"
            >
              Discard
            </button>
            <button
              onClick={async () => {
                await handleSave();
                setEditing(false);
                setShowUnsavedWarning(false);
              }}
              className="px-3 py-1 text-sm text-white bg-green-600 rounded hover:bg-green-700"
            >
              Save & Exit
            </button>
          </div>
        </div>
      )}

      {/* Floor Plan Viewer */}
      <div
        ref={containerRef}
        className={cn(
          'flex-1 overflow-hidden bg-gray-50 relative',
          isEditing ? 'cursor-crosshair' : 'cursor-grab active:cursor-grabbing'
        )}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
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
            <div className="relative" onClick={handleFloorPlanClick}>
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
                markers.map((marker) => (
                  <LocationMarker
                    key={marker.id}
                    data-marker
                    marker={marker}
                    isSelected={marker.id === selectedMarkerId}
                    isEditable={isEditing}
                    scale={scale}
                    onSelect={handleMarkerSelect}
                    onDoubleClick={handleMarkerDoubleClick}
                    onDragEnd={handleMarkerDragEnd}
                    onDelete={handleMarkerDelete}
                  />
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
              <p className="text-sm mt-2">Upload a floor plan to start editing</p>
            </div>
          )}

          {/* Loading indicator */}
          {authImageUrl && !imageLoaded && !imageError && (
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
      </div>

      {/* Legend */}
      {markers.length > 0 && (
        <div className="p-2 bg-gray-50 border-t">
          <div className="flex flex-wrap gap-3">
            {Array.from(new Set(markers.map((m) => m.type))).map((type) => {
              const config = DEFAULT_MARKER_CONFIGS.find((c) => c.type === type);
              const count = markers.filter((m) => m.type === type).length;
              return (
                <div key={type} className="flex items-center gap-1 text-xs text-gray-600">
                  <span
                    className={cn(
                      'w-4 h-4 rounded-full flex items-center justify-center text-white text-[10px]',
                      config?.color || 'bg-gray-500'
                    )}
                  >
                    {config?.icon || ''}
                  </span>
                  <span>
                    {config?.label || type} ({count})
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Marker Properties Modal */}
      <Suspense fallback={null}>
        <MarkerPropertiesModal
          marker={editingMarker}
          isOpen={isModalOpen}
          onClose={handleModalClose}
          onSave={handleModalSave}
          onDelete={editingMarker && 'id' in editingMarker ? handleModalDelete : undefined}
        />
      </Suspense>
    </div>
  );
}

export default FloorPlanEditor;
