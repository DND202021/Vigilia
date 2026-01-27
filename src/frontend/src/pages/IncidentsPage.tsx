/**
 * Incidents Page
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useIncidentStore } from '../stores/incidentStore';
import { usePolling } from '../hooks/useInterval';
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
import {
  formatRelativeTime,
  getPriorityLabel,
  getPriorityBgColor,
  getPriorityColor,
  getStatusLabel,
  getStatusBgColor,
  getIncidentTypeLabel,
  cn,
} from '../utils';
import type { Incident, IncidentCreateRequest, IncidentType, IncidentPriority } from '../types';

const POLL_INTERVAL = 15000;

const incidentTypeOptions = [
  { value: 'fire', label: 'Fire' },
  { value: 'medical', label: 'Medical' },
  { value: 'police', label: 'Police' },
  { value: 'traffic', label: 'Traffic' },
  { value: 'hazmat', label: 'HazMat' },
  { value: 'rescue', label: 'Rescue' },
  { value: 'other', label: 'Other' },
];

const priorityOptions = [
  { value: '1', label: 'P1 - Critical' },
  { value: '2', label: 'P2 - High' },
  { value: '3', label: 'P3 - Medium' },
  { value: '4', label: 'P4 - Low' },
  { value: '5', label: 'P5 - Info' },
];

const statusFilterOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'new', label: 'New' },
  { value: 'assigned', label: 'Assigned' },
  { value: 'dispatched', label: 'Dispatched' },
  { value: 'en_route', label: 'En Route' },
  { value: 'on_scene', label: 'On Scene' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
];

export function IncidentsPage() {
  const {
    incidents,
    fetchIncidents,
    createIncident,
    isLoading,
    error,
    clearError,
  } = useIncidentStore();

  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Fetch with filters
  const fetchWithFilters = () => {
    const params: Record<string, unknown> = {};
    if (statusFilter) params.status = statusFilter;
    if (typeFilter) params.incident_type = typeFilter;
    fetchIncidents(params);
  };

  usePolling(fetchWithFilters, POLL_INTERVAL);

  useEffect(() => {
    fetchWithFilters();
  }, [statusFilter, typeFilter]);

  const filteredIncidents = incidents.filter((incident) => {
    if (statusFilter && incident.status !== statusFilter) return false;
    if (typeFilter && incident.incident_type !== typeFilter) return false;
    return true;
  });

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Incidents</h1>
          <p className="mt-1 text-gray-500">Manage emergency incidents</p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          New Incident
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <div className="w-48">
          <Select
            options={statusFilterOptions}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            placeholder="Filter by status"
          />
        </div>
        <div className="w-48">
          <Select
            options={[{ value: '', label: 'All Types' }, ...incidentTypeOptions]}
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            placeholder="Filter by type"
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

      {/* Incidents List */}
      <Card>
        <CardContent className="p-0">
          {isLoading && incidents.length === 0 ? (
            <div className="flex justify-center py-12">
              <Spinner size="lg" />
            </div>
          ) : filteredIncidents.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              No incidents found
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Incident
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Priority
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Location
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Reported
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredIncidents.map((incident) => (
                    <IncidentTableRow key={incident.id} incident={incident} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Modal */}
      <CreateIncidentModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={createIncident}
      />
    </div>
  );
}

function IncidentTableRow({ incident }: { incident: Incident }) {
  return (
    <tr className="hover:bg-gray-50">
      <td className="px-6 py-4">
        <Link
          to={`/incidents/${incident.id}`}
          className="font-medium text-blue-600 hover:text-blue-700"
        >
          {incident.incident_number}
        </Link>
        <p className="text-sm text-gray-500 truncate max-w-xs">{incident.title}</p>
      </td>
      <td className="px-6 py-4">
        <Badge variant="secondary">{getIncidentTypeLabel(incident.incident_type)}</Badge>
      </td>
      <td className="px-6 py-4">
        <Badge
          className={cn(
            getPriorityBgColor(incident.priority),
            getPriorityColor(incident.priority)
          )}
        >
          {getPriorityLabel(incident.priority)}
        </Badge>
      </td>
      <td className="px-6 py-4">
        <Badge className={getStatusBgColor(incident.status)}>
          {getStatusLabel(incident.status)}
        </Badge>
      </td>
      <td className="px-6 py-4 text-sm text-gray-600 truncate max-w-xs">
        {incident.address || '-'}
      </td>
      <td className="px-6 py-4 text-sm text-gray-500">
        {formatRelativeTime(incident.reported_at)}
      </td>
      <td className="px-6 py-4 text-right">
        <Link
          to={`/incidents/${incident.id}`}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          View
        </Link>
      </td>
    </tr>
  );
}

interface CreateIncidentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (data: IncidentCreateRequest) => Promise<Incident>;
}

function CreateIncidentModal({ isOpen, onClose, onCreate }: CreateIncidentModalProps) {
  const [formData, setFormData] = useState<IncidentCreateRequest>({
    incident_type: 'other',
    priority: 3,
    title: '',
    description: '',
    address: '',
    latitude: undefined,
    longitude: undefined,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!formData.title || formData.title.length < 5) {
      setError('Title is required and must be at least 5 characters');
      return;
    }

    setIsSubmitting(true);
    try {
      await onCreate(formData);
      onClose();
      setFormData({
        incident_type: 'other',
        priority: 3,
        title: '',
        description: '',
        address: '',
        latitude: undefined,
        longitude: undefined,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create incident');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create New Incident" size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        <Input
          label="Title"
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          placeholder="Brief incident description"
          required
        />

        <div className="grid grid-cols-2 gap-4">
          <Select
            label="Type"
            options={incidentTypeOptions}
            value={formData.incident_type}
            onChange={(e) =>
              setFormData({ ...formData, incident_type: e.target.value as IncidentType })
            }
          />
          <Select
            label="Priority"
            options={priorityOptions}
            value={String(formData.priority)}
            onChange={(e) =>
              setFormData({ ...formData, priority: Number(e.target.value) as IncidentPriority })
            }
          />
        </div>

        <Input
          label="Address"
          value={formData.address || ''}
          onChange={(e) => setFormData({ ...formData, address: e.target.value })}
          placeholder="Incident location"
        />

        <textarea
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          rows={3}
          placeholder="Additional details..."
          value={formData.description || ''}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
        />

        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Latitude (optional)"
            type="number"
            value={formData.latitude ?? ''}
            onChange={(e) => setFormData({ ...formData, latitude: e.target.value ? parseFloat(e.target.value) : undefined })}
            placeholder="e.g., 45.5017"
          />
          <Input
            label="Longitude (optional)"
            type="number"
            value={formData.longitude ?? ''}
            onChange={(e) => setFormData({ ...formData, longitude: e.target.value ? parseFloat(e.target.value) : undefined })}
            placeholder="e.g., -73.5673"
          />
        </div>
        <p className="text-xs text-gray-500">
          Leave coordinates blank to use default location. You can update the location later.
        </p>

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Create Incident
          </Button>
        </div>
      </form>
    </Modal>
  );
}
