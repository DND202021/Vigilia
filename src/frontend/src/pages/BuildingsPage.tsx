/**
 * Buildings Page - Building Information Management
 */

import { useEffect, useState, useCallback } from 'react';
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
import { FloorPlanViewer, FloorPlanUpload } from '../components/buildings';
import { cn } from '../utils';
import type {
  Building,
  BuildingType,
  BuildingCreateRequest,
  BuildingStats,
  HazardLevel,
  FloorPlan,
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
  const [selectedBuilding, setSelectedBuilding] = useState<Building | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

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

  const handleVerifyBuilding = async (id: string) => {
    try {
      await buildingsApi.verify(id);
      fetchBuildings();
      if (selectedBuilding?.id === id) {
        const updated = await buildingsApi.get(id);
        setSelectedBuilding(updated);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to verify building');
    }
  };

  const openBuildingDetail = (building: Building) => {
    setSelectedBuilding(building);
    setIsDetailModalOpen(true);
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

      {/* Detail Modal */}
      {selectedBuilding && (
        <BuildingDetailModal
          isOpen={isDetailModalOpen}
          onClose={() => setIsDetailModalOpen(false)}
          building={selectedBuilding}
          onVerify={handleVerifyBuilding}
        />
      )}
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

interface BuildingDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  building: Building;
  onVerify: (id: string) => Promise<void>;
}

type DetailTab = 'info' | 'floors' | 'upload';

function BuildingDetailModal({ isOpen, onClose, building, onVerify }: BuildingDetailModalProps) {
  const [floorPlans, setFloorPlans] = useState<FloorPlan[]>([]);
  const [isLoadingFloors, setIsLoadingFloors] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [activeTab, setActiveTab] = useState<DetailTab>('info');
  const [selectedFloor, setSelectedFloor] = useState<FloorPlan | null>(null);

  useEffect(() => {
    if (isOpen && building) {
      loadFloorPlans();
      setActiveTab('info');
      setSelectedFloor(null);
    }
  }, [isOpen, building]);

  const loadFloorPlans = useCallback(async () => {
    setIsLoadingFloors(true);
    try {
      const plans = await buildingsApi.getFloorPlans(building.id);
      setFloorPlans(plans);
      if (plans.length > 0 && !selectedFloor) {
        setSelectedFloor(plans[0]);
      }
    } catch (err) {
      console.error('Failed to load floor plans:', err);
    } finally {
      setIsLoadingFloors(false);
    }
  }, [building.id, selectedFloor]);

  const handleVerify = async () => {
    setIsVerifying(true);
    try {
      await onVerify(building.id);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleUploadComplete = useCallback((newFloorPlan: FloorPlan) => {
    setFloorPlans((prev) => [...prev, newFloorPlan].sort((a, b) => a.floor_number - b.floor_number));
    setSelectedFloor(newFloorPlan);
    setActiveTab('floors');
  }, []);

  const hazardStyle = hazardLevelConfig[building.hazard_level];
  const typeLabel = buildingTypeOptions.find((t) => t.value === building.building_type)?.label || building.building_type;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={building.name}>
      <div className="flex flex-col h-[70vh]">
        {/* Header Info */}
        <div className="flex items-start justify-between pb-4 border-b">
          <div>
            <p className="text-gray-600">{building.full_address}</p>
            <div className="flex gap-2 mt-2">
              <Badge variant="secondary">{typeLabel}</Badge>
              <Badge className={cn(hazardStyle.bgColor, hazardStyle.color)}>
                {building.hazard_level} hazard
              </Badge>
              {building.is_verified ? (
                <Badge className="bg-green-100 text-green-700">Verified</Badge>
              ) : (
                <Badge variant="secondary">Unverified</Badge>
              )}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b mt-4">
          <button
            onClick={() => setActiveTab('info')}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === 'info'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            )}
          >
            Building Info
          </button>
          <button
            onClick={() => setActiveTab('floors')}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === 'floors'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            )}
          >
            Floor Plans ({floorPlans.length})
          </button>
          <button
            onClick={() => setActiveTab('upload')}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === 'upload'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            )}
          >
            Upload Plan
          </button>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-auto py-4">
          {activeTab === 'info' && (
            <div className="space-y-6">
              {/* Building Specs */}
              <div className="grid grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
                <div>
                  <p className="text-xs text-gray-500">Floors</p>
                  <p className="font-semibold">{building.total_floors}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Basements</p>
                  <p className="font-semibold">{building.basement_levels}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Year Built</p>
                  <p className="font-semibold">{building.year_built || 'Unknown'}</p>
                </div>
              </div>

              {/* Safety Features */}
              <div>
                <h4 className="font-semibold mb-2">Safety Features</h4>
                <div className="flex flex-wrap gap-2">
                  {building.has_sprinkler_system && (
                    <Badge className="bg-blue-100 text-blue-700">Sprinkler System</Badge>
                  )}
                  {building.has_fire_alarm && (
                    <Badge className="bg-blue-100 text-blue-700">Fire Alarm</Badge>
                  )}
                  {building.has_standpipe && (
                    <Badge className="bg-blue-100 text-blue-700">Standpipe</Badge>
                  )}
                  {building.has_elevator && (
                    <Badge className="bg-blue-100 text-blue-700">Elevator ({building.elevator_count || 1})</Badge>
                  )}
                  {building.has_generator && (
                    <Badge className="bg-blue-100 text-blue-700">Generator</Badge>
                  )}
                  {building.knox_box && (
                    <Badge className="bg-blue-100 text-blue-700">Knox Box</Badge>
                  )}
                  {building.has_hazmat && (
                    <Badge className="bg-red-100 text-red-700">HAZMAT Present</Badge>
                  )}
                  {!building.has_sprinkler_system && !building.has_fire_alarm && !building.has_standpipe &&
                   !building.has_elevator && !building.has_generator && !building.knox_box && !building.has_hazmat && (
                    <span className="text-sm text-gray-500">No safety features recorded</span>
                  )}
                </div>
              </div>

              {/* Access Information */}
              {(building.primary_entrance || building.staging_area || building.key_box_location) && (
                <div>
                  <h4 className="font-semibold mb-2">Access Information</h4>
                  <div className="space-y-2 text-sm">
                    {building.primary_entrance && (
                      <p><span className="text-gray-500">Primary Entrance:</span> {building.primary_entrance}</p>
                    )}
                    {building.staging_area && (
                      <p><span className="text-gray-500">Staging Area:</span> {building.staging_area}</p>
                    )}
                    {building.key_box_location && (
                      <p><span className="text-gray-500">Key Box:</span> {building.key_box_location}</p>
                    )}
                  </div>
                </div>
              )}

              {/* Emergency Contacts */}
              {(building.emergency_contact_name || building.owner_name) && (
                <div>
                  <h4 className="font-semibold mb-2">Contacts</h4>
                  <div className="space-y-2 text-sm">
                    {building.emergency_contact_name && (
                      <p>
                        <span className="text-gray-500">Emergency:</span> {building.emergency_contact_name}
                        {building.emergency_contact_phone && ` - ${building.emergency_contact_phone}`}
                      </p>
                    )}
                    {building.owner_name && (
                      <p>
                        <span className="text-gray-500">Owner:</span> {building.owner_name}
                        {building.owner_phone && ` - ${building.owner_phone}`}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Tactical Notes */}
              {building.tactical_notes && (
                <div>
                  <h4 className="font-semibold mb-2">Tactical Notes</h4>
                  <p className="text-sm text-gray-700 bg-yellow-50 p-3 rounded">{building.tactical_notes}</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'floors' && (
            <div className="h-full flex flex-col">
              {isLoadingFloors ? (
                <div className="flex-1 flex items-center justify-center">
                  <Spinner size="lg" />
                </div>
              ) : floorPlans.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-gray-500">
                  <svg className="w-16 h-16 mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                  </svg>
                  <p>No floor plans uploaded yet</p>
                  <Button className="mt-4" onClick={() => setActiveTab('upload')}>
                    Upload Floor Plan
                  </Button>
                </div>
              ) : (
                <div className="flex flex-col h-full">
                  {/* Floor selector */}
                  <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
                    {floorPlans.map((plan) => (
                      <button
                        key={plan.id}
                        onClick={() => setSelectedFloor(plan)}
                        className={cn(
                          'px-3 py-1.5 text-sm rounded-lg whitespace-nowrap transition-colors',
                          selectedFloor?.id === plan.id
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        )}
                      >
                        {plan.floor_name || `Floor ${plan.floor_number}`}
                      </button>
                    ))}
                  </div>

                  {/* Floor plan viewer */}
                  {selectedFloor && (
                    <div className="flex-1 border rounded-lg overflow-hidden">
                      <FloorPlanViewer
                        floorPlan={selectedFloor}
                        keyLocations={selectedFloor.key_locations || []}
                        emergencyExits={selectedFloor.emergency_exits || []}
                        fireEquipment={selectedFloor.fire_equipment || []}
                        hazards={selectedFloor.hazards || []}
                        showControls={true}
                        showLegend={true}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === 'upload' && (
            <FloorPlanUpload
              buildingId={building.id}
              totalFloors={building.total_floors}
              basementLevels={building.basement_levels}
              existingFloorPlans={floorPlans}
              onUploadComplete={handleUploadComplete}
            />
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          {!building.is_verified && (
            <Button onClick={handleVerify} isLoading={isVerifying}>
              Verify Building
            </Button>
          )}
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
}
