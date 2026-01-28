/**
 * MarkerPropertiesModal Component
 *
 * Modal for editing marker properties on floor plans.
 * Supports creating new markers and editing existing ones.
 */

import { useState, useEffect, useCallback } from 'react';
import { Modal } from '../ui/Modal';
import type { FloorKeyLocation, LocationMarkerType } from '../../types';

interface MarkerPropertiesModalProps {
  marker: FloorKeyLocation | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (marker: FloorKeyLocation) => void;
  onDelete?: (markerId: string) => void;
}

interface FormErrors {
  name?: string;
  type?: string;
}

// Grouped marker type options for the dropdown
const MARKER_TYPE_OPTIONS = {
  'Fire Equipment': [
    { value: 'fire_extinguisher', label: 'Fire Extinguisher' },
    { value: 'fire_hose', label: 'Fire Hose' },
    { value: 'alarm_pull', label: 'Alarm Pull Station' },
    { value: 'fire_alarm', label: 'Fire Alarm Pull' },
    { value: 'sprinkler_control', label: 'Sprinkler Control' },
  ],
  'Access': [
    { value: 'stairwell', label: 'Stairwell' },
    { value: 'elevator', label: 'Elevator' },
    { value: 'emergency_exit', label: 'Emergency Exit' },
    { value: 'roof_access', label: 'Roof Access' },
  ],
  'Utilities': [
    { value: 'electrical_panel', label: 'Electrical Panel' },
    { value: 'gas_shutoff', label: 'Gas Shutoff' },
    { value: 'water_shutoff', label: 'Water Shutoff' },
  ],
  'Hazards': [
    { value: 'hazmat', label: 'Hazmat' },
    { value: 'hazard', label: 'Hazard' },
    { value: 'confined_space', label: 'Confined Space' },
    { value: 'high_voltage', label: 'High Voltage' },
  ],
  'Medical': [
    { value: 'aed', label: 'AED' },
    { value: 'first_aid', label: 'First Aid Kit' },
    { value: 'eyewash', label: 'Eyewash Station' },
  ],
} as const;

export function MarkerPropertiesModal({
  marker,
  isOpen,
  onClose,
  onSave,
  onDelete,
}: MarkerPropertiesModalProps) {
  // Form state
  const [name, setName] = useState('');
  const [type, setType] = useState<LocationMarkerType | string>('fire_extinguisher');
  const [description, setDescription] = useState('');
  const [notes, setNotes] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Determine if editing existing marker or creating new
  const isEditing = marker?.id !== undefined && marker.id !== '';

  // Reset form when marker changes
  useEffect(() => {
    if (marker) {
      setName(marker.name || '');
      setType(marker.type || 'fire_extinguisher');
      setDescription(marker.description || '');
      setNotes(marker.notes || '');
    } else {
      // Reset to defaults for new marker
      setName('');
      setType('fire_extinguisher');
      setDescription('');
      setNotes('');
    }
    setErrors({});
    setShowDeleteConfirm(false);
  }, [marker, isOpen]);

  // Validate form
  const validate = useCallback((): boolean => {
    const newErrors: FormErrors = {};

    if (!name.trim()) {
      newErrors.name = 'Name is required';
    }

    if (!type) {
      newErrors.type = 'Type is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [name, type]);

  // Handle save
  const handleSave = useCallback(() => {
    if (!validate()) {
      return;
    }

    const updatedMarker: FloorKeyLocation = {
      ...marker,
      name: name.trim(),
      type: type as LocationMarkerType,
      description: description.trim() || undefined,
      notes: notes.trim() || undefined,
      updatedAt: new Date().toISOString(),
    };

    // Set createdAt for new markers
    if (!isEditing) {
      updatedMarker.createdAt = new Date().toISOString();
    }

    onSave(updatedMarker);
  }, [marker, name, type, description, notes, isEditing, validate, onSave]);

  // Handle delete
  const handleDelete = useCallback(() => {
    if (marker?.id && onDelete) {
      onDelete(marker.id);
      setShowDeleteConfirm(false);
    }
  }, [marker, onDelete]);

  // Handle close
  const handleClose = useCallback(() => {
    setShowDeleteConfirm(false);
    onClose();
  }, [onClose]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={isEditing ? 'Edit Marker' : 'New Marker'}
      size="md"
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSave();
        }}
        className="space-y-4"
      >
        {/* Name field */}
        <div>
          <label
            htmlFor="marker-name"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Name <span className="text-red-500">*</span>
          </label>
          <input
            id="marker-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={`
              w-full px-3 py-2 border rounded-md shadow-sm
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
              ${errors.name ? 'border-red-500' : 'border-gray-300'}
            `}
            placeholder="Enter marker name"
            autoFocus
          />
          {errors.name && (
            <p className="mt-1 text-sm text-red-600">{errors.name}</p>
          )}
        </div>

        {/* Type field */}
        <div>
          <label
            htmlFor="marker-type"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Type <span className="text-red-500">*</span>
          </label>
          <select
            id="marker-type"
            value={type}
            onChange={(e) => setType(e.target.value as LocationMarkerType)}
            className={`
              w-full px-3 py-2 border rounded-md shadow-sm
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
              ${errors.type ? 'border-red-500' : 'border-gray-300'}
            `}
          >
            {Object.entries(MARKER_TYPE_OPTIONS).map(([groupLabel, options]) => (
              <optgroup key={groupLabel} label={groupLabel}>
                {options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
          {errors.type && (
            <p className="mt-1 text-sm text-red-600">{errors.type}</p>
          )}
        </div>

        {/* Description field */}
        <div>
          <label
            htmlFor="marker-description"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Description
          </label>
          <textarea
            id="marker-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="
              w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
              resize-none
            "
            placeholder="Enter description (optional)"
          />
        </div>

        {/* Notes field */}
        <div>
          <label
            htmlFor="marker-notes"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Notes
          </label>
          <textarea
            id="marker-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="
              w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
              resize-none
            "
            placeholder="Enter notes (optional)"
          />
        </div>

        {/* Delete confirmation */}
        {showDeleteConfirm && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-sm text-red-700 mb-3">
              Are you sure you want to delete this marker? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(false)}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDelete}
                className="px-3 py-1.5 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                Delete
              </button>
            </div>
          </div>
        )}

        {/* Footer buttons */}
        <div className="flex justify-between pt-4 border-t border-gray-200">
          <div>
            {isEditing && onDelete && !showDeleteConfirm && (
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(true)}
                className="px-4 py-2 text-sm font-medium text-red-600 bg-white border border-red-300 rounded-md hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                Delete
              </button>
            )}
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Save
            </button>
          </div>
        </div>
      </form>
    </Modal>
  );
}

export default MarkerPropertiesModal;
