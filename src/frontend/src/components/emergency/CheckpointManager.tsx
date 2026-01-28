/**
 * CheckpointManager Component
 *
 * Manages emergency checkpoints on floor plans with support for:
 * - Checkpoint display with type-specific icons and colors
 * - Placement mode for creating new checkpoints
 * - Drag-and-drop positioning (when editing)
 * - Details panel for editing checkpoint properties
 * - Visual indicators for capacity, selection state
 */

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { cn } from '../../utils';
import type {
  EmergencyCheckpoint,
  CheckpointType,
  CheckpointEquipment,
  CheckpointContactInfo,
} from '../../types';

// --- Checkpoint Type Configuration ---

interface CheckpointTypeConfig {
  icon: string;
  label: string;
  color: string;
  bgColor: string;
  ringColor: string;
}

const CHECKPOINT_TYPE_CONFIG: Record<CheckpointType, CheckpointTypeConfig> = {
  assembly_point: {
    icon: '\u{1F6A9}', // flag
    label: 'Assembly Point',
    color: 'text-green-700',
    bgColor: 'bg-green-500',
    ringColor: 'ring-green-300',
  },
  muster_station: {
    icon: '\u{1F465}', // people group
    label: 'Muster Station',
    color: 'text-blue-700',
    bgColor: 'bg-blue-500',
    ringColor: 'ring-blue-300',
  },
  first_aid: {
    icon: '\u2795', // plus/cross
    label: 'First Aid',
    color: 'text-pink-700',
    bgColor: 'bg-pink-500',
    ringColor: 'ring-pink-300',
  },
  command_post: {
    icon: '\u2B50', // star
    label: 'Command Post',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-500',
    ringColor: 'ring-yellow-300',
  },
  triage_area: {
    icon: '\u2695\uFE0F', // medical
    label: 'Triage Area',
    color: 'text-red-700',
    bgColor: 'bg-red-500',
    ringColor: 'ring-red-300',
  },
  decontamination: {
    icon: '\u2622\uFE0F', // hazard/radioactive
    label: 'Decontamination',
    color: 'text-purple-700',
    bgColor: 'bg-purple-500',
    ringColor: 'ring-purple-300',
  },
  staging_area: {
    icon: '\u{1F4E6}', // box/container
    label: 'Staging Area',
    color: 'text-orange-700',
    bgColor: 'bg-orange-500',
    ringColor: 'ring-orange-300',
  },
  media_point: {
    icon: '\u{1F4F7}', // camera
    label: 'Media Point',
    color: 'text-cyan-700',
    bgColor: 'bg-cyan-500',
    ringColor: 'ring-cyan-300',
  },
};

// --- Checkpoint Types List for Toolbar ---

const CHECKPOINT_TYPES: CheckpointType[] = [
  'assembly_point',
  'muster_station',
  'first_aid',
  'command_post',
  'triage_area',
  'decontamination',
  'staging_area',
  'media_point',
];

// --- Props ---

export interface CheckpointManagerProps {
  floorPlanId: string;
  floorPlanUrl: string;
  containerWidth: number;
  containerHeight: number;
  checkpoints: EmergencyCheckpoint[];
  selectedCheckpointId?: string;
  onCheckpointSelect?: (checkpointId: string) => void;
  onCheckpointCreate?: (
    checkpoint: Omit<EmergencyCheckpoint, 'id' | 'created_at' | 'updated_at'>
  ) => void;
  onCheckpointUpdate?: (
    checkpointId: string,
    data: Partial<EmergencyCheckpoint>
  ) => void;
  onCheckpointDelete?: (checkpointId: string) => void;
  isEditing?: boolean;
  className?: string;
}

// --- CheckpointMarker Sub-component ---

interface CheckpointMarkerProps {
  checkpoint: EmergencyCheckpoint;
  isSelected: boolean;
  isEditing: boolean;
  containerWidth: number;
  containerHeight: number;
  onSelect: () => void;
  onDragEnd?: (newX: number, newY: number) => void;
}

