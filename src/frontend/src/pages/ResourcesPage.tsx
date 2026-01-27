/**
 * Resources Page
 */

import { useEffect, useState } from 'react';
import { useResourceStore } from '../stores/resourceStore';
import { useAuthStore } from '../stores/authStore';
import { usePolling } from '../hooks/useInterval';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  Button,
  Select,
  Modal,
  Input,
  Spinner,
} from '../components/ui';
import {
  formatRelativeTime,
  getResourceStatusLabel,
  resourceStatusConfig,
  cn,
} from '../utils';
import type { Resource, ResourceStatus, ResourceType, ResourceCreateRequest } from '../types';

const POLL_INTERVAL = 15000;

const resourceTypeOptions = [
  { value: 'personnel', label: 'Personnel' },
  { value: 'vehicle', label: 'Vehicle' },
  { value: 'equipment', label: 'Equipment' },
];

const statusOptions = [
  { value: 'available', label: 'Available' },
  { value: 'dispatched', label: 'Dispatched' },
  { value: 'en_route', label: 'En Route' },
  { value: 'on_scene', label: 'On Scene' },
  { value: 'out_of_service', label: 'Out of Service' },
  { value: 'off_duty', label: 'Off Duty' },
];

const typeFilterOptions = [
  { value: '', label: 'All Types' },
  ...resourceTypeOptions,
];

const statusFilterOptions = [
  { value: '', label: 'All Statuses' },
  ...statusOptions,
];

