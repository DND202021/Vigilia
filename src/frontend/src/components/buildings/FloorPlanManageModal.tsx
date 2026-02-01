/**
 * FloorPlanManageModal Component
 * Modal for managing floor plans: edit metadata, replace image, delete.
 */

import { useState, useRef } from 'react';
import { Button, Badge, Spinner } from '../ui';
import { cn } from '../../utils';
import { buildingsApi } from '../../services/api';
import { toast } from '../../stores/toastStore';
import type { FloorPlan } from '../../types';

interface FloorPlanManageModalProps {
  buildingId: string;
  floorPlans: FloorPlan[];
  isOpen: boolean;
  onClose: () => void;
  onUpdated: () => void;
}

type EditMode = 'list' | 'edit' | 'replace';

interface EditState {
  id: string;
  floor_name: string;
  floor_number: number;
}

export function FloorPlanManageModal({
  buildingId,
  floorPlans,
  isOpen,
  onClose,
  onUpdated,
}: FloorPlanManageModalProps) {
  const [mode, setMode] = useState<EditMode>('list');
  const [editState, setEditState] = useState<EditState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadingFloorId, setUploadingFloorId] = useState<string | null>(null);

  const handleEdit = (plan: FloorPlan) => {
    setEditState({
      id: plan.id,
      floor_name: plan.floor_name || '',
      floor_number: plan.floor_number,
    });
    setMode('edit');
  };

  const handleSaveEdit = async () => {
    if (!editState) return;

    setIsLoading(true);
    try {
      await buildingsApi.updateFloorPlan(editState.id, {
        floor_name: editState.floor_name || undefined,
      });
      toast.success('Floor plan updated');
      setMode('list');
      setEditState(null);
      onUpdated();
    } catch (error) {
      console.error('Failed to update floor plan:', error);
      toast.error('Failed to update floor plan');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (planId: string) => {
    setIsLoading(true);
    try {
      await buildingsApi.deleteFloorPlan(planId);
      toast.success('Floor plan deleted');
      setConfirmDelete(null);
      onUpdated();
    } catch (error) {
      console.error('Failed to delete floor plan:', error);
      toast.error('Failed to delete floor plan');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReplaceClick = (planId: string) => {
    setUploadingFloorId(planId);
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !uploadingFloorId) return;

    const plan = floorPlans.find(p => p.id === uploadingFloorId);
    if (!plan) return;

    setIsLoading(true);
    try {
      await buildingsApi.uploadFloorPlan(buildingId, file, plan.floor_number, plan.floor_name);
      toast.success('Floor plan image replaced');
      onUpdated();
    } catch (error) {
      console.error('Failed to replace floor plan:', error);
      toast.error('Failed to replace floor plan image');
    } finally {
      setIsLoading(false);
      setUploadingFloorId(null);
      // Reset the file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleClose = () => {
    setMode('list');
    setEditState(null);
    setConfirmDelete(null);
    onClose();
  };

  if (!isOpen) return null;

  const sortedPlans = [...floorPlans].sort((a, b) => b.floor_number - a.floor_number);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={() => !isLoading && handleClose()}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">
            {mode === 'edit' ? 'Edit Floor Plan' : 'Manage Floor Plans'}
          </h2>
          <button
            onClick={handleClose}
            disabled={isLoading}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {mode === 'list' && (
            <div className="space-y-3">
              {sortedPlans.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No floor plans uploaded yet.</p>
              ) : (
                sortedPlans.map((plan) => (
                  <div
                    key={plan.id}
                    className={cn(
                      'border rounded-lg p-3 transition-colors',
                      confirmDelete === plan.id ? 'border-red-300 bg-red-50' : 'hover:bg-gray-50'
                    )}
                  >
                    {confirmDelete === plan.id ? (
                      <div className="space-y-3">
                        <p className="text-sm text-red-700 font-medium">
                          Delete "{plan.floor_name || `Floor ${plan.floor_number}`}"?
                        </p>
                        <p className="text-xs text-red-600">
                          This will permanently remove the floor plan and all associated markers.
                        </p>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => setConfirmDelete(null)}
                            disabled={isLoading}
                          >
                            Cancel
                          </Button>
                          <Button
                            size="sm"
                            className="bg-red-600 hover:bg-red-700"
                            onClick={() => handleDelete(plan.id)}
                            disabled={isLoading}
                          >
                            {isLoading ? 'Deleting...' : 'Delete'}
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center gap-3">
                        {/* Thumbnail */}
                        <div className="w-16 h-16 bg-gray-100 rounded overflow-hidden flex-shrink-0">
                          {plan.plan_thumbnail_url ? (
                            <img
                              src={plan.plan_thumbnail_url}
                              alt={plan.floor_name || `Floor ${plan.floor_number}`}
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-gray-400">
                              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                              </svg>
                            </div>
                          )}
                        </div>

                        {/* Info */}
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-gray-900 truncate">
                            {plan.floor_name || `Floor ${plan.floor_number}`}
                          </h4>
                          <div className="flex items-center gap-2 mt-0.5">
                            <Badge variant="secondary" size="sm">
                              Level {plan.floor_number}
                            </Badge>
                            {plan.file_type && (
                              <span className="text-xs text-gray-400 uppercase">
                                {plan.file_type}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex gap-1">
                          <button
                            onClick={() => handleEdit(plan)}
                            className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                            title="Edit name"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleReplaceClick(plan.id)}
                            className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                            title="Replace image"
                            disabled={isLoading}
                          >
                            {uploadingFloorId === plan.id && isLoading ? (
                              <Spinner size="sm" />
                            ) : (
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                              </svg>
                            )}
                          </button>
                          <button
                            onClick={() => setConfirmDelete(plan.id)}
                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                            title="Delete"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {mode === 'edit' && editState && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Floor Name</label>
                <input
                  type="text"
                  value={editState.floor_name}
                  onChange={e => setEditState({ ...editState, floor_name: e.target.value })}
                  placeholder={`Floor ${editState.floor_number}`}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Leave empty to use "Floor {editState.floor_number}"
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Floor Level</label>
                <input
                  type="number"
                  value={editState.floor_number}
                  disabled
                  className="w-full px-3 py-2 border rounded-lg bg-gray-50 text-gray-500"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Floor level cannot be changed. Delete and re-upload to use a different level.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 p-4 border-t bg-gray-50">
          {mode === 'edit' ? (
            <>
              <Button
                variant="secondary"
                onClick={() => {
                  setMode('list');
                  setEditState(null);
                }}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button onClick={handleSaveEdit} disabled={isLoading}>
                {isLoading ? 'Saving...' : 'Save'}
              </Button>
            </>
          ) : (
            <Button variant="secondary" onClick={handleClose} disabled={isLoading}>
              Done
            </Button>
          )}
        </div>
      </div>

      {/* Hidden file input for replace */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".png,.jpg,.jpeg,.pdf,.svg,.dwg"
        onChange={handleFileChange}
        className="hidden"
      />
    </div>
  );
}

export default FloorPlanManageModal;
