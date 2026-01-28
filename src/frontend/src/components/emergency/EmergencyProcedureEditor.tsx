/**
 * EmergencyProcedureEditor Component
 *
 * Form component for creating and editing emergency procedures.
 * Supports procedure steps, contacts, and equipment management.
 */

import { useState, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '../ui/Card';
import { cn } from '../../utils';
import type {
  EmergencyProcedure,
  EmergencyProcedureType,
  ProcedureStep,
  ProcedureContact,
} from '../../types';

// --- Props ---

export interface EmergencyProcedureEditorProps {
  buildingId: string;
  procedure?: EmergencyProcedure;
  onSave: (procedure: EmergencyProcedure) => void;
  onCancel: () => void;
  className?: string;
}

// --- Types ---

interface FormData {
  name: string;
  procedure_type: EmergencyProcedureType;
  priority: number;
  description: string;
  estimated_duration_minutes: number;
  is_active: boolean;
  steps: ProcedureStep[];
  contacts: ProcedureContact[];
  equipment_needed: string[];
}

interface ValidationErrors {
  name?: string;
  steps?: string;
}

// --- Constants ---

const PROCEDURE_TYPES: { value: EmergencyProcedureType; label: string }[] = [
  { value: 'evacuation', label: 'Evacuation' },
  { value: 'fire', label: 'Fire Response' },
  { value: 'medical', label: 'Medical Emergency' },
  { value: 'hazmat', label: 'Hazmat Incident' },
  { value: 'lockdown', label: 'Lockdown' },
  { value: 'active_shooter', label: 'Active Shooter' },
  { value: 'weather', label: 'Severe Weather' },
  { value: 'utility_failure', label: 'Utility Failure' },
];

const PRIORITY_OPTIONS: { value: number; label: string; color: string }[] = [
  { value: 1, label: 'Critical', color: 'text-red-700 bg-red-100' },
  { value: 2, label: 'High', color: 'text-orange-700 bg-orange-100' },
  { value: 3, label: 'Medium', color: 'text-yellow-700 bg-yellow-100' },
  { value: 4, label: 'Low', color: 'text-blue-700 bg-blue-100' },
  { value: 5, label: 'Routine', color: 'text-gray-700 bg-gray-100' },
];

const DEFAULT_STEP: Omit<ProcedureStep, 'order'> = {
  title: '',
  description: '',
  responsible_role: '',
  duration_minutes: undefined,
};

const DEFAULT_CONTACT: ProcedureContact = {
  name: '',
  role: '',
  phone: '',
  email: '',
};

// --- Helper Functions ---

function createDefaultFormData(_buildingId: string, procedure?: EmergencyProcedure): FormData {
  if (procedure) {
    return {
      name: procedure.name,
      procedure_type: procedure.procedure_type,
      priority: procedure.priority,
      description: procedure.description || '',
      estimated_duration_minutes: procedure.estimated_duration_minutes || 0,
      is_active: procedure.is_active,
      steps: procedure.steps.length > 0 ? [...procedure.steps] : [{ ...DEFAULT_STEP, order: 1 }],
      contacts: [...procedure.contacts],
      equipment_needed: [...procedure.equipment_needed],
    };
  }

  return {
    name: '',
    procedure_type: 'evacuation',
    priority: 3,
    description: '',
    estimated_duration_minutes: 0,
    is_active: true,
    steps: [{ ...DEFAULT_STEP, order: 1 }],
    contacts: [],
    equipment_needed: [],
  };
}

function validateForm(data: FormData): ValidationErrors {
  const errors: ValidationErrors = {};

  if (!data.name.trim()) {
    errors.name = 'Procedure name is required';
  }

  const validSteps = data.steps.filter((s) => s.title.trim());
  if (validSteps.length === 0) {
    errors.steps = 'At least one step with a title is required';
  }

  return errors;
}

// --- Sub-Components ---

interface StepItemProps {
  step: ProcedureStep;
  index: number;
  onUpdate: (index: number, step: ProcedureStep) => void;
  onRemove: (index: number) => void;
  onMoveUp: (index: number) => void;
  onMoveDown: (index: number) => void;
  canMoveUp: boolean;
  canMoveDown: boolean;
}

function StepItem({
  step,
  index,
  onUpdate,
  onRemove,
  onMoveUp,
  onMoveDown,
  canMoveUp,
  canMoveDown,
}: StepItemProps) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 space-y-3 bg-gray-50">
      <div className="flex items-center gap-3">
        {/* Drag handle and step number */}
        <div className="flex flex-col items-center gap-1">
          <button
            type="button"
            onClick={() => onMoveUp(index)}
            disabled={!canMoveUp}
            className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
            aria-label="Move step up"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            </svg>
          </button>
          <span className="w-8 h-8 flex items-center justify-center bg-blue-100 text-blue-700 rounded-full text-sm font-semibold">
            {index + 1}
          </span>
          <button
            type="button"
            onClick={() => onMoveDown(index)}
            disabled={!canMoveDown}
            className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
            aria-label="Move step down"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>

        {/* Step content */}
        <div className="flex-1 space-y-3">
          <input
            type="text"
            value={step.title}
            onChange={(e) => onUpdate(index, { ...step, title: e.target.value })}
            placeholder="Step title"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <textarea
            value={step.description}
            onChange={(e) => onUpdate(index, { ...step, description: e.target.value })}
            placeholder="Step description (optional)"
            rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          />
          <div className="grid grid-cols-2 gap-3">
            <input
              type="text"
              value={step.responsible_role || ''}
              onChange={(e) => onUpdate(index, { ...step, responsible_role: e.target.value || undefined })}
              placeholder="Responsible role (optional)"
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={step.duration_minutes || ''}
                onChange={(e) =>
                  onUpdate(index, {
                    ...step,
                    duration_minutes: e.target.value ? Number(e.target.value) : undefined,
                  })
                }
                placeholder="Duration"
                min={0}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <span className="text-sm text-gray-500">min</span>
            </div>
          </div>
        </div>

        {/* Remove button */}
        <button
          type="button"
          onClick={() => onRemove(index)}
          className="p-2 text-gray-400 hover:text-red-600 transition-colors"
          aria-label="Remove step"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}