function CheckpointMarker({
  checkpoint,
  isSelected,
  isEditing,
  containerWidth,
  containerHeight,
  onSelect,
  onDragEnd,
}: CheckpointMarkerProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dragPosition, setDragPosition] = useState<{ x: number; y: number } | null>(null);
  const markerRef = useRef<HTMLDivElement>(null);
  const parentRef = useRef<HTMLElement | null>(null);

  const config = CHECKPOINT_TYPE_CONFIG[checkpoint.checkpoint_type];

  // Calculate position (use drag position if dragging, otherwise checkpoint position)
  const x = dragPosition?.x ?? checkpoint.position_x;
  const y = dragPosition?.y ?? checkpoint.position_y;

  // Convert percentage to pixels
  const left = (x / 100) * containerWidth;
  const top = (y / 100) * containerHeight;

  // Handle click
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      if (!isDragging) {
        onSelect();
      }
    },
    [onSelect, isDragging]
  );

  // --- Drag handling ---
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!isEditing || e.button !== 0) return;

      e.preventDefault();
      e.stopPropagation();

      if (markerRef.current) {
        parentRef.current = markerRef.current.parentElement;
      }

      setIsDragging(true);
      setDragPosition({ x: checkpoint.position_x, y: checkpoint.position_y });
    },
    [isEditing, checkpoint.position_x, checkpoint.position_y]
  );

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
      if (dragPosition && onDragEnd) {
        onDragEnd(dragPosition.x, dragPosition.y);
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
  }, [isDragging, dragPosition, onDragEnd]);

  return (
    <div
      ref={markerRef}
      className={cn(
        'absolute transform -translate-x-1/2 -translate-y-1/2',
        'transition-all duration-150 ease-out',
        isEditing ? 'cursor-move' : 'cursor-pointer',
        isDragging && 'z-50'
      )}
      style={{
        left: `${left}px`,
        top: `${top}px`,
        zIndex: isSelected ? 30 : isHovered ? 20 : 10,
      }}
      onClick={handleClick}
      onMouseDown={handleMouseDown}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Selection pulse animation */}
      {isSelected && (
        <div
          className={cn(
            'absolute rounded-full opacity-30 animate-pulse',
            config.bgColor
          )}
          style={{
            width: 44,
            height: 44,
            left: -6,
            top: -6,
          }}
        />
      )}

      {/* Marker icon */}
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center text-sm',
          'ring-2 shadow-md transition-transform',
          config.bgColor,
          config.ringColor,
          isSelected && 'ring-4 ring-blue-500 ring-offset-2',
          (isHovered || isDragging) && !isSelected && 'scale-110',
          isDragging && 'opacity-80'
        )}
      >
        <span className="drop-shadow-sm">{config.icon}</span>
      </div>

      {/* Capacity badge */}
      {checkpoint.capacity && (
        <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-gray-800 text-white text-[10px] font-bold flex items-center justify-center border border-white">
          {checkpoint.capacity > 99 ? '99+' : checkpoint.capacity}
        </div>
      )}

      {/* Label */}
      <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 px-1.5 py-0.5 bg-white rounded text-[10px] font-medium text-gray-700 shadow-sm whitespace-nowrap max-w-[100px] truncate">
        {checkpoint.name}
      </div>

      {/* Tooltip on hover */}
      {isHovered && !isDragging && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1.5 bg-gray-900 text-white text-xs rounded shadow-lg z-40 pointer-events-none whitespace-nowrap">
          <div className="font-medium">{checkpoint.name}</div>
          <div className="text-gray-300">{config.label}</div>
          {checkpoint.capacity && (
            <div className="text-gray-400 mt-0.5">
              Capacity: {checkpoint.capacity}
            </div>
          )}
          {checkpoint.responsible_person && (
            <div className="text-gray-400 mt-0.5">
              {checkpoint.responsible_person}
            </div>
          )}
        </div>
      )}

      {/* Drag position indicator */}
      {isDragging && dragPosition && (
        <div className="absolute top-full left-1/2 -translate-x-1/2 mt-6 px-2 py-1 bg-gray-900 text-white text-[10px] rounded shadow-lg z-50 whitespace-nowrap">
          X: {dragPosition.x.toFixed(1)}%, Y: {dragPosition.y.toFixed(1)}%
        </div>
      )}
    </div>
  );
}

// --- CheckpointDetailsPanel Sub-component ---

interface CheckpointDetailsPanelProps {
  checkpoint: EmergencyCheckpoint;
  onUpdate: (data: Partial<EmergencyCheckpoint>) => void;
  onDelete: () => void;
  onClose: () => void;
}

