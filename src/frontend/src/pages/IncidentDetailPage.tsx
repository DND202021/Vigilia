/**
 * Incident Detail Page
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useIncidentStore } from '../stores/incidentStore';
import { useResourceStore } from '../stores/resourceStore';
import { useWebSocket } from '../hooks/useWebSocket';
import { buildingsApi, incidentsApi } from '../services/api';
import { BuildingInfoPanel, IncidentEditForm } from '../components/incidents';
import type { IncidentUpdateRequest } from '../types';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  Button,
  Select,
  Modal,
  Spinner,
} from '../components/ui';
import {
  formatDate,
  getPriorityLabel,
  getPriorityBgColor,
  getPriorityColor,
  getStatusLabel,
  getStatusBgColor,
  getIncidentTypeLabel,
  cn,
} from '../utils';
import type { IncidentStatus, Building } from '../types';

const statusOptions = [
  { value: 'new', label: 'New' },
  { value: 'assigned', label: 'Assigned' },
  { value: 'dispatched', label: 'Dispatched' },
  { value: 'en_route', label: 'En Route' },
  { value: 'on_scene', label: 'On Scene' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
  { value: 'cancelled', label: 'Cancelled' },
];

export function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const {
    selectedIncident: incident,
    fetchIncident,
    updateIncidentStatus,
    assignUnit,
    isLoading,
    error,
  } = useIncidentStore();

  const { availableResources, fetchAvailableResources } = useResourceStore();
  const { joinBuilding, leaveBuilding } = useWebSocket();

  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [linkedBuilding, setLinkedBuilding] = useState<Building | null>(null);
  const [isBuildingLoading, setIsBuildingLoading] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);

  useEffect(() => {
    if (id) {
      fetchIncident(id);
      fetchAvailableResources();
    }
  }, [id]);

  // Fetch building data when incident has building_id
  useEffect(() => {
    if (incident?.building_id) {
      setIsBuildingLoading(true);
      buildingsApi
        .get(incident.building_id)
        .then(setLinkedBuilding)
        .catch((err) => {
          console.error('Failed to fetch linked building:', err);
          setLinkedBuilding(null);
        })
        .finally(() => setIsBuildingLoading(false));
    } else {
      setLinkedBuilding(null);
    }
  }, [incident?.building_id]);

  // Subscribe to building updates via WebSocket
  useEffect(() => {
    const buildingId = incident?.building_id;
    if (buildingId) {
      joinBuilding(buildingId);
      return () => leaveBuilding(buildingId);
    }
  }, [incident?.building_id, joinBuilding, leaveBuilding]);

  // Reset edit mode when incident changes
  useEffect(() => {
    setIsEditMode(false);
  }, [id]);

  // Handle incident update from edit form
  const handleUpdate = async (updates: IncidentUpdateRequest) => {
    if (!id) return;
    await incidentsApi.update(id, updates);
    await fetchIncident(id);
    setIsEditMode(false);
  };

  if (isLoading && !incident) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h2 className="text-xl font-semibold text-red-700">Error Loading Incident</h2>
          <p className="mt-2 text-red-600">{error}</p>
          <Button
            variant="secondary"
            className="mt-4"
            onClick={() => navigate('/incidents')}
          >
            Back to Incidents
          </Button>
        </div>
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="bg-gray-50 rounded-lg p-6 text-center">
          <h2 className="text-xl font-semibold text-gray-700">Incident Not Found</h2>
          <Button
            variant="secondary"
            className="mt-4"
            onClick={() => navigate('/incidents')}
          >
            Back to Incidents
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Breadcrumb */}
      <nav className="mb-4">
        <Link to="/incidents" className="text-blue-600 hover:text-blue-700">
          Incidents
        </Link>
        <span className="mx-2 text-gray-400">/</span>
        <span className="text-gray-600">{incident.incident_number}</span>
      </nav>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-gray-900">{incident.incident_number}</h1>
            <Badge
              className={cn(
                getPriorityBgColor(incident.priority),
                getPriorityColor(incident.priority)
              )}
            >
              {getPriorityLabel(incident.priority)}
            </Badge>
            <Badge className={getStatusBgColor(incident.status)}>
              {getStatusLabel(incident.status)}
            </Badge>
          </div>
          <p className="mt-2 text-xl text-gray-700">{incident.title}</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            onClick={() => setIsEditMode(true)}
            disabled={isEditMode}
          >
            Edit Incident
          </Button>
          <Button variant="outline" onClick={() => setIsStatusModalOpen(true)}>
            Update Status
          </Button>
          <Button onClick={() => setIsAssignModalOpen(true)}>Assign Unit</Button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Details or Edit Form */}
        <div className="lg:col-span-2 space-y-6">
          {isEditMode ? (
            <IncidentEditForm
              incident={incident}
              onSave={handleUpdate}
              onCancel={() => setIsEditMode(false)}
            />
          ) : (
            <>
              {/* Info Card */}
              <Card>
                <CardHeader>
                  <CardTitle>Incident Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <dl className="grid grid-cols-2 gap-4">
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Type</dt>
                      <dd className="mt-1">
                        <Badge variant="secondary">
                          {getIncidentTypeLabel(incident.incident_type)}
                        </Badge>
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Reported</dt>
                      <dd className="mt-1 text-gray-900">{formatDate(incident.reported_at)}</dd>
                    </div>
                    <div className="col-span-2">
                      <dt className="text-sm font-medium text-gray-500">Address</dt>
                      <dd className="mt-1 text-gray-900">{incident.address || 'Not specified'}</dd>
                    </div>
                    {incident.description && (
                      <div className="col-span-2">
                        <dt className="text-sm font-medium text-gray-500">Description</dt>
                        <dd className="mt-1 text-gray-900 whitespace-pre-wrap">
                          {incident.description}
                        </dd>
                      </div>
                    )}
                  </dl>
                </CardContent>
              </Card>

              {/* Caller Info */}
              {(incident.caller_name || incident.caller_phone) && (
                <Card>
                  <CardHeader>
                    <CardTitle>Caller Information</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <dl className="grid grid-cols-2 gap-4">
                      {incident.caller_name && (
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Name</dt>
                          <dd className="mt-1 text-gray-900">{incident.caller_name}</dd>
                        </div>
                      )}
                      {incident.caller_phone && (
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Phone</dt>
                          <dd className="mt-1 text-gray-900">{incident.caller_phone}</dd>
                        </div>
                      )}
                    </dl>
                  </CardContent>
                </Card>
              )}

              {/* Timeline */}
              <Card>
                <CardHeader>
                  <CardTitle>Timeline</CardTitle>
                </CardHeader>
                <CardContent>
                  {incident.timeline_events && incident.timeline_events.length > 0 ? (
                    <div className="space-y-4">
                      {incident.timeline_events.map((event, index) => (
                        <div key={index} className="flex gap-4">
                          <div className="flex flex-col items-center">
                            <div className="w-3 h-3 bg-blue-600 rounded-full" />
                            {index < incident.timeline_events.length - 1 && (
                              <div className="w-0.5 h-full bg-gray-200 mt-1" />
                            )}
                          </div>
                          <div className="flex-1 pb-4">
                            <p className="text-sm font-medium text-gray-900">
                              {event.event_type}
                            </p>
                            <p className="text-sm text-gray-600">{event.description}</p>
                            <p className="text-xs text-gray-400 mt-1">
                              {formatDate(event.timestamp)}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-4">No timeline events</p>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </div>

        {/* Right Column - Sidebar */}
        <div className="space-y-6">
          {/* Linked Building Info */}
          {isBuildingLoading && (
            <Card>
              <CardContent className="py-6">
                <div className="flex items-center justify-center gap-2">
                  <Spinner size="sm" />
                  <span className="text-gray-500">Loading building info...</span>
                </div>
              </CardContent>
            </Card>
          )}
          {linkedBuilding && !isBuildingLoading && (
            <div className="space-y-3">
              <BuildingInfoPanel
                building={linkedBuilding}
                onViewFloorPlans={() =>
                  navigate(`/buildings/${linkedBuilding.id}#floor-plans`)
                }
              />
              <Button
                variant="outline"
                className="w-full"
                onClick={() => navigate(`/buildings/${linkedBuilding.id}`)}
              >
                View Full Building Details
              </Button>
            </div>
          )}

          {/* Timestamps */}
          <Card>
            <CardHeader>
              <CardTitle>Timestamps</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-sm font-medium text-gray-500">Reported</p>
                <p className="text-gray-900">{formatDate(incident.reported_at)}</p>
              </div>
              {incident.dispatched_at && (
                <div>
                  <p className="text-sm font-medium text-gray-500">Dispatched</p>
                  <p className="text-gray-900">{formatDate(incident.dispatched_at)}</p>
                </div>
              )}
              {incident.on_scene_at && (
                <div>
                  <p className="text-sm font-medium text-gray-500">On Scene</p>
                  <p className="text-gray-900">{formatDate(incident.on_scene_at)}</p>
                </div>
              )}
              {incident.resolved_at && (
                <div>
                  <p className="text-sm font-medium text-gray-500">Resolved</p>
                  <p className="text-gray-900">{formatDate(incident.resolved_at)}</p>
                </div>
              )}
              {incident.closed_at && (
                <div>
                  <p className="text-sm font-medium text-gray-500">Closed</p>
                  <p className="text-gray-900">{formatDate(incident.closed_at)}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Assigned Units */}
          <Card>
            <CardHeader>
              <CardTitle>Assigned Units ({incident.assigned_units?.length || 0})</CardTitle>
            </CardHeader>
            <CardContent>
              {incident.assigned_units && incident.assigned_units.length > 0 ? (
                <div className="space-y-2">
                  {incident.assigned_units.map((unitId) => (
                    <div
                      key={unitId}
                      className="flex items-center gap-2 p-2 bg-gray-50 rounded"
                    >
                      <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-blue-700 text-sm font-semibold">U</span>
                      </div>
                      <span className="text-sm font-medium">{unitId}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-4">No units assigned</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Status Update Modal */}
      <StatusUpdateModal
        isOpen={isStatusModalOpen}
        onClose={() => setIsStatusModalOpen(false)}
        currentStatus={incident.status}
        onUpdate={async (status, notes) => {
          await updateIncidentStatus(incident.id, status, notes);
          setIsStatusModalOpen(false);
        }}
      />

      {/* Assign Unit Modal */}
      <AssignUnitModal
        isOpen={isAssignModalOpen}
        onClose={() => setIsAssignModalOpen(false)}
        availableResources={availableResources}
        onAssign={async (unitId) => {
          await assignUnit(incident.id, unitId);
          setIsAssignModalOpen(false);
        }}
      />
    </div>
  );
}

interface StatusUpdateModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentStatus: IncidentStatus;
  onUpdate: (status: string, notes?: string) => Promise<void>;
}

function StatusUpdateModal({
  isOpen,
  onClose,
  currentStatus,
  onUpdate,
}: StatusUpdateModalProps) {
  const [status, setStatus] = useState(currentStatus);
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onUpdate(status, notes || undefined);
      setNotes('');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Update Status">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Select
          label="New Status"
          options={statusOptions}
          value={status}
          onChange={(e) => setStatus(e.target.value as IncidentStatus)}
        />
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Notes (optional)
          </label>
          <textarea
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add notes about this status change..."
          />
        </div>
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

interface AssignUnitModalProps {
  isOpen: boolean;
  onClose: () => void;
  availableResources: Array<{ id: string; name: string; call_sign?: string; resource_type: string }>;
  onAssign: (unitId: string) => Promise<void>;
}

function AssignUnitModal({
  isOpen,
  onClose,
  availableResources,
  onAssign,
}: AssignUnitModalProps) {
  const [selectedUnit, setSelectedUnit] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUnit) return;

    setIsSubmitting(true);
    try {
      await onAssign(selectedUnit);
      setSelectedUnit('');
    } finally {
      setIsSubmitting(false);
    }
  };

  const unitOptions = availableResources.map((r) => ({
    value: r.id,
    label: r.call_sign || r.name,
  }));

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Assign Unit">
      <form onSubmit={handleSubmit} className="space-y-4">
        {availableResources.length === 0 ? (
          <p className="text-center text-gray-500 py-4">
            No available units to assign
          </p>
        ) : (
          <Select
            label="Select Unit"
            options={unitOptions}
            value={selectedUnit}
            onChange={(e) => setSelectedUnit(e.target.value)}
            placeholder="Choose a unit..."
          />
        )}
        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            isLoading={isSubmitting}
            disabled={!selectedUnit || availableResources.length === 0}
          >
            Assign Unit
          </Button>
        </div>
      </form>
    </Modal>
  );
}
