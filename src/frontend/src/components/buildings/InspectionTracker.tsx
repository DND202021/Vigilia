/**
 * InspectionTracker Component
 *
 * Tracks building inspections: list, create, update with status and schedule management.
 */

import { useState, useEffect } from 'react';
import { useInspectionStore } from '../../stores/inspectionStore';
import type { Inspection, InspectionType, InspectionStatus, InspectionCreateRequest } from '../../types';
import { cn } from '../../utils';

const TYPE_LABELS: Record<InspectionType, string> = {
  fire_safety: 'Fire Safety',
  structural: 'Structural',
  hazmat: 'Hazmat',
  general: 'General',
};

const TYPE_ICONS: Record<InspectionType, string> = {
  fire_safety: '\u{1F525}',
  structural: '\u{1F3D7}\uFE0F',
  hazmat: '\u2622\uFE0F',
  general: '\u{1F50D}',
};

const STATUS_COLORS: Record<InspectionStatus, string> = {
  scheduled: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-yellow-100 text-yellow-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  overdue: 'bg-red-100 text-red-700 animate-pulse',
};

const STATUS_LABELS: Record<InspectionStatus, string> = {
  scheduled: 'Scheduled',
  in_progress: 'In Progress',
  completed: 'Completed',
  failed: 'Failed',
  overdue: 'Overdue',
};

interface InspectionTrackerProps {
  buildingId: string;
  onInspectionSelect?: (inspection: Inspection) => void;
  className?: string;
}