interface ContactItemProps {
  contact: ProcedureContact;
  index: number;
  onUpdate: (index: number, contact: ProcedureContact) => void;
  onRemove: (index: number) => void;
}

function ContactItem({ contact, index, onUpdate, onRemove }: ContactItemProps) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
      <div className="flex items-start gap-3">
        <div className="flex-1 grid grid-cols-2 gap-3">
          <input
            type="text"
            value={contact.name}
            onChange={(e) => onUpdate(index, { ...contact, name: e.target.value })}
            placeholder="Contact name"
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <input
            type="text"
            value={contact.role}
            onChange={(e) => onUpdate(index, { ...contact, role: e.target.value })}
            placeholder="Role"
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <input
            type="tel"
            value={contact.phone || ''}
            onChange={(e) => onUpdate(index, { ...contact, phone: e.target.value || undefined })}
            placeholder="Phone number"
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <input
            type="email"
            value={contact.email || ''}
            onChange={(e) => onUpdate(index, { ...contact, email: e.target.value || undefined })}
            placeholder="Email address"
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <button
          type="button"
          onClick={() => onRemove(index)}
          className="p-2 text-gray-400 hover:text-red-600 transition-colors"
          aria-label="Remove contact"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}

interface EquipmentTagsProps {
  equipment: string[];
  onAdd: (item: string) => void;
  onRemove: (index: number) => void;
}

function EquipmentTags({ equipment, onAdd, onRemove }: EquipmentTagsProps) {
  const [inputValue, setInputValue] = useState('');

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      e.preventDefault();
      onAdd(inputValue.trim());
      setInputValue('');
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {equipment.map((item, index) => (
          <span
            key={`${item}-${index}`}
            className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-100 text-blue-700 rounded-full text-sm"
          >
            {item}
            <button
              type="button"
              onClick={() => onRemove(index)}
              className="ml-1 text-blue-500 hover:text-blue-700"
              aria-label={`Remove ${item}`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </span>
        ))}
      </div>
      <input
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type equipment name and press Enter"
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      />
    </div>
  );
}

// --- Main Component ---

