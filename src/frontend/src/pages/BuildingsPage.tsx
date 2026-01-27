/**
 * Buildings Page - Building Information Management
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { buildingsApi } from '../services/api';
import {
  Card,
  CardContent,
  Badge,
  Button,
  Select,
  Modal,
  Input,
  Spinner,
} from '../components/ui';
import { cn } from '../utils';
import type {
  Building,
  BuildingType,
  BuildingCreateRequest,
  BuildingStats,
  HazardLevel,
} from '../types';

const buildingTypeOptions = [
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

const hazardLevelOptions = [
  { value: 'low', label: 'Low' },
  { value: 'moderate', label: 'Moderate' },
  { value: 'high', label: 'High' },
  { value: 'extreme', label: 'Extreme' },
];

const typeFilterOptions = [
  { value: '', label: 'All Types' },
  ...buildingTypeOptions,
];

const hazardLevelConfig: Record<HazardLevel, { color: string; bgColor: string }> = {
  low: { color: 'text-green-700', bgColor: 'bg-green-100' },
  moderate: { color: 'text-yellow-700', bgColor: 'bg-yellow-100' },
  high: { color: 'text-orange-700', bgColor: 'bg-orange-100' },
  extreme: { color: 'text-red-700', bgColor: 'bg-red-100' },
};

export function BuildingsPage() {
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [stats, setStats] = useState<BuildingStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const navigate = useNavigate();

  const fetchBuildings = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, unknown> = {};
      if (typeFilter) params.building_type = typeFilter;
      if (searchQuery) params.search = searchQuery;
      params.page_size = 100;

      const response = await buildingsApi.list(params);
      setBuildings(response.items);

      const statsResponse = await buildingsApi.getStats();
      setStats(statsResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch buildings');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBuildings();
  }, [typeFilter]);

  const handleSearch = () => {
    fetchBuildings();
  };

  const handleCreateBuilding = async (data: BuildingCreateRequest) => {
    try {
      await buildingsApi.create(data);
      fetchBuildings();
      setIsCreateModalOpen(false);
    } catch (err) {
      throw err;
    }
  };

  const openBuildingDetail = (building: Building) => {
    navigate(`/buildings/${building.id}`);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Buildings</h1>
          <p className="mt-1 text-gray-500">Pre-incident building information for emergency response</p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)}>Add Building</Button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard label="Total Buildings" count={stats.total} color="blue" />
          <StatCard label="Verified" count={stats.verified} color="green" />
          <StatCard label="With Hazmat" count={stats.with_hazmat} color="orange" />
          <StatCard label="High Rise" count={stats.high_rise} color="purple" />
        </div>
      )}

      {/* Search and Filters */}
      <div className="flex gap-4 mb-6">
        <div className="flex-1">
          <div className="flex gap-2">
            <Input
              placeholder="Search by name or address..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
            <Button onClick={handleSearch}>Search</Button>
          </div>
        </div>
        <div className="w-48">
          <Select
            options={typeFilterOptions}
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          />
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between">
          <span className="text-red-700">{error}</span>
          <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">
            Dismiss
          </button>
        </div>
      )}

      {/* Buildings List */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : buildings.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12 text-gray-500">
            No buildings found
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {buildings.map((building) => (
            <BuildingCard
              key={building.id}
              building={building}
              onClick={() => openBuildingDetail(building)}
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      <CreateBuildingModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreateBuilding}
      />

    </div>
  );
}

interface StatCardProps {
  label: string;
  count: number;
  color: 'green' | 'blue' | 'purple' | 'orange';
}

function StatCard({ label, count, color }: StatCardProps) {
  const colorStyles = {
    green: 'bg-green-50 text-green-700 border-green-200',
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
    orange: 'bg-orange-50 text-orange-700 border-orange-200',
  };

  return (
    <div className={cn('p-4 rounded-lg border', colorStyles[color])}>
      <p className="text-2xl font-bold">{count}</p>
      <p className="text-sm">{label}</p>
    </div>
  );
}

interface BuildingCardProps {
  building: Building;
  onClick: () => void;
}

function BuildingCard({ building, onClick }: BuildingCardProps) {
  const hazardStyle = hazardLevelConfig[building.hazard_level];
  const typeLabel = buildingTypeOptions.find((t) => t.value === building.building_type)?.label || building.building_type;

  return (
    <div
      className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="font-semibold text-gray-900">{building.name}</h3>
          <p className="text-sm text-gray-500">{building.full_address}</p>
        </div>
        <Badge className={cn(hazardStyle.bgColor, hazardStyle.color)}>
          {building.hazard_level}
        </Badge>
      </div>

      <div className="flex flex-wrap gap-2 mt-3">
        <Badge variant="secondary" size="sm">{typeLabel}</Badge>
        <Badge variant="secondary" size="sm">{building.total_floors} floors</Badge>
        {building.has_hazmat && (
          <Badge className="bg-red-100 text-red-700" size="sm">HAZMAT</Badge>
        )}
        {building.has_elevator && (
          <Badge variant="secondary" size="sm">Elevator</Badge>
        )}
        {building.has_sprinkler_system && (
          <Badge variant="secondary" size="sm">Sprinkler</Badge>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-gray-400">
        <span>{building.city}, {building.province_state}</span>
        {building.is_verified ? (
          <Badge className="bg-green-100 text-green-700" size="sm">Verified</Badge>
        ) : (
          <Badge variant="secondary" size="sm">Unverified</Badge>
        )}
      </div>
    </div>
  );
}

interface CreateBuildingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (data: BuildingCreateRequest) => Promise<void>;
}

function CreateBuildingModal({ isOpen, onClose, onCreate }: CreateBuildingModalProps) {
  const [formData, setFormData] = useState<BuildingCreateRequest>({
    name: '',
    street_name: '',
    city: '',
    province_state: 'Quebec',
    latitude: 45.5017,
    longitude: -73.5673,
    building_type: 'other',
    hazard_level: 'low',
    total_floors: 1,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!formData.name || !formData.street_name || !formData.city) {
      setError('Name, street name, and city are required');
      return;
    }

    setIsSubmitting(true);
    try {
      await onCreate(formData);
      setFormData({
        name: '',
        street_name: '',
        city: '',
        province_state: 'Quebec',
        latitude: 45.5017,
        longitude: -73.5673,
        building_type: 'other',
        hazard_level: 'low',
        total_floors: 1,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create building');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add New Building">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        <Input
          label="Building Name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="e.g., City Hall, 100 Main Building"
          required
        />

        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Civic Number"
            value={formData.civic_number || ''}
            onChange={(e) => setFormData({ ...formData, civic_number: e.target.value })}
            placeholder="100"
          />
          <Input
            label="Street Name"
            value={formData.street_name}
            onChange={(e) => setFormData({ ...formData, street_name: e.target.value })}
            placeholder="Main Street"
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Input
            label="City"
            value={formData.city}
            onChange={(e) => setFormData({ ...formData, city: e.target.value })}
            placeholder="Montreal"
            required
          />
          <Input
            label="Province/State"
            value={formData.province_state}
            onChange={(e) => setFormData({ ...formData, province_state: e.target.value })}
            placeholder="Quebec"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Latitude"
            type="number"
            step="0.0001"
            value={formData.latitude}
            onChange={(e) => setFormData({ ...formData, latitude: parseFloat(e.target.value) })}
          />
          <Input
            label="Longitude"
            type="number"
            step="0.0001"
            value={formData.longitude}
            onChange={(e) => setFormData({ ...formData, longitude: parseFloat(e.target.value) })}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Select
            label="Building Type"
            options={buildingTypeOptions}
            value={formData.building_type || 'other'}
            onChange={(e) => setFormData({ ...formData, building_type: e.target.value as BuildingType })}
          />
          <Select
            label="Hazard Level"
            options={hazardLevelOptions}
            value={formData.hazard_level || 'low'}
            onChange={(e) => setFormData({ ...formData, hazard_level: e.target.value as HazardLevel })}
          />
        </div>

        <div className="grid grid-cols-3 gap-4">
          <Input
            label="Total Floors"
            type="number"
            min="1"
            value={formData.total_floors || 1}
            onChange={(e) => setFormData({ ...formData, total_floors: parseInt(e.target.value) })}
          />
          <Input
            label="Basement Levels"
            type="number"
            min="0"
            value={formData.basement_levels || 0}
            onChange={(e) => setFormData({ ...formData, basement_levels: parseInt(e.target.value) })}
          />
          <Input
            label="Year Built"
            type="number"
            value={formData.year_built || ''}
            onChange={(e) => setFormData({ ...formData, year_built: e.target.value ? parseInt(e.target.value) : undefined })}
          />
        </div>

        <div className="flex gap-4 py-2">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formData.has_sprinkler_system || false}
              onChange={(e) => setFormData({ ...formData, has_sprinkler_system: e.target.checked })}
            />
            Sprinkler System
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formData.has_fire_alarm || false}
              onChange={(e) => setFormData({ ...formData, has_fire_alarm: e.target.checked })}
            />
            Fire Alarm
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formData.has_elevator || false}
              onChange={(e) => setFormData({ ...formData, has_elevator: e.target.checked })}
            />
            Elevator
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formData.has_hazmat || false}
              onChange={(e) => setFormData({ ...formData, has_hazmat: e.target.checked })}
            />
            Hazmat
          </label>
        </div>

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Add Building
          </Button>
        </div>
      </form>
    </Modal>
  );
}