export function InspectionTracker({ buildingId, onInspectionSelect, className }: InspectionTrackerProps) {
  const {
    inspections,
    isLoading,
    isSaving,
    error,
    typeFilter,
    statusFilter,
    fetchInspections,
    createInspection,
    updateInspection,
    deleteInspection,
    setTypeFilter,
    setStatusFilter,
    clearError,
  } = useInspectionStore();

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState<Inspection | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Create form state
  const [newType, setNewType] = useState<InspectionType>('general');
  const [newDate, setNewDate] = useState('');
  const [newInspector, setNewInspector] = useState('');

  // Edit form state
  const [editStatus, setEditStatus] = useState<InspectionStatus>('scheduled');
  const [editFindings, setEditFindings] = useState('');
  const [editFollowUp, setEditFollowUp] = useState(false);
  const [editFollowUpDate, setEditFollowUpDate] = useState('');

  // Fetch inspections on mount and filter change
  useEffect(() => {
    fetchInspections(buildingId);
  }, [buildingId, typeFilter, statusFilter, fetchInspections]);

  // Handle create
  const handleCreate = async () => {
    if (!newDate || !newInspector) return;

    const data: InspectionCreateRequest = {
      inspection_type: newType,
      scheduled_date: newDate,
      inspector_name: newInspector,
    };

    const result = await createInspection(buildingId, data);
    if (result) {
      setShowCreateForm(false);
      setNewType('general');
      setNewDate('');
      setNewInspector('');
    }
  };

  // Open edit form
  const openEditForm = (inspection: Inspection) => {
    setShowEditForm(inspection);
    setEditStatus(inspection.status);
    setEditFindings(inspection.findings || '');
    setEditFollowUp(inspection.follow_up_required);
    setEditFollowUpDate(inspection.follow_up_date || '');
  };

  // Handle update
  const handleUpdate = async () => {
    if (!showEditForm) return;

    await updateInspection(showEditForm.id, {
      status: editStatus,
      findings: editFindings || undefined,
      follow_up_required: editFollowUp,
      follow_up_date: editFollowUp ? editFollowUpDate || undefined : undefined,
      completed_date: editStatus === 'completed' ? new Date().toISOString() : undefined,
    });

    setShowEditForm(null);
  };

  // Handle delete
  const handleDelete = async (id: string) => {
    await deleteInspection(id);
    setDeleteConfirmId(null);
  };

  // Check if inspection is overdue
  const isOverdue = (inspection: Inspection): boolean => {
    if (inspection.status === 'completed' || inspection.status === 'failed') return false;
    return new Date(inspection.scheduled_date) < new Date();
  };

  // Format date
  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  // Days until/since
  const getDaysLabel = (dateStr: string): string => {
    const date = new Date(dateStr);
    const today = new Date();
    const diffTime = date.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Tomorrow';
    if (diffDays === -1) return 'Yesterday';
    if (diffDays > 0) return `In ${diffDays} days`;
    return `${Math.abs(diffDays)} days ago`;
  };

  return (
    <div className={cn('bg-white rounded-lg shadow', className)}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900">Inspections</h3>
          <button
            onClick={() => setShowCreateForm(true)}
            className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700"
          >
            Schedule Inspection
          </button>
        </div>

        {/* Type filter pills */}
        <div className="flex flex-wrap gap-2 mb-2">
          <button
            onClick={() => setTypeFilter(null)}
            className={cn(
              'px-2.5 py-1 text-xs font-medium rounded-full transition-colors',
              typeFilter === null ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            )}
          >
            All Types
          </button>
          {(Object.keys(TYPE_LABELS) as InspectionType[]).map((type) => (
            <button
              key={type}
              onClick={() => setTypeFilter(type)}
              className={cn(
                'px-2.5 py-1 text-xs font-medium rounded-full transition-colors',
                typeFilter === type ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
            >
              {TYPE_ICONS[type]} {TYPE_LABELS[type]}
            </button>
          ))}
        </div>

        {/* Status filter pills */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setStatusFilter(null)}
            className={cn(
              'px-2.5 py-1 text-xs font-medium rounded-full transition-colors',
              statusFilter === null ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            )}
          >
            All Status
          </button>
          {(Object.keys(STATUS_LABELS) as InspectionStatus[]).map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={cn(
                'px-2.5 py-1 text-xs font-medium rounded-full transition-colors',
                statusFilter === status ? STATUS_COLORS[status] : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
            >
              {STATUS_LABELS[status]}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mt-3 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between">
          <span className="text-sm text-red-700">{error}</span>
          <button onClick={clearError} className="text-red-500 hover:text-red-700">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Create form */}
      {showCreateForm && (
        <div className="p-4 border-b border-gray-200 bg-gray-50">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Schedule New Inspection</h4>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Type *</label>
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value as InspectionType)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
              >
                {(Object.keys(TYPE_LABELS) as InspectionType[]).map((type) => (
                  <option key={type} value={type}>{TYPE_LABELS[type]}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Scheduled Date *</label>
              <input
                type="date"
                value={newDate}
                onChange={(e) => setNewDate(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Inspector Name *</label>
              <input
                type="text"
                value={newInspector}
                onChange={(e) => setNewInspector(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                placeholder="Inspector name"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <button
              onClick={() => { setShowCreateForm(false); setNewType('general'); setNewDate(''); setNewInspector(''); }}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50"
              disabled={isSaving}
            >
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={!newDate || !newInspector || isSaving}
              className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {isSaving ? 'Creating...' : 'Schedule'}
            </button>
          </div>
        </div>
      )}

      {/* Edit form modal */}
      {showEditForm && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={() => setShowEditForm(null)}>
          <div className="bg-white rounded-lg shadow-lg max-w-md w-full p-4" onClick={(e) => e.stopPropagation()}>
            <h4 className="text-lg font-semibold text-gray-900 mb-4">Update Inspection</h4>

            <div className="space-y-3 mb-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Status</label>
                <select
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value as InspectionStatus)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                >
                  {(Object.keys(STATUS_LABELS) as InspectionStatus[]).filter(s => s !== 'overdue').map((status) => (
                    <option key={status} value={status}>{STATUS_LABELS[status]}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Findings</label>
                <textarea
                  value={editFindings}
                  onChange={(e) => setEditFindings(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder="Inspection findings..."
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="followUp"
                  checked={editFollowUp}
                  onChange={(e) => setEditFollowUp(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="followUp" className="text-sm text-gray-700">Follow-up required</label>
              </div>

              {editFollowUp && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Follow-up Date</label>
                  <input
                    type="date"
                    value={editFollowUpDate}
                    onChange={(e) => setEditFollowUpDate(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowEditForm(null)}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50"
                disabled={isSaving}
              >
                Cancel
              </button>
              <button
                onClick={handleUpdate}
                disabled={isSaving}
                className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {isSaving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Inspection list */}
      <div className="divide-y divide-gray-100">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <svg className="animate-spin h-6 w-6 text-blue-500" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span className="ml-2 text-sm text-gray-500">Loading inspections...</span>
          </div>
        ) : inspections.length === 0 ? (
          <div className="py-12 text-center">
            <span className="text-4xl">{'\u{1F4CB}'}</span>
            <p className="mt-2 text-sm text-gray-500">No inspections scheduled</p>
            <button onClick={() => setShowCreateForm(true)} className="mt-3 text-sm text-blue-600 hover:text-blue-700 font-medium">
              Schedule first inspection
            </button>
          </div>
        ) : (
          inspections.map((inspection) => {
            const overdue = isOverdue(inspection);
            const status = overdue && inspection.status === 'scheduled' ? 'overdue' : inspection.status;

            return (
              <div
                key={inspection.id}
                className="px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => onInspectionSelect?.(inspection)}
              >
                <div className="flex items-start gap-3">
                  <span className="text-2xl flex-shrink-0">{TYPE_ICONS[inspection.inspection_type]}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-gray-900">{TYPE_LABELS[inspection.inspection_type]}</span>
                      <span className={cn('px-2 py-0.5 text-[10px] font-medium rounded-full', STATUS_COLORS[status])}>
                        {STATUS_LABELS[status]}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      <span>{formatDate(inspection.scheduled_date)}</span>
                      <span className={cn(overdue ? 'text-red-600 font-medium' : '')}>
                        {getDaysLabel(inspection.scheduled_date)}
                      </span>
                      <span>Inspector: {inspection.inspector_name}</span>
                    </div>
                    {inspection.findings && (
                      <p className="text-xs text-gray-500 mt-1 truncate">{inspection.findings}</p>
                    )}
                    {inspection.follow_up_required && (
                      <div className="flex items-center gap-1 mt-1 text-xs text-amber-600">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                        </svg>
                        <span>Follow-up required{inspection.follow_up_date ? ` by ${formatDate(inspection.follow_up_date)}` : ''}</span>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={(e) => { e.stopPropagation(); openEditForm(inspection); }}
                      className="p-1.5 text-gray-400 hover:text-blue-600 rounded hover:bg-blue-50"
                      title="Edit"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                    {deleteConfirmId === inspection.id ? (
                      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                        <button onClick={() => handleDelete(inspection.id)} className="p-1 text-xs text-white bg-red-600 rounded hover:bg-red-700">Yes</button>
                        <button onClick={() => setDeleteConfirmId(null)} className="p-1 text-xs text-gray-600 bg-gray-200 rounded hover:bg-gray-300">No</button>
                      </div>
                    ) : (
                      <button
                        onClick={(e) => { e.stopPropagation(); setDeleteConfirmId(inspection.id); }}
                        className="p-1.5 text-gray-400 hover:text-red-600 rounded hover:bg-red-50"
                        title="Delete"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

export default InspectionTracker;