export function EmergencyProcedureEditor({
  buildingId,
  procedure,
  onSave,
  onCancel,
  className,
}: EmergencyProcedureEditorProps) {
  const [formData, setFormData] = useState<FormData>(() =>
    createDefaultFormData(buildingId, procedure)
  );
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [saving, setSaving] = useState(false);

  const isEditMode = Boolean(procedure?.id);

  // --- Step Handlers ---

  const handleStepUpdate = useCallback((index: number, step: ProcedureStep) => {
    setFormData((prev) => ({
      ...prev,
      steps: prev.steps.map((s, i) => (i === index ? step : s)),
    }));
  }, []);

  const handleStepRemove = useCallback((index: number) => {
    setFormData((prev) => ({
      ...prev,
      steps: prev.steps
        .filter((_, i) => i !== index)
        .map((s, i) => ({ ...s, order: i + 1 })),
    }));
  }, []);

  const handleStepMoveUp = useCallback((index: number) => {
    if (index === 0) return;
    setFormData((prev) => {
      const newSteps = [...prev.steps];
      [newSteps[index - 1], newSteps[index]] = [newSteps[index], newSteps[index - 1]];
      return {
        ...prev,
        steps: newSteps.map((s, i) => ({ ...s, order: i + 1 })),
      };
    });
  }, []);

  const handleStepMoveDown = useCallback((index: number) => {
    setFormData((prev) => {
      if (index >= prev.steps.length - 1) return prev;
      const newSteps = [...prev.steps];
      [newSteps[index], newSteps[index + 1]] = [newSteps[index + 1], newSteps[index]];
      return {
        ...prev,
        steps: newSteps.map((s, i) => ({ ...s, order: i + 1 })),
      };
    });
  }, []);

  const handleAddStep = useCallback(() => {
    setFormData((prev) => ({
      ...prev,
      steps: [...prev.steps, { ...DEFAULT_STEP, order: prev.steps.length + 1 }],
    }));
  }, []);

  // --- Contact Handlers ---

  const handleContactUpdate = useCallback((index: number, contact: ProcedureContact) => {
    setFormData((prev) => ({
      ...prev,
      contacts: prev.contacts.map((c, i) => (i === index ? contact : c)),
    }));
  }, []);

  const handleContactRemove = useCallback((index: number) => {
    setFormData((prev) => ({
      ...prev,
      contacts: prev.contacts.filter((_, i) => i !== index),
    }));
  }, []);

  const handleAddContact = useCallback(() => {
    setFormData((prev) => ({
      ...prev,
      contacts: [...prev.contacts, { ...DEFAULT_CONTACT }],
    }));
  }, []);

  // --- Equipment Handlers ---

  const handleAddEquipment = useCallback((item: string) => {
    setFormData((prev) => {
      if (prev.equipment_needed.includes(item)) return prev;
      return {
        ...prev,
        equipment_needed: [...prev.equipment_needed, item],
      };
    });
  }, []);

  const handleRemoveEquipment = useCallback((index: number) => {
    setFormData((prev) => ({
      ...prev,
      equipment_needed: prev.equipment_needed.filter((_, i) => i !== index),
    }));
  }, []);

  // --- Form Submit ---

  const handleSubmit = useCallback(async () => {
    const validationErrors = validateForm(formData);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setErrors({});
    setSaving(true);

    try {
      // Filter out empty steps and contacts
      const cleanSteps = formData.steps
        .filter((s) => s.title.trim())
        .map((s, i) => ({ ...s, order: i + 1 }));

      const cleanContacts = formData.contacts.filter((c) => c.name.trim() && c.role.trim());

      const procedureData: EmergencyProcedure = {
        id: procedure?.id || '',
        building_id: buildingId,
        name: formData.name.trim(),
        procedure_type: formData.procedure_type,
        priority: formData.priority,
        description: formData.description.trim() || undefined,
        estimated_duration_minutes: formData.estimated_duration_minutes || undefined,
        is_active: formData.is_active,
        steps: cleanSteps,
        contacts: cleanContacts,
        equipment_needed: formData.equipment_needed,
        created_at: procedure?.created_at || new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      onSave(procedureData);
    } finally {
      setSaving(false);
    }
  }, [formData, buildingId, procedure, onSave]);

  // --- Render ---

  return (
    <Card className={cn('', className)}>
      <CardHeader>
        <CardTitle>{isEditMode ? 'Edit Procedure' : 'Create Emergency Procedure'}</CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Basic Info Section */}
        <div className="space-y-4">
          <h4 className="text-sm font-semibold text-gray-900 border-b pb-2">Basic Information</h4>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Procedure Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="e.g., Building Evacuation Procedure"
              className={cn(
                'w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                errors.name ? 'border-red-300' : 'border-gray-300'
              )}
            />
            {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name}</p>}
          </div>

          {/* Type and Priority */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Procedure Type</label>
              <select
                value={formData.procedure_type}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    procedure_type: e.target.value as EmergencyProcedureType,
                  }))
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {PROCEDURE_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
              <div className="flex gap-1">
                {PRIORITY_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setFormData((prev) => ({ ...prev, priority: option.value }))}
                    className={cn(
                      'flex-1 py-2 text-xs font-medium rounded-lg border transition-all',
                      formData.priority === option.value
                        ? option.color + ' border-transparent ring-2 ring-offset-1 ring-blue-500'
                        : 'bg-white border-gray-300 text-gray-600 hover:border-gray-400'
                    )}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
              placeholder="Describe the purpose and scope of this procedure..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            />
          </div>

          {/* Duration and Active Status */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Estimated Duration
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={formData.estimated_duration_minutes || ''}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      estimated_duration_minutes: e.target.value ? Number(e.target.value) : 0,
                    }))
                  }
                  placeholder="0"
                  min={0}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <span className="text-sm text-gray-500">minutes</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <label className="flex items-center gap-3 cursor-pointer py-2">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, is_active: e.target.checked }))
                  }
                  className="w-5 h-5 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Active Procedure</span>
              </label>
            </div>
          </div>
        </div>

        {/* Steps Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b pb-2">
            <h4 className="text-sm font-semibold text-gray-900">
              Procedure Steps <span className="text-red-500">*</span>
            </h4>
            <button
              type="button"
              onClick={handleAddStep}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add Step
            </button>
          </div>

          {errors.steps && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{errors.steps}</p>
          )}

          <div className="space-y-3">
            {formData.steps.map((step, index) => (
              <StepItem
                key={index}
                step={step}
                index={index}
                onUpdate={handleStepUpdate}
                onRemove={handleStepRemove}
                onMoveUp={handleStepMoveUp}
                onMoveDown={handleStepMoveDown}
                canMoveUp={index > 0}
                canMoveDown={index < formData.steps.length - 1}
              />
            ))}
          </div>
        </div>

        {/* Contacts Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b pb-2">
            <h4 className="text-sm font-semibold text-gray-900">Emergency Contacts</h4>
            <button
              type="button"
              onClick={handleAddContact}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add Contact
            </button>
          </div>

          {formData.contacts.length === 0 ? (
            <p className="text-sm text-gray-500 italic py-4 text-center">
              No emergency contacts added yet.
            </p>
          ) : (
            <div className="space-y-3">
              {formData.contacts.map((contact, index) => (
                <ContactItem
                  key={index}
                  contact={contact}
                  index={index}
                  onUpdate={handleContactUpdate}
                  onRemove={handleContactRemove}
                />
              ))}
            </div>
          )}
        </div>

        {/* Equipment Section */}
        <div className="space-y-4">
          <h4 className="text-sm font-semibold text-gray-900 border-b pb-2">Equipment Needed</h4>
          <EquipmentTags
            equipment={formData.equipment_needed}
            onAdd={handleAddEquipment}
            onRemove={handleRemoveEquipment}
          />
        </div>
      </CardContent>

      <CardFooter className="flex justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSubmit}
          disabled={saving}
          className={cn(
            'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
            'bg-blue-600 text-white hover:bg-blue-700',
            'disabled:bg-blue-400 disabled:cursor-not-allowed'
          )}
        >
          {saving ? 'Saving...' : isEditMode ? 'Update Procedure' : 'Create Procedure'}
        </button>
      </CardFooter>
    </Card>
  );
}

export default EmergencyProcedureEditor;
