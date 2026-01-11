/**
 * Alerts Page
 */

import { useEffect, useState } from 'react';
import { useAlertStore } from '../stores/alertStore';
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
  Spinner,
} from '../components/ui';
import {
  formatRelativeTime,
  formatDate,
  getSeverityLabel,
  getSeverityBgColor,
  getSeverityColor,
  getAlertTypeLabel,
  cn,
} from '../utils';
import type { Alert, AlertSeverity, AlertType, IncidentType, IncidentPriority } from '../types';

const POLL_INTERVAL = 10000;

const severityFilterOptions = [
  { value: '', label: 'All Severities' },
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
  { value: 'info', label: 'Info' },
];

const statusFilterOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'new', label: 'New' },
  { value: 'acknowledged', label: 'Acknowledged' },
  { value: 'investigating', label: 'Investigating' },
  { value: 'escalated', label: 'Escalated' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'false_alarm', label: 'False Alarm' },
];

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

export function AlertsPage() {
  const {
    alerts,
    pendingAlerts,
    fetchAlerts,
    fetchPendingAlerts,
    acknowledgeAlert,
    resolveAlert,
    createIncidentFromAlert,
    isLoading,
    error,
    clearError,
  } = useAlertStore();

  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isCreateIncidentModalOpen, setIsCreateIncidentModalOpen] = useState(false);

  const fetchWithFilters = () => {
    const params: Record<string, unknown> = {};
    if (severityFilter) params.severity = severityFilter;
    if (statusFilter) params.status = statusFilter;
    fetchAlerts(params);
  };

  usePolling(fetchWithFilters, POLL_INTERVAL);
  usePolling(fetchPendingAlerts, POLL_INTERVAL);

  useEffect(() => {
    fetchWithFilters();
  }, [severityFilter, statusFilter]);

  const handleAcknowledge = async (alert: Alert) => {
    await acknowledgeAlert(alert.id);
  };

  const handleResolve = async (alert: Alert, isFalseAlarm: boolean = false) => {
    await resolveAlert(alert.id, isFalseAlarm);
    setIsDetailModalOpen(false);
  };

  const openDetail = (alert: Alert) => {
    setSelectedAlert(alert);
    setIsDetailModalOpen(true);
  };

  const openCreateIncident = (alert: Alert) => {
    setSelectedAlert(alert);
    setIsCreateIncidentModalOpen(true);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Alerts</h1>
        <p className="mt-1 text-gray-500">Monitor and manage incoming alerts</p>
      </div>

      {/* Pending Alerts Banner */}
      {pendingAlerts.length > 0 && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
              </span>
              <span className="font-semibold text-red-700">
                {pendingAlerts.length} pending alert{pendingAlerts.length > 1 ? 's' : ''} requiring attention
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <div className="w-48">
          <Select
            options={severityFilterOptions}
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
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

      {/* Alerts List */}
      <Card>
        <CardContent className="p-0">
          {isLoading && alerts.length === 0 ? (
            <div className="flex justify-center py-12">
              <Spinner size="lg" />
            </div>
          ) : alerts.length === 0 ? (
            <div className="text-center py-12 text-gray-500">No alerts found</div>
          ) : (
            <div className="divide-y divide-gray-200">
              {alerts.map((alert) => (
                <AlertRow
                  key={alert.id}
                  alert={alert}
                  onAcknowledge={() => handleAcknowledge(alert)}
                  onViewDetail={() => openDetail(alert)}
                  onCreateIncident={() => openCreateIncident(alert)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Detail Modal */}
      {selectedAlert && (
        <AlertDetailModal
          isOpen={isDetailModalOpen}
          onClose={() => setIsDetailModalOpen(false)}
          alert={selectedAlert}
          onResolve={(isFalseAlarm) => handleResolve(selectedAlert, isFalseAlarm)}
          onCreateIncident={() => {
            setIsDetailModalOpen(false);
            setIsCreateIncidentModalOpen(true);
          }}
        />
      )}

      {/* Create Incident Modal */}
      {selectedAlert && (
        <CreateIncidentFromAlertModal
          isOpen={isCreateIncidentModalOpen}
          onClose={() => setIsCreateIncidentModalOpen(false)}
          alert={selectedAlert}
          onCreate={async (data) => {
            await createIncidentFromAlert(selectedAlert.id, data);
            setIsCreateIncidentModalOpen(false);
          }}
        />
      )}
    </div>
  );
}

interface AlertRowProps {
  alert: Alert;
  onAcknowledge: () => void;
  onViewDetail: () => void;
  onCreateIncident: () => void;
}

function AlertRow({ alert, onAcknowledge, onViewDetail, onCreateIncident }: AlertRowProps) {
  const isPending = alert.status === 'new';

  return (
    <div
      className={cn(
        'px-6 py-4 hover:bg-gray-50 transition-colors',
        isPending && 'bg-red-50 hover:bg-red-100'
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Badge
              className={cn(
                getSeverityBgColor(alert.severity),
                getSeverityColor(alert.severity)
              )}
            >
              {getSeverityLabel(alert.severity)}
            </Badge>
            <span className="text-sm font-medium text-gray-900">{alert.title}</span>
            {isPending && (
              <span className="flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
              </span>
            )}
          </div>
          <div className="mt-1 flex items-center gap-4 text-sm text-gray-500">
            <span>{alert.source}</span>
            <span>{getAlertTypeLabel(alert.alert_type)}</span>
            <span>{formatRelativeTime(alert.created_at)}</span>
          </div>
          {alert.description && (
            <p className="mt-1 text-sm text-gray-600 truncate">{alert.description}</p>
          )}
        </div>
        <div className="ml-4 flex items-center gap-2">
          <Badge variant="secondary">{alert.status}</Badge>
          <div className="flex gap-1">
            {alert.status === 'new' && (
              <Button size="sm" variant="outline" onClick={onAcknowledge}>
                Acknowledge
              </Button>
            )}
            <Button size="sm" variant="ghost" onClick={onViewDetail}>
              Details
            </Button>
            {!alert.linked_incident_id && alert.status !== 'resolved' && (
              <Button size="sm" onClick={onCreateIncident}>
                Create Incident
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

interface AlertDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  alert: Alert;
  onResolve: (isFalseAlarm: boolean) => void;
  onCreateIncident: () => void;
}

function AlertDetailModal({
  isOpen,
  onClose,
  alert,
  onResolve,
  onCreateIncident,
}: AlertDetailModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Alert Details" size="lg">
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Badge
            className={cn(
              getSeverityBgColor(alert.severity),
              getSeverityColor(alert.severity)
            )}
          >
            {getSeverityLabel(alert.severity)}
          </Badge>
          <Badge variant="secondary">{alert.status}</Badge>
        </div>

        <h3 className="text-xl font-semibold">{alert.title}</h3>

        <dl className="grid grid-cols-2 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-500">Type</dt>
            <dd className="mt-1">{getAlertTypeLabel(alert.alert_type)}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Source</dt>
            <dd className="mt-1">{alert.source}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Created</dt>
            <dd className="mt-1">{formatDate(alert.created_at)}</dd>
          </div>
          {alert.acknowledged_at && (
            <div>
              <dt className="text-sm font-medium text-gray-500">Acknowledged</dt>
              <dd className="mt-1">{formatDate(alert.acknowledged_at)}</dd>
            </div>
          )}
          {alert.latitude && alert.longitude && (
            <div className="col-span-2">
              <dt className="text-sm font-medium text-gray-500">Location</dt>
              <dd className="mt-1">
                {alert.latitude.toFixed(6)}, {alert.longitude.toFixed(6)}
              </dd>
            </div>
          )}
        </dl>

        {alert.description && (
          <div>
            <h4 className="text-sm font-medium text-gray-500">Description</h4>
            <p className="mt-1 text-gray-900">{alert.description}</p>
          </div>
        )}

        {alert.raw_payload && (
          <div>
            <h4 className="text-sm font-medium text-gray-500">Raw Data</h4>
            <pre className="mt-1 p-3 bg-gray-100 rounded text-xs overflow-auto max-h-40">
              {JSON.stringify(alert.raw_payload, null, 2)}
            </pre>
          </div>
        )}

        {alert.linked_incident_id && (
          <div className="p-3 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-700">
              Linked to incident: {alert.linked_incident_id}
            </p>
          </div>
        )}

        <div className="flex justify-end gap-3 pt-4 border-t">
          {alert.status !== 'resolved' && alert.status !== 'false_alarm' && (
            <>
              <Button variant="secondary" onClick={() => onResolve(true)}>
                Mark as False Alarm
              </Button>
              <Button variant="outline" onClick={() => onResolve(false)}>
                Resolve
              </Button>
            </>
          )}
          {!alert.linked_incident_id && alert.status !== 'resolved' && (
            <Button onClick={onCreateIncident}>Create Incident</Button>
          )}
        </div>
      </div>
    </Modal>
  );
}

interface CreateIncidentFromAlertModalProps {
  isOpen: boolean;
  onClose: () => void;
  alert: Alert;
  onCreate: (data: { incident_type: IncidentType; priority: IncidentPriority; title?: string }) => Promise<void>;
}

function CreateIncidentFromAlertModal({
  isOpen,
  onClose,
  alert,
  onCreate,
}: CreateIncidentFromAlertModalProps) {
  const [incidentType, setIncidentType] = useState<IncidentType>('other');
  const [priority, setPriority] = useState<IncidentPriority>(2);
  const [title, setTitle] = useState(alert.title);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Map alert severity to priority
  useEffect(() => {
    const severityToPriority: Record<AlertSeverity, IncidentPriority> = {
      critical: 1,
      high: 2,
      medium: 3,
      low: 4,
      info: 5,
    };
    setPriority(severityToPriority[alert.severity] || 3);
    setTitle(alert.title);
  }, [alert]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onCreate({ incident_type: incidentType, priority, title });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create Incident from Alert">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600">
            Creating incident from alert: <strong>{alert.title}</strong>
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Incident Title
          </label>
          <input
            type="text"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Select
            label="Incident Type"
            options={incidentTypeOptions}
            value={incidentType}
            onChange={(e) => setIncidentType(e.target.value as IncidentType)}
          />
          <Select
            label="Priority"
            options={priorityOptions}
            value={String(priority)}
            onChange={(e) => setPriority(Number(e.target.value) as IncidentPriority)}
          />
        </div>

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
