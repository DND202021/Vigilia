/**
 * BuildingEditModal Component
 * Modal for editing building information including basic info, characteristics,
 * safety features, access info, and contacts.
 */

import { useState, useEffect } from 'react';
import { Button, Badge } from '../ui';
import { cn } from '../../utils';
import { buildingsApi } from '../../services/api';
import { toast } from '../../stores/toastStore';
import type {
  Building,
  BuildingUpdateRequest,
  BuildingType,
  HazardLevel,
  OccupancyType,
  ConstructionType
} from '../../types';

interface BuildingEditModalProps {
  building: Building;
  isOpen: boolean;
  onClose: () => void;
  onSaved: (building: Building) => void;
}

type TabId = 'basic' | 'characteristics' | 'safety' | 'access' | 'contacts' | 'notes';

const buildingTypes: { value: BuildingType; label: string }[] = [
  { value: 'residential_single', label: 'Residential (Single)' },
  { value: 'residential_multi', label: 'Residential (Multi)' },
  { value: 'commercial', label: 'Commercial' },
  { value: 'industrial', label: 'Industrial' },
  { value: 'institutional', label: 'Institutional' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'educational', label: 'Educational' },
  { value: 'government', label: 'Government' },
  { value: 'religious', label: 'Religious' },
  { value: 'mixed_use', label: 'Mixed Use' },
  { value: 'parking', label: 'Parking' },
  { value: 'warehouse', label: 'Warehouse' },
  { value: 'high_rise', label: 'High Rise' },
  { value: 'other', label: 'Other' },
];

const hazardLevels: { value: HazardLevel; label: string; color: string }[] = [
  { value: 'low', label: 'Low', color: 'bg-green-100 text-green-700' },
  { value: 'moderate', label: 'Moderate', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'high', label: 'High', color: 'bg-orange-100 text-orange-700' },
  { value: 'extreme', label: 'Extreme', color: 'bg-red-100 text-red-700' },
];

const occupancyTypes: { value: OccupancyType; label: string }[] = [
  { value: 'assembly', label: 'Assembly' },
  { value: 'business', label: 'Business' },
  { value: 'educational', label: 'Educational' },
  { value: 'factory', label: 'Factory' },
  { value: 'high_hazard', label: 'High Hazard' },
  { value: 'institutional', label: 'Institutional' },
  { value: 'mercantile', label: 'Mercantile' },
  { value: 'residential', label: 'Residential' },
  { value: 'storage', label: 'Storage' },
  { value: 'utility', label: 'Utility' },
];

const constructionTypes: { value: ConstructionType; label: string }[] = [
  { value: 'type_i', label: 'Type I (Fire Resistive)' },
  { value: 'type_ii', label: 'Type II (Non-Combustible)' },
  { value: 'type_iii', label: 'Type III (Ordinary)' },
  { value: 'type_iv', label: 'Type IV (Heavy Timber)' },
  { value: 'type_v', label: 'Type V (Wood Frame)' },
  { value: 'unknown', label: 'Unknown' },
];