export function ResourcesPage() {
  const {
    resources,
    fetchResources,
    createResource,
    updateResourceStatus,
    isLoading,
    error,
    clearError,
  } = useResourceStore();

  const { user } = useAuthStore();

  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedResource, setSelectedResource] = useState<Resource | null>(null);
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);

  const fetchWithFilters = () => {
    const params: Record<string, unknown> = {};
    if (typeFilter) params.resource_type = typeFilter;
    if (statusFilter) params.status = statusFilter;
    fetchResources(params);
  };

  usePolling(fetchWithFilters, POLL_INTERVAL);

  useEffect(() => {
    fetchWithFilters();
  }, [typeFilter, statusFilter]);

  const filteredResources = resources.filter((resource) => {
    if (typeFilter && resource.resource_type !== typeFilter) return false;
    if (statusFilter && resource.status !== statusFilter) return false;
    return true;
  });

  // Group resources by type
  const groupedResources = filteredResources.reduce((acc, resource) => {
    const type = resource.resource_type;
    if (!acc[type]) acc[type] = [];
    acc[type].push(resource);
    return acc;
  }, {} as Record<string, Resource[]>);

  const openStatusUpdate = (resource: Resource) => {
    setSelectedResource(resource);
    setIsStatusModalOpen(true);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Resources</h1>
          <p className="mt-1 text-gray-500">Manage personnel, vehicles, and equipment</p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)}>Add Resource</Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Available"
          count={resources.filter((r) => r.status === 'available').length}
          color="green"
        />
        <StatCard
          label="Dispatched"
          count={resources.filter((r) => r.status === 'dispatched').length}
          color="blue"
        />
        <StatCard
          label="On Scene"
          count={resources.filter((r) => r.status === 'on_scene').length}
          color="purple"
        />
        <StatCard
          label="Out of Service"
          count={resources.filter((r) => r.status === 'out_of_service').length}
          color="orange"
        />
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <div className="w-48">
          <Select
            options={typeFilterOptions}
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          />
        </div>
        <div className="w-48">
          <Select
            options={statusFilterOptions}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          />
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between">
          <span className="text-red-700">{error}</span>
          <button onClick={clearError} className="text-red-500 hover:text-red-700">
            Dismiss
          </button>
        </div>
      )}

      {/* Resources */}
      {isLoading && resources.length === 0 ? (
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : filteredResources.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12 text-gray-500">
            No resources found
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedResources).map(([type, typeResources]) => (
            <Card key={type}>
              <CardHeader>
                <CardTitle className="capitalize">
                  {type} ({typeResources.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
                  {typeResources.map((resource) => (
                    <ResourceCard
                      key={resource.id}
                      resource={resource}
                      onUpdateStatus={() => openStatusUpdate(resource)}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Modal */}
      <CreateResourceModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={createResource}
        agencyId={user?.agency_id}
      />

      {/* Status Update Modal */}
      {selectedResource && (
        <UpdateStatusModal
          isOpen={isStatusModalOpen}
          onClose={() => setIsStatusModalOpen(false)}
          resource={selectedResource}
          onUpdate={async (status) => {
            await updateResourceStatus(selectedResource.id, { status });
            setIsStatusModalOpen(false);
          }}
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

interface ResourceCardProps {
  resource: Resource;
  onUpdateStatus: () => void;
}

function ResourceCard({ resource, onUpdateStatus }: ResourceCardProps) {
  const statusStyle = resourceStatusConfig[resource.status];

  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold',
              statusStyle?.bgColor || 'bg-gray-100'
            )}
          >
            {resource.call_sign?.[0] || resource.name[0]}
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">
              {resource.call_sign || resource.name}
            </h3>
            <p className="text-sm text-gray-500">{resource.name}</p>
          </div>
        </div>
        <Badge className={cn(statusStyle?.bgColor, statusStyle?.color)}>
          {getResourceStatusLabel(resource.status)}
        </Badge>
      </div>

      {resource.capabilities && resource.capabilities.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {resource.capabilities.slice(0, 3).map((cap) => (
            <Badge key={cap} variant="secondary" size="sm">
              {cap}
            </Badge>
          ))}
          {resource.capabilities.length > 3 && (
            <Badge variant="secondary" size="sm">
              +{resource.capabilities.length - 3}
            </Badge>
          )}
        </div>
      )}

      {resource.current_incident_id && (
        <div className="mt-3 p-2 bg-blue-50 rounded text-sm text-blue-700">
          Assigned to incident
        </div>
      )}

      <div className="mt-3 flex items-center justify-between text-xs text-gray-400">
        <span>Updated {formatRelativeTime(resource.last_status_update)}</span>
        <Button size="sm" variant="ghost" onClick={onUpdateStatus}>
          Update Status
        </Button>
      </div>
    </div>
  );
}

interface CreateResourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (data: ResourceCreateRequest) => Promise<Resource>;
  agencyId?: string;
}

function CreateResourceModal({ isOpen, onClose, onCreate, agencyId }: CreateResourceModalProps) {
  const [formData, setFormData] = useState<ResourceCreateRequest>({
    resource_type: 'vehicle',
    name: '',
    call_sign: '',
    capabilities: [],
  });
  const [capabilitiesInput, setCapabilitiesInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!formData.name) {
      setError('Name is required');
      return;
    }

    if (!agencyId) {
      setError('You must belong to an agency to create resources');
      return;
    }

    setIsSubmitting(true);
    try {
      const capabilities = capabilitiesInput
        .split(',')
        .map((c) => c.trim())
        .filter(Boolean);

      await onCreate({ ...formData, capabilities, agency_id: agencyId });
      onClose();
      setFormData({
        resource_type: 'vehicle',
        name: '',
        call_sign: '',
        capabilities: [],
      });
      setCapabilitiesInput('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create resource');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add New Resource">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        <Select
          label="Resource Type"
          options={resourceTypeOptions}
          value={formData.resource_type}
          onChange={(e) =>
            setFormData({ ...formData, resource_type: e.target.value as ResourceType })
          }
        />

        <Input
          label="Name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="Resource name"
          required
        />

        <Input
          label="Call Sign"
          value={formData.call_sign || ''}
          onChange={(e) => setFormData({ ...formData, call_sign: e.target.value })}
          placeholder="E.g., Engine 1, Unit 42"
        />

        <Input
          label="Capabilities (comma-separated)"
          value={capabilitiesInput}
          onChange={(e) => setCapabilitiesInput(e.target.value)}
          placeholder="E.g., fire, rescue, hazmat"
        />

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Add Resource
          </Button>
        </div>
      </form>
    </Modal>
  );
}

interface UpdateStatusModalProps {
  isOpen: boolean;
  onClose: () => void;
  resource: Resource;
  onUpdate: (status: ResourceStatus) => Promise<void>;
}

function UpdateStatusModal({
  isOpen,
  onClose,
  resource,
  onUpdate,
}: UpdateStatusModalProps) {
  const [status, setStatus] = useState<ResourceStatus>(resource.status);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setStatus(resource.status);
  }, [resource]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onUpdate(status);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Update Resource Status">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600">
            Updating: <strong>{resource.call_sign || resource.name}</strong>
          </p>
        </div>

        <Select
          label="New Status"
          options={statusOptions}
          value={status}
          onChange={(e) => setStatus(e.target.value as ResourceStatus)}
        />

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Update Status
          </Button>
        </div>
      </form>
    </Modal>
  );
}
