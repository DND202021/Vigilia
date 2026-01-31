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
 * - Real-time synchronization
 * - Collaborative editing with presence indicators
 */

import { useState, useRef, useCallback, useEffect, lazy, Suspense } from 'react';
import { cn } from '../../utils';
import { tokenStorage, toAbsoluteApiUrl } from '../../services/api';
import { LocationMarker } from './LocationMarker';
import { useMarkerStore, initializeMarkersFromFloorPlan } from '../../stores/markerStore';
import { useFloorPlanSync } from '../../hooks/useFloorPlanSync';
import { PresenceIndicator } from './PresenceIndicator';
import { DeviceStatusOverlay } from './DeviceStatusOverlay';
import { DeviceEditSidebar } from './DeviceEditSidebar';
import { useAuthStore } from '../../stores/authStore';
import { useDevicePositionStore } from '../../stores/devicePositionStore';
import type { FloorPlan, Building, FloorKeyLocation, LocationMarkerType, IoTDevice } from '../../types';
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
  const floorPlanContainerRef = useRef<HTMLDivElement>(null);

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
  const [containerDimensions, setContainerDimensions] = useState({ width: 0, height: 0 });
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [deviceEditMode, setDeviceEditMode] = useState(false);
  const [draggingDevice, setDraggingDevice] = useState<IoTDevice | null>(null);

  // Auth store for current user
  const { user } = useAuthStore();

  // Device position store for device placement
  const {
    positions: devicePositions,
    addDeviceToFloorPlan,
    updateDevicePosition,
    removeDeviceFromFloorPlan,
    setCurrentFloorPlan: setCurrentDeviceFloorPlan,
  } = useDevicePositionStore();

  // Real-time sync hook
  const {
    isConnected,
    isSyncing,
    // activeUsers - accessed via PresenceIndicator from store
    setEditing: setSyncEditing,
    addMarker: syncAddMarker,
    updateMarker: syncUpdateMarker,
    deleteMarker: syncDeleteMarker,
    conflicts,
    resolveConflict,
    // devicePositions - accessed via DeviceStatusOverlay from store
    error: syncError,
  } = useFloorPlanSync({
    floorPlanId: floorPlan.id,
    userId: user?.id || '',
    userName: user?.full_name || 'Anonymous',
    userRole: user?.role || undefined,
    enabled: !!user,
  });

  // Marker store state
  const {
    markers,
    selectedMarkerId,
    isEditing,
    isDirty,
    isSaving,
    error,
    addMarker: localAddMarker,
    updateMarker: localUpdateMarker,
    deleteMarker: localDeleteMarker,
    selectMarker,
    setEditing,
    saveMarkers,
  } = useMarkerStore();

  // Use sync methods when connected, fall back to local methods
  const addMarker = isConnected ? syncAddMarker : localAddMarker;
  const updateMarker = isConnected ? syncUpdateMarker : localUpdateMarker;
  const deleteMarker = isConnected ? syncDeleteMarker : localDeleteMarker;

  // Track container dimensions for DeviceStatusOverlay
  useEffect(() => {
    const updateDimensions = () => {
      if (floorPlanContainerRef.current) {
        setContainerDimensions({
          width: floorPlanContainerRef.current.offsetWidth,
          height: floorPlanContainerRef.current.offsetHeight,
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, [imageLoaded]);

  // Sync editing state with presence
  useEffect(() => {
    setSyncEditing(isEditing);
  }, [isEditing, setSyncEditing]);

  // Cleanup: set editing to false when component unmounts
  useEffect(() => {
    return () => {
      setSyncEditing(false);
    };
  }, [setSyncEditing]);

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

  // Load authenticated image - convert relative URL to absolute
  const rawImgSrc = toAbsoluteApiUrl(floorPlan.plan_file_url || floorPlan.plan_thumbnail_url);

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

  // --- Fullscreen controls ---
  const toggleFullscreen = useCallback(() => {
    if (!containerRef.current) return;

    if (!document.fullscreenElement) {
      containerRef.current.parentElement?.requestFullscreen?.().catch((err) => {
        console.warn('Failed to enter fullscreen:', err);
      });
    } else {
      document.exitFullscreen?.().catch((err) => {
        console.warn('Failed to exit fullscreen:', err);
      });
    }
  }, []);

  // Listen for fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // Wheel zoom handler - must use native event listener with { passive: false }
  // to allow preventDefault() for preventing page scroll during zoom
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      setScale((s) => Math.min(Math.max(s * delta, 0.5), 5));
    };

    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => container.removeEventListener('wheel', handleWheel);
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

  // --- Device edit mode handlers ---
  const handleToggleDeviceEditMode = useCallback(() => {
    if (deviceEditMode) {
      // Exiting device edit mode
      setDeviceEditMode(false);
      setDraggingDevice(null);
    } else {
      // Entering device edit mode - exit marker edit mode first
      if (isEditing) {
        setEditing(false);
      }
      setDeviceEditMode(true);
      setCurrentDeviceFloorPlan(floorPlan.id);
    }
  }, [deviceEditMode, isEditing, setEditing, floorPlan.id, setCurrentDeviceFloorPlan]);

  const handleDeviceDragStart = useCallback((device: IoTDevice) => {
    setDraggingDevice(device);
  }, []);

  const handleDeviceDragEnd = useCallback(() => {
    setDraggingDevice(null);
  }, []);

  const handleDeviceDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    if (!draggingDevice || !imageRef.current) return;

    const rect = imageRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    // Clamp to 0-100
    const clampedX = Math.max(0, Math.min(100, x));
    const clampedY = Math.max(0, Math.min(100, y));

    // Check if device is already placed (has position in store)
    const existingPos = devicePositions[draggingDevice.id];
    if (existingPos) {
      // Update position
      await updateDevicePosition(draggingDevice.id, clampedX, clampedY);
    } else {
      // Add new device to floor plan with full device details
      await addDeviceToFloorPlan(
        draggingDevice.id,
        clampedX,
        clampedY,
        {
          deviceName: draggingDevice.name,
          deviceType: draggingDevice.device_type,
          iconType: draggingDevice.icon_type,
          iconColor: draggingDevice.icon_color,
          status: draggingDevice.status,
        }
      );
    }

    setDraggingDevice(null);
  }, [draggingDevice, devicePositions, updateDevicePosition, addDeviceToFloorPlan]);

  const handleDevicePositionUpdate = useCallback(async (deviceId: string, x: number, y: number) => {
    await updateDevicePosition(deviceId, x, y);
  }, [updateDevicePosition]);

  const handleDeviceRemove = useCallback(async (deviceId: string) => {
    await removeDeviceFromFloorPlan(deviceId);
  }, [removeDeviceFromFloorPlan]);

  // Get list of placed device IDs
  const placedDeviceIds = Object.keys(devicePositions).filter(
    id => devicePositions[id]?.floor_plan_id === floorPlan.id
  );

  return (
    <div className={cn(
      'flex flex-col h-full',
      isFullscreen && 'fixed inset-0 z-50 bg-gray-900',
      className
    )}>
      {/* Toolbar */}
      <div className={cn(
        'flex items-center justify-between p-2 border-b gap-2 flex-wrap',
        isFullscreen ? 'bg-gray-800 border-gray-700' : 'bg-gray-100'
      )}>
        {/* Left: Floor info and edit toggle */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">
            {floorPlan.floor_name || `Floor ${floorPlan.floor_number}`}
          </span>

          {/* Marker edit mode toggle */}
          <button
            onClick={handleToggleEditMode}
            disabled={deviceEditMode}
            className={cn(
              'p-1.5 rounded transition-colors',
              isEditing
                ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                : deviceEditMode
                  ? 'text-gray-400 cursor-not-allowed'
                  : 'hover:bg-gray-200 text-gray-600'
            )}
            title={isEditing ? 'Exit Marker Edit Mode' : 'Edit Markers'}
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

          {/* Device edit mode toggle */}
          <button
            onClick={handleToggleDeviceEditMode}
            disabled={isEditing}
            className={cn(
              'p-1.5 rounded transition-colors',
              deviceEditMode
                ? 'bg-green-100 text-green-700 hover:bg-green-200'
                : isEditing
                  ? 'text-gray-400 cursor-not-allowed'
                  : 'hover:bg-gray-200 text-gray-600'
            )}
            title={deviceEditMode ? 'Exit Device Edit Mode' : 'Edit Devices'}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
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
          {deviceEditMode && (
            <span className="text-xs text-green-600 hidden sm:inline">
              Drag devices from sidebar, right-click to remove
            </span>
          )}
        </div>

        {/* Center: Presence and sync status */}
        <div className="flex items-center gap-2 ml-auto">
          {/* Connection status indicator */}
          {!isConnected && user && (
            <span className="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded">
              <span className="w-2 h-2 bg-amber-500 rounded-full" />
              Offline
            </span>
          )}

          {/* Sync status indicator */}
          {isSyncing && (
            <span className="flex items-center gap-1 text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
              <svg className="w-3 h-3 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Syncing...
            </span>
          )}

          {/* Presence indicator */}
          <PresenceIndicator floorPlanId={floorPlan.id} className="ml-auto" />
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

          {/* Fullscreen button */}
          <button
            onClick={toggleFullscreen}
            className={cn(
              'p-1.5 rounded transition-colors ml-1',
              isFullscreen ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'
            )}
            title={isFullscreen ? 'Exit Fullscreen (Esc)' : 'Fullscreen'}
          >
            {isFullscreen ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25"
                />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
                />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="px-3 py-2 bg-red-50 border-b border-red-200 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Sync error message */}
      {syncError && (
        <div className="px-3 py-2 bg-red-50 border-b border-red-200 text-sm text-red-700 flex items-center gap-2">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          Sync error: {syncError}
        </div>
      )}

      {/* Conflict notification banner */}
      {conflicts.length > 0 && (
        <div className="px-3 py-2 bg-orange-50 border-b border-orange-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span className="text-sm text-orange-800">
              {conflicts.length} conflict{conflicts.length > 1 ? 's' : ''} detected - another user modified markers you were editing
            </span>
          </div>
          <div className="flex gap-2">
            {conflicts.map((conflict) => (
              <div key={conflict.marker_id} className="flex gap-1">
                <button
                  onClick={() => resolveConflict(conflict.marker_id, 'keep_local')}
                  className="px-2 py-1 text-xs text-orange-700 bg-white border border-orange-300 rounded hover:bg-orange-50"
                  title="Keep your version"
                >
                  Keep Mine
                </button>
                <button
                  onClick={() => resolveConflict(conflict.marker_id, 'accept_remote')}
                  className="px-2 py-1 text-xs text-orange-700 bg-white border border-orange-300 rounded hover:bg-orange-50"
                  title="Accept the other user's version"
                >
                  Accept Theirs
                </button>
                <button
                  onClick={() => resolveConflict(conflict.marker_id, 'merge')}
                  className="px-2 py-1 text-xs text-white bg-orange-600 rounded hover:bg-orange-700"
                  title="Merge both versions"
                >
                  Merge
                </button>
              </div>
            ))}
          </div>
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

      {/* Main content area - floor plan with optional sidebar */}
      <div className="flex flex-1 min-h-0">
        {/* Floor Plan Viewer */}
        <div
          ref={containerRef}
          className={cn(
            'flex-1 overflow-hidden bg-gray-50 relative',
            isEditing ? 'cursor-crosshair' : deviceEditMode ? 'cursor-default' : 'cursor-grab active:cursor-grabbing'
          )}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onDrop={deviceEditMode ? handleDeviceDrop : undefined}
          onDragOver={deviceEditMode ? (e) => e.preventDefault() : undefined}
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
            <div ref={floorPlanContainerRef} className="relative" onClick={handleFloorPlanClick}>
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

              {/* Device status overlay - shows real-time device positions */}
              {imageLoaded && containerDimensions.width > 0 && (
                <DeviceStatusOverlay
                  floorPlanId={floorPlan.id}
                  containerWidth={containerDimensions.width}
                  containerHeight={containerDimensions.height}
                  showLabels={scale >= 1.5}
                  isEditable={deviceEditMode}
                  onDeviceDragEnd={handleDevicePositionUpdate}
                  onDeviceRemove={handleDeviceRemove}
                />
              )}

              {/* Drop indicator when dragging device */}
              {deviceEditMode && draggingDevice && (
                <div className="absolute inset-0 bg-green-50/50 border-2 border-dashed border-green-500 rounded flex items-center justify-center pointer-events-none">
                  <div className="bg-white px-4 py-2 rounded-lg shadow-lg text-sm text-green-600 font-medium">
                    Drop {draggingDevice.name} here
                  </div>
                </div>
              )}
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

        {/* Device Edit Sidebar */}
        {deviceEditMode && (
          <DeviceEditSidebar
            buildingId={building.id}
            floorPlanId={floorPlan.id}
            placedDeviceIds={placedDeviceIds}
            onDragStart={handleDeviceDragStart}
            onDragEnd={handleDeviceDragEnd}
            isFullscreen={isFullscreen}
          />
        )}
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
