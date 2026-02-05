/**
 * Agency Settings Component
 * Allows admins to manage agency configuration
 */

import { useState, useEffect } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { agencyApi } from '../../services/api';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Select, Spinner } from '../ui';
import type { Agency, AgencyType } from '../../types';

const agencyTypeOptions = [
  { value: 'police', label: 'Police' },
  { value: 'fire', label: 'Fire Department' },
  { value: 'ems', label: 'EMS' },
  { value: 'dispatch', label: 'Dispatch Center' },
  { value: 'other', label: 'Other' },
];

export function AgencySettings() {
  const { user } = useAuthStore();
  const [agency, setAgency] = useState<Agency | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // Form state
  const [name, setName] = useState('');
  const [agencyType, setAgencyType] = useState<AgencyType>('other');
  const [jurisdiction, setJurisdiction] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [address, setAddress] = useState('');

  useEffect(() => {
    if (user?.agency_id) {
      loadAgency();
    } else {
      setIsLoading(false);
      setError('No agency associated with your account');
    }
  }, [user?.agency_id]);

  const loadAgency = async () => {
    if (!user?.agency_id) return;
    setIsLoading(true);
    try {
      const data = await agencyApi.get(user.agency_id);
      setAgency(data);
      // Populate form
      setName(data.name);
      setAgencyType(data.agency_type);
      setJurisdiction(data.jurisdiction || '');
      setContactEmail(data.contact_email || '');
      setContactPhone(data.contact_phone || '');
      setAddress(data.address || '');
    } catch (err: unknown) {
      const errorMessage = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : null;
      setError(errorMessage || 'Failed to load agency settings');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!user?.agency_id) return;
    setIsSaving(true);
    setError('');
    setSuccess(false);

    try {
      const updated = await agencyApi.update(user.agency_id, {
        name,
        agency_type: agencyType,
        jurisdiction: jurisdiction || undefined,
        contact_email: contactEmail || undefined,
        contact_phone: contactPhone || undefined,
        address: address || undefined,
      });
      setAgency(updated);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: unknown) {
      const errorMessage = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : null;
      setError(errorMessage || 'Failed to save agency settings');
    } finally {
      setIsSaving(false);
    }
  };

  const hasChanges = agency && (
    name !== agency.name ||
    agencyType !== agency.agency_type ||
    jurisdiction !== (agency.jurisdiction || '') ||
    contactEmail !== (agency.contact_email || '') ||
    contactPhone !== (agency.contact_phone || '') ||
    address !== (agency.address || '')
  );

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!user?.agency_id) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-gray-500">
          No agency associated with your account
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {success && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
          Agency settings saved successfully
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Agency Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            label="Agency Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter agency name"
            required
          />

          <Select
            label="Agency Type"
            value={agencyType}
            onChange={(e) => setAgencyType(e.target.value as AgencyType)}
            options={agencyTypeOptions}
          />

          <Input
            label="Jurisdiction"
            value={jurisdiction}
            onChange={(e) => setJurisdiction(e.target.value)}
            placeholder="Geographic jurisdiction"
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Contact Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            label="Contact Email"
            type="email"
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
            placeholder="agency@example.com"
          />

          <Input
            label="Contact Phone"
            type="tel"
            value={contactPhone}
            onChange={(e) => setContactPhone(e.target.value)}
            placeholder="(555) 123-4567"
          />

          <Input
            label="Address"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="123 Main St, City, State"
          />
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button
          onClick={handleSave}
          isLoading={isSaving}
          disabled={isSaving || !hasChanges}
        >
          Save Changes
        </Button>
      </div>
    </div>
  );
}