export function BuildingEditModal({ building, isOpen, onClose, onSaved }: BuildingEditModalProps) {
  const [activeTab, setActiveTab] = useState<TabId>('basic');
  const [isSaving, setIsSaving] = useState(false);
  const [formData, setFormData] = useState<BuildingUpdateRequest>({});
  const [hasChanges, setHasChanges] = useState(false);

  // Initialize form data from building
  useEffect(() => {
    if (isOpen && building) {
      setFormData({
        name: building.name,
        civic_number: building.civic_number,
        street_name: building.street_name,
        street_type: building.street_type,
        unit_number: building.unit_number,
        city: building.city,
        province_state: building.province_state,
        postal_code: building.postal_code,
        country: building.country,
        latitude: building.latitude,
        longitude: building.longitude,
        building_type: building.building_type,
        occupancy_type: building.occupancy_type,
        construction_type: building.construction_type,
        year_built: building.year_built,
        year_renovated: building.year_renovated,
        total_floors: building.total_floors,
        basement_levels: building.basement_levels,
        total_area_sqm: building.total_area_sqm,
        building_height_m: building.building_height_m,
        max_occupancy: building.max_occupancy,
        hazard_level: building.hazard_level,
        has_sprinkler_system: building.has_sprinkler_system,
        has_fire_alarm: building.has_fire_alarm,
        has_standpipe: building.has_standpipe,
        has_elevator: building.has_elevator,
        elevator_count: building.elevator_count,
        has_generator: building.has_generator,
        has_hazmat: building.has_hazmat,
        knox_box: building.knox_box,
        primary_entrance: building.primary_entrance,
        staging_area: building.staging_area,
        key_box_location: building.key_box_location,
        roof_access: building.roof_access,
        owner_name: building.owner_name,
        owner_phone: building.owner_phone,
        owner_email: building.owner_email,
        manager_name: building.manager_name,
        manager_phone: building.manager_phone,
        emergency_contact_name: building.emergency_contact_name,
        emergency_contact_phone: building.emergency_contact_phone,
        special_needs_occupants: building.special_needs_occupants,
        special_needs_details: building.special_needs_details,
        animals_present: building.animals_present,
        animals_details: building.animals_details,
        tactical_notes: building.tactical_notes,
      });
      setHasChanges(false);
      setActiveTab('basic');
    }
  }, [isOpen, building]);

  const updateField = <K extends keyof BuildingUpdateRequest>(
    field: K,
    value: BuildingUpdateRequest[K]
  ) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Only send changed fields
      const updates: BuildingUpdateRequest = {};
      for (const [key, value] of Object.entries(formData)) {
        const originalValue = building[key as keyof Building];
        if (value !== originalValue) {
          (updates as any)[key] = value;
        }
      }

      if (Object.keys(updates).length === 0) {
        toast.info('No changes to save');
        onClose();
        return;
      }

      const updatedBuilding = await buildingsApi.update(building.id, updates);
      toast.success('Building updated successfully');
      onSaved(updatedBuilding);
      onClose();
    } catch (error) {
      console.error('Failed to update building:', error);
      toast.error('Failed to update building');
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  const tabs: { id: TabId; label: string }[] = [
    { id: 'basic', label: 'Basic Info' },
    { id: 'characteristics', label: 'Characteristics' },
    { id: 'safety', label: 'Safety' },
    { id: 'access', label: 'Access' },
    { id: 'contacts', label: 'Contacts' },
    { id: 'notes', label: 'Notes' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={() => !isSaving && onClose()}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Edit Building</h2>
            <p className="text-sm text-gray-500">{building.name}</p>
          </div>
          <button
            onClick={onClose}
            disabled={isSaving}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b px-4 overflow-x-auto">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px whitespace-nowrap',
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === 'basic' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Building Name *</label>
                <input
                  type="text"
                  value={formData.name || ''}
                  onChange={e => updateField('name', e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Civic Number</label>
                  <input
                    type="text"
                    value={formData.civic_number || ''}
                    onChange={e => updateField('civic_number', e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Unit Number</label>
                  <input
                    type="text"
                    value={formData.unit_number || ''}
                    onChange={e => updateField('unit_number', e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Street Name</label>
                  <input
                    type="text"
                    value={formData.street_name || ''}
                    onChange={e => updateField('street_name', e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Street Type</label>
                  <input
                    type="text"
                    value={formData.street_type || ''}
                    onChange={e => updateField('street_type', e.target.value)}
                    placeholder="e.g., Street, Avenue, Boulevard"
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
                  <input
                    type="text"
                    value={formData.city || ''}
                    onChange={e => updateField('city', e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Province/State</label>
                  <input
                    type="text"
                    value={formData.province_state || ''}
                    onChange={e => updateField('province_state', e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Postal Code</label>
                  <input
                    type="text"
                    value={formData.postal_code || ''}
                    onChange={e => updateField('postal_code', e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Latitude</label>
                  <input
                    type="number"
                    step="any"
                    value={formData.latitude ?? ''}
                    onChange={e => updateField('latitude', e.target.value ? parseFloat(e.target.value) : undefined)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Longitude</label>
                  <input
                    type="number"
                    step="any"
                    value={formData.longitude ?? ''}
                    onChange={e => updateField('longitude', e.target.value ? parseFloat(e.target.value) : undefined)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'characteristics' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Building Type</label>
                  <select
                    value={formData.building_type || ''}
                    onChange={e => updateField('building_type', e.target.value as BuildingType)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    {buildingTypes.map(t => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Occupancy Type</label>
                  <select
                    value={formData.occupancy_type || ''}
                    onChange={e => updateField('occupancy_type', e.target.value as OccupancyType)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select...</option>
                    {occupancyTypes.map(t => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Construction Type</label>
                <select
                  value={formData.construction_type || ''}
                  onChange={e => updateField('construction_type', e.target.value as ConstructionType)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  {constructionTypes.map(t => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Year Built</label>
                  <input
                    type="number"
                    value={formData.year_built ?? ''}
                    onChange={e => updateField('year_built', e.target.value ? parseInt(e.target.value) : undefined)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Year Renovated</label>
                  <input
                    type="number"
                    value={formData.year_renovated ?? ''}
                    onChange={e => updateField('year_renovated', e.target.value ? parseInt(e.target.value) : undefined)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Max Occupancy</label>
                  <input
                    type="number"
                    value={formData.max_occupancy ?? ''}
                    onChange={e => updateField('max_occupancy', e.target.value ? parseInt(e.target.value) : undefined)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Total Floors</label>
                  <input
                    type="number"
                    value={formData.total_floors ?? ''}
                    onChange={e => updateField('total_floors', e.target.value ? parseInt(e.target.value) : undefined)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Basement Levels</label>
                  <input
                    type="number"
                    value={formData.basement_levels ?? ''}
                    onChange={e => updateField('basement_levels', e.target.value ? parseInt(e.target.value) : undefined)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Total Area (sqm)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.total_area_sqm ?? ''}
                    onChange={e => updateField('total_area_sqm', e.target.value ? parseFloat(e.target.value) : undefined)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Building Height (m)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.building_height_m ?? ''}
                    onChange={e => updateField('building_height_m', e.target.value ? parseFloat(e.target.value) : undefined)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'safety' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Hazard Level</label>
                <div className="flex gap-2">
                  {hazardLevels.map(level => (
                    <button
                      key={level.value}
                      type="button"
                      onClick={() => updateField('hazard_level', level.value)}
                      className={cn(
                        'px-4 py-2 rounded-lg text-sm font-medium transition-all',
                        formData.hazard_level === level.value
                          ? level.color + ' ring-2 ring-offset-2 ring-blue-500'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      )}
                    >
                      {level.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Safety Features</label>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { field: 'has_sprinkler_system', label: 'Sprinkler System' },
                    { field: 'has_fire_alarm', label: 'Fire Alarm' },
                    { field: 'has_standpipe', label: 'Standpipe' },
                    { field: 'has_generator', label: 'Generator' },
                    { field: 'knox_box', label: 'Knox Box' },
                    { field: 'has_hazmat', label: 'HAZMAT Present' },
                  ].map(({ field, label }) => (
                    <label key={field} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={!!formData[field as keyof BuildingUpdateRequest]}
                        onChange={e => updateField(field as keyof BuildingUpdateRequest, e.target.checked)}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-700">{label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!!formData.has_elevator}
                    onChange={e => updateField('has_elevator', e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">Has Elevator</span>
                </label>
                {formData.has_elevator && (
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-gray-500">Count:</label>
                    <input
                      type="number"
                      min="1"
                      value={formData.elevator_count ?? 1}
                      onChange={e => updateField('elevator_count', parseInt(e.target.value) || 1)}
                      className="w-16 px-2 py-1 border rounded focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                )}
              </div>

              <div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!!formData.special_needs_occupants}
                    onChange={e => updateField('special_needs_occupants', e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">Special Needs Occupants</span>
                </label>
                {formData.special_needs_occupants && (
                  <textarea
                    value={formData.special_needs_details || ''}
                    onChange={e => updateField('special_needs_details', e.target.value)}
                    placeholder="Describe special needs..."
                    className="mt-2 w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    rows={2}
                  />
                )}
              </div>

              <div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!!formData.animals_present}
                    onChange={e => updateField('animals_present', e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">Animals Present</span>
                </label>
                {formData.animals_present && (
                  <textarea
                    value={formData.animals_details || ''}
                    onChange={e => updateField('animals_details', e.target.value)}
                    placeholder="Describe animals (type, count, location)..."
                    className="mt-2 w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    rows={2}
                  />
                )}
              </div>
            </div>
          )}

          {activeTab === 'access' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Primary Entrance</label>
                <input
                  type="text"
                  value={formData.primary_entrance || ''}
                  onChange={e => updateField('primary_entrance', e.target.value)}
                  placeholder="e.g., Front door on Main Street"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Staging Area</label>
                <input
                  type="text"
                  value={formData.staging_area || ''}
                  onChange={e => updateField('staging_area', e.target.value)}
                  placeholder="e.g., Parking lot on west side"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Key Box Location</label>
                <input
                  type="text"
                  value={formData.key_box_location || ''}
                  onChange={e => updateField('key_box_location', e.target.value)}
                  placeholder="e.g., Left of main entrance"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Roof Access</label>
                <input
                  type="text"
                  value={formData.roof_access || ''}
                  onChange={e => updateField('roof_access', e.target.value)}
                  placeholder="e.g., Stairwell on east side, requires key"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          )}

          {activeTab === 'contacts' && (
            <div className="space-y-4">
              <div className="p-3 bg-gray-50 rounded-lg">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Building Owner</h4>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Name</label>
                    <input
                      type="text"
                      value={formData.owner_name || ''}
                      onChange={e => updateField('owner_name', e.target.value)}
                      className="w-full px-2 py-1.5 text-sm border rounded focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Phone</label>
                    <input
                      type="tel"
                      value={formData.owner_phone || ''}
                      onChange={e => updateField('owner_phone', e.target.value)}
                      className="w-full px-2 py-1.5 text-sm border rounded focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Email</label>
                    <input
                      type="email"
                      value={formData.owner_email || ''}
                      onChange={e => updateField('owner_email', e.target.value)}
                      className="w-full px-2 py-1.5 text-sm border rounded focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>

              <div className="p-3 bg-gray-50 rounded-lg">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Building Manager</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Name</label>
                    <input
                      type="text"
                      value={formData.manager_name || ''}
                      onChange={e => updateField('manager_name', e.target.value)}
                      className="w-full px-2 py-1.5 text-sm border rounded focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Phone</label>
                    <input
                      type="tel"
                      value={formData.manager_phone || ''}
                      onChange={e => updateField('manager_phone', e.target.value)}
                      className="w-full px-2 py-1.5 text-sm border rounded focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>

              <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                <h4 className="text-sm font-medium text-yellow-800 mb-3">Emergency Contact</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-yellow-700 mb-1">Name</label>
                    <input
                      type="text"
                      value={formData.emergency_contact_name || ''}
                      onChange={e => updateField('emergency_contact_name', e.target.value)}
                      className="w-full px-2 py-1.5 text-sm border border-yellow-300 rounded focus:ring-2 focus:ring-yellow-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-yellow-700 mb-1">Phone</label>
                    <input
                      type="tel"
                      value={formData.emergency_contact_phone || ''}
                      onChange={e => updateField('emergency_contact_phone', e.target.value)}
                      className="w-full px-2 py-1.5 text-sm border border-yellow-300 rounded focus:ring-2 focus:ring-yellow-500"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'notes' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tactical Notes</label>
                <p className="text-xs text-gray-500 mb-2">
                  Important information for first responders (hazards, access points, special considerations)
                </p>
                <textarea
                  value={formData.tactical_notes || ''}
                  onChange={e => updateField('tactical_notes', e.target.value)}
                  rows={10}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter tactical notes..."
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t bg-gray-50">
          <div>
            {hasChanges && (
              <Badge className="bg-yellow-100 text-yellow-700">Unsaved changes</Badge>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={onClose} disabled={isSaving}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={isSaving || !hasChanges}>
              {isSaving ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BuildingEditModal;