function CheckpointDetailsPanel({
  checkpoint,
  onUpdate,
  onDelete,
  onClose,
}: CheckpointDetailsPanelProps) {
  const [name, setName] = useState(checkpoint.name);
  const [capacity, setCapacity] = useState(checkpoint.capacity?.toString() || '');
  const [responsiblePerson, setResponsiblePerson] = useState(
    checkpoint.responsible_person || ''
  );
  const [instructions, setInstructions] = useState(checkpoint.instructions || '');
  const [equipment, setEquipment] = useState<CheckpointEquipment[]>(
    checkpoint.equipment || []
  );
  const [contactInfo, setContactInfo] = useState<CheckpointContactInfo>(
    checkpoint.contact_info || {}
  );
  const [newEquipmentName, setNewEquipmentName] = useState('');
  const [newEquipmentQty, setNewEquipmentQty] = useState('1');

  const config = CHECKPOINT_TYPE_CONFIG[checkpoint.checkpoint_type];

  const handleSave = useCallback(() => {
    onUpdate({
      name,
      capacity: capacity ? parseInt(capacity, 10) : undefined,
      responsible_person: responsiblePerson || undefined,
      instructions: instructions || undefined,
      equipment,
      contact_info: Object.keys(contactInfo).length > 0 ? contactInfo : undefined,
    });
  }, [name, capacity, responsiblePerson, instructions, equipment, contactInfo, onUpdate]);

  const handleAddEquipment = useCallback(() => {
    if (!newEquipmentName.trim()) return;
    setEquipment([
      ...equipment,
      { name: newEquipmentName.trim(), quantity: parseInt(newEquipmentQty, 10) || 1 },
    ]);
    setNewEquipmentName('');
    setNewEquipmentQty('1');
  }, [newEquipmentName, newEquipmentQty, equipment]);

  const handleRemoveEquipment = useCallback((index: number) => {
    setEquipment(equipment.filter((_, i) => i !== index));
  }, [equipment]);

  const handleContactChange = useCallback(
    (field: keyof CheckpointContactInfo, value: string) => {
      setContactInfo((prev) => ({
        ...prev,
        [field]: value || undefined,
      }));
    },
    []
  );

  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-200 w-80 max-h-[calc(100vh-200px)] overflow-y-auto">
      {/* Header */}
      <div className={cn('px-4 py-3 rounded-t-lg', config.bgColor)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">{config.icon}</span>
            <span className="text-white font-medium">{config.label}</span>
          </div>
          <button
            onClick={onClose}
            className="text-white/80 hover:text-white transition-colors"
          >
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

      {/* Body */}
      <div className="p-4 space-y-4">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Checkpoint name"
          />
        </div>

        {/* Capacity */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Capacity
          </label>
          <input
            type="number"
            value={capacity}
            onChange={(e) => setCapacity(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Max number of people"
            min="0"
          />
        </div>

        {/* Responsible Person */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Responsible Person
          </label>
          <input
            type="text"
            value={responsiblePerson}
            onChange={(e) => setResponsiblePerson(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Person in charge"
          />
        </div>

        {/* Contact Info */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Contact Information
          </label>
          <div className="space-y-2">
            <input
              type="tel"
              value={contactInfo.phone || ''}
              onChange={(e) => handleContactChange('phone', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Phone"
            />
            <input
              type="email"
              value={contactInfo.email || ''}
              onChange={(e) => handleContactChange('email', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Email"
            />
            <input
              type="text"
              value={contactInfo.radio_channel || ''}
              onChange={(e) => handleContactChange('radio_channel', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Radio channel"
            />
          </div>
        </div>

        {/* Equipment List */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Equipment
          </label>
          {equipment.length > 0 && (
            <ul className="mb-2 space-y-1">
              {equipment.map((item, index) => (
                <li
                  key={index}
                  className="flex items-center justify-between bg-gray-50 rounded px-2 py-1 text-sm"
                >
                  <span>
                    {item.name} (x{item.quantity})
                  </span>
                  <button
                    onClick={() => handleRemoveEquipment(index)}
                    className="text-red-500 hover:text-red-700 ml-2"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="flex gap-2">
            <input
              type="text"
              value={newEquipmentName}
              onChange={(e) => setNewEquipmentName(e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Equipment name"
            />
            <input
              type="number"
              value={newEquipmentQty}
              onChange={(e) => setNewEquipmentQty(e.target.value)}
              className="w-16 px-2 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              min="1"
            />
            <button
              onClick={handleAddEquipment}
              className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-md text-sm font-medium text-gray-700 transition-colors"
            >
              Add
            </button>
          </div>
        </div>

        {/* Instructions */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Instructions
          </label>
          <textarea
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
            placeholder="Special instructions for this checkpoint..."
          />
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 rounded-b-lg flex justify-between">
        <button
          onClick={onDelete}
          className="px-3 py-2 text-sm font-medium text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition-colors"
        >
          Delete
        </button>
        <button
          onClick={handleSave}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
        >
          Save Changes
        </button>
      </div>
    </div>
  );
}

// --- PlacementToolbar Sub-component ---

interface PlacementToolbarProps {
  selectedType: CheckpointType | null;
  onTypeSelect: (type: CheckpointType | null) => void;
  snapToGrid: boolean;
  onSnapToGridToggle: () => void;
}

function PlacementToolbar({
  selectedType,
  onTypeSelect,
  snapToGrid,
  onSnapToGridToggle,
}: PlacementToolbarProps) {
  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm font-medium text-gray-700">Place Checkpoint:</span>
        <button
          onClick={onSnapToGridToggle}
          className={cn(
            'ml-auto px-2 py-1 text-xs rounded transition-colors',
            snapToGrid
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          )}
        >
          Snap to Grid: {snapToGrid ? 'ON' : 'OFF'}
        </button>
      </div>
      <div className="flex flex-wrap gap-1">
        {CHECKPOINT_TYPES.map((type) => {
          const config = CHECKPOINT_TYPE_CONFIG[type];
          const isSelected = selectedType === type;
          return (
            <button
              key={type}
              onClick={() => onTypeSelect(isSelected ? null : type)}
              className={cn(
                'flex items-center gap-1 px-2 py-1.5 rounded-md text-xs font-medium transition-colors',
                isSelected
                  ? cn(config.bgColor, 'text-white')
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              )}
              title={config.label}
            >
              <span>{config.icon}</span>
              <span className="hidden sm:inline">{config.label}</span>
            </button>
          );
        })}
      </div>
      {selectedType && (
        <p className="mt-2 text-xs text-gray-500">
          Click on the floor plan to place a{' '}
          {CHECKPOINT_TYPE_CONFIG[selectedType].label}
        </p>
      )}
    </div>
  );
}

// --- Main Component ---

export function CheckpointManager({
  floorPlanId,
  floorPlanUrl,
  containerWidth,
  containerHeight,
  checkpoints,
  selectedCheckpointId,
  onCheckpointSelect,
  onCheckpointCreate,
  onCheckpointUpdate,
  onCheckpointDelete,
  isEditing = false,
  className,
}: CheckpointManagerProps) {
  const [placementType, setPlacementType] = useState<CheckpointType | null>(null);
  const [snapToGrid, setSnapToGrid] = useState(false);
  const [previewPosition, setPreviewPosition] = useState<{ x: number; y: number } | null>(
    null
  );
  const containerRef = useRef<HTMLDivElement>(null);

  // Get selected checkpoint
  const selectedCheckpoint = useMemo(
    () => checkpoints.find((c) => c.id === selectedCheckpointId),
    [checkpoints, selectedCheckpointId]
  );

  // Handle floor plan click for placement
  const handleFloorPlanClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!isEditing || !placementType || !containerRef.current || !onCheckpointCreate)
        return;

      const rect = containerRef.current.getBoundingClientRect();
      let x = ((e.clientX - rect.left) / rect.width) * 100;
      let y = ((e.clientY - rect.top) / rect.height) * 100;

      // Snap to grid if enabled (5% grid)
      if (snapToGrid) {
        x = Math.round(x / 5) * 5;
        y = Math.round(y / 5) * 5;
      }

      // Clamp to bounds
      x = Math.max(0, Math.min(100, x));
      y = Math.max(0, Math.min(100, y));

      const config = CHECKPOINT_TYPE_CONFIG[placementType];
      onCheckpointCreate({
        building_id: '', // Will be set by parent
        floor_plan_id: floorPlanId,
        name: `New ${config.label}`,
        checkpoint_type: placementType,
        position_x: x,
        position_y: y,
        equipment: [],
        is_active: true,
      });

      // Reset placement mode
      setPlacementType(null);
      setPreviewPosition(null);
    },
    [isEditing, placementType, snapToGrid, floorPlanId, onCheckpointCreate]
  );

  // Handle mouse move for placement preview
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!isEditing || !placementType || !containerRef.current) {
        setPreviewPosition(null);
        return;
      }

      const rect = containerRef.current.getBoundingClientRect();
      let x = ((e.clientX - rect.left) / rect.width) * 100;
      let y = ((e.clientY - rect.top) / rect.height) * 100;

      // Snap to grid if enabled
      if (snapToGrid) {
        x = Math.round(x / 5) * 5;
        y = Math.round(y / 5) * 5;
      }

      // Clamp to bounds
      x = Math.max(0, Math.min(100, x));
      y = Math.max(0, Math.min(100, y));

      setPreviewPosition({ x, y });
    },
    [isEditing, placementType, snapToGrid]
  );

  // Handle mouse leave
  const handleMouseLeave = useCallback(() => {
    setPreviewPosition(null);
  }, []);

  // Handle checkpoint drag end
  const handleCheckpointDragEnd = useCallback(
    (checkpointId: string, newX: number, newY: number) => {
      if (!onCheckpointUpdate) return;

      // Snap to grid if enabled
      let x = newX;
      let y = newY;
      if (snapToGrid) {
        x = Math.round(x / 5) * 5;
        y = Math.round(y / 5) * 5;
      }

      onCheckpointUpdate(checkpointId, {
        position_x: x,
        position_y: y,
      });
    },
    [onCheckpointUpdate, snapToGrid]
  );

  // Handle details panel close
  const handleDetailsPanelClose = useCallback(() => {
    onCheckpointSelect?.('');
  }, [onCheckpointSelect]);

  // Handle checkpoint update from details panel
  const handleCheckpointDetailsUpdate = useCallback(
    (data: Partial<EmergencyCheckpoint>) => {
      if (selectedCheckpointId && onCheckpointUpdate) {
        onCheckpointUpdate(selectedCheckpointId, data);
      }
    },
    [selectedCheckpointId, onCheckpointUpdate]
  );

  // Handle checkpoint delete
  const handleCheckpointDetailsDelete = useCallback(() => {
    if (selectedCheckpointId && onCheckpointDelete) {
      onCheckpointDelete(selectedCheckpointId);
    }
  }, [selectedCheckpointId, onCheckpointDelete]);

  // Clear placement mode when editing is disabled
  useEffect(() => {
    if (!isEditing) {
      setPlacementType(null);
      setPreviewPosition(null);
    }
  }, [isEditing]);

  if (containerWidth === 0 || containerHeight === 0) {
    return null;
  }

  return (
    <div className={cn('relative', className)}>
      {/* Placement Toolbar (when editing) */}
      {isEditing && (
        <div className="absolute top-4 left-4 z-40">
          <PlacementToolbar
            selectedType={placementType}
            onTypeSelect={setPlacementType}
            snapToGrid={snapToGrid}
            onSnapToGridToggle={() => setSnapToGrid(!snapToGrid)}
          />
        </div>
      )}

      {/* Floor Plan Container */}
      <div
        ref={containerRef}
        className={cn(
          'relative',
          isEditing && placementType && 'cursor-crosshair'
        )}
        style={{ width: containerWidth, height: containerHeight }}
        onClick={handleFloorPlanClick}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        {/* Floor Plan Image */}
        <img
          src={floorPlanUrl}
          alt="Floor Plan"
          className="w-full h-full object-contain pointer-events-none"
          draggable={false}
        />

        {/* Checkpoint Markers */}
        {checkpoints.map((checkpoint) => (
          <CheckpointMarker
            key={checkpoint.id}
            checkpoint={checkpoint}
            isSelected={checkpoint.id === selectedCheckpointId}
            isEditing={isEditing}
            containerWidth={containerWidth}
            containerHeight={containerHeight}
            onSelect={() => onCheckpointSelect?.(checkpoint.id)}
            onDragEnd={
              isEditing
                ? (newX, newY) => handleCheckpointDragEnd(checkpoint.id, newX, newY)
                : undefined
            }
          />
        ))}

        {/* Placement Preview */}
        {previewPosition && placementType && (
          <div
            className="absolute transform -translate-x-1/2 -translate-y-1/2 pointer-events-none z-50"
            style={{
              left: `${(previewPosition.x / 100) * containerWidth}px`,
              top: `${(previewPosition.y / 100) * containerHeight}px`,
            }}
          >
            <div
              className={cn(
                'w-8 h-8 rounded-full flex items-center justify-center text-sm',
                'ring-2 shadow-md opacity-70',
                CHECKPOINT_TYPE_CONFIG[placementType].bgColor,
                CHECKPOINT_TYPE_CONFIG[placementType].ringColor
              )}
            >
              <span className="drop-shadow-sm">
                {CHECKPOINT_TYPE_CONFIG[placementType].icon}
              </span>
            </div>
            <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 px-1.5 py-0.5 bg-gray-900 text-white text-[10px] rounded whitespace-nowrap">
              {previewPosition.x.toFixed(1)}%, {previewPosition.y.toFixed(1)}%
            </div>
          </div>
        )}
      </div>

      {/* Details Panel (when checkpoint selected and editing) */}
      {isEditing && selectedCheckpoint && (
        <div className="absolute top-4 right-4 z-40">
          <CheckpointDetailsPanel
            checkpoint={selectedCheckpoint}
            onUpdate={handleCheckpointDetailsUpdate}
            onDelete={handleCheckpointDetailsDelete}
            onClose={handleDetailsPanelClose}
          />
        </div>
      )}
    </div>
  );
}

export default CheckpointManager;
