/**
 * Incident Edit Form
 * Allows editing all incident fields (title, description, type, priority, address)
 */

import { useState } from 'react';
import { Button, Input, Select, Card, CardHeader, CardTitle, CardContent } from '../ui';
import type { Incident, IncidentUpdateRequest, IncidentType, IncidentPriority } from '../../types';

interface IncidentEditFormProps {
  incident: Incident;
  onSave: (updates: IncidentUpdateRequest) => Promise<void>;
  onCancel: () => void;
}

const incidentTypeOptions = [
  { value: 'fire', label: 'Fire' },
  { value: 'medical', label: 'Medical' },
  { value: 'police', label: 'Police' },
  { value: 'traffic', label: 'Traffic' },
  { value: 'hazmat', label: 'Hazmat' },
  { value: 'rescue', label: 'Rescue' },
  { value: 'other', label: 'Other' },
];

const priorityOptions = [
  { value: '1', label: 'Critical (1)' },
  { value: '2', label: 'High (2)' },
  { value: '3', label: 'Medium (3)' },
  { value: '4', label: 'Low (4)' },
  { value: '5', label: 'Info (5)' },
];

export function IncidentEditForm({ incident, onSave, onCancel }: IncidentEditFormProps) {
  const [title, setTitle] = useState(incident.title);
  const [description, setDescription] = useState(incident.description || '');
  const [incidentType, setIncidentType] = useState<IncidentType>(incident.incident_type);
  const [priority, setPriority] = useState<IncidentPriority>(incident.priority);
  const [address, setAddress] = useState(incident.address || '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!title.trim()) {
      setError('Title is required');
      return;
    }

    setIsSubmitting(true);

    try {
      await onSave({
        title: title.trim(),
        description: description.trim() || undefined,
        incident_type: incidentType,
        priority,
        address: address.trim() || undefined,
      });
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      const detail = axiosError.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Failed to save changes');
    } finally {
      setIsSubmitting(false);
    }
  };

  const hasChanges =
    title !== incident.title ||
    description !== (incident.description || '') ||
    incidentType !== incident.incident_type ||
    priority !== incident.priority ||
    address !== (incident.address || '');

  return (
    <Card>
      <CardHeader>
        <CardTitle>Edit Incident</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <Input
            label="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Incident title"
            required
          />

          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Type"
              value={incidentType}
              onChange={(e) => setIncidentType(e.target.value as IncidentType)}
              options={incidentTypeOptions}
            />

            <Select
              label="Priority"
              value={priority.toString()}
              onChange={(e) => setPriority(parseInt(e.target.value) as IncidentPriority)}
              options={priorityOptions}
            />
          </div>

          <Input
            label="Address"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Location address"
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detailed description of the incident"
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button
              type="button"
              variant="secondary"
              onClick={onCancel}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              isLoading={isSubmitting}
              disabled={isSubmitting || !hasChanges}
            >
              Save Changes
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
