/**
 * FloorPlanUpload Component
 * Drag-and-drop file upload for floor plans with preview and progress.
 */

import { useState, useCallback, useRef } from 'react';
import { cn } from '../../utils';
import { buildingsApi } from '../../services/api';
import type { FloorPlan } from '../../types';

interface FloorPlanUploadProps {
  buildingId: string;
  totalFloors: number;
  basementLevels: number;
  existingFloorPlans: FloorPlan[];
  onUploadComplete: (floorPlan: FloorPlan) => void;
  onClose?: () => void;
  className?: string;
}

const ALLOWED_TYPES = [
  'image/png',
  'image/jpeg',
  'image/jpg',
  'application/pdf',
  'image/svg+xml',
];

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

export function FloorPlanUpload({
  buildingId,
  totalFloors,
  basementLevels,
  existingFloorPlans,
  onUploadComplete,
  onClose,
  className,
}: FloorPlanUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [floorNumber, setFloorNumber] = useState<number>(0);
  const [floorName, setFloorName] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Generate floor options
  const floorOptions: { value: number; label: string; disabled: boolean }[] = [];

  // Basement levels (negative numbers)
  for (let i = -basementLevels; i < 0; i++) {
    const exists = existingFloorPlans.some((fp) => fp.floor_number === i);
    floorOptions.push({
      value: i,
      label: `Basement ${Math.abs(i)}`,
      disabled: exists,
    });
  }

  // Ground floor and above
  for (let i = 0; i < totalFloors; i++) {
    const exists = existingFloorPlans.some((fp) => fp.floor_number === i);
    floorOptions.push({
      value: i,
      label: i === 0 ? 'Ground Floor' : `Floor ${i}`,
      disabled: exists,
    });
  }

  // Validate file
  const validateFile = useCallback((file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return 'Invalid file type. Allowed: PNG, JPG, PDF, SVG';
    }
    if (file.size > MAX_FILE_SIZE) {
      return 'File too large. Maximum size is 50MB';
    }
    return null;
  }, []);

  // Handle file selection
  const handleFileSelect = useCallback(
    (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }

      setError(null);
      setSelectedFile(file);

      // Generate preview for images
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
          setPreview(e.target?.result as string);
        };
        reader.readAsDataURL(file);
      } else {
        setPreview(null);
      }
    },
    [validateFile]
  );

  // Drag and drop handlers
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        handleFileSelect(files[0]);
      }
    },
    [handleFileSelect]
  );

  // Handle file input change
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleFileSelect(files[0]);
      }
    },
    [handleFileSelect]
  );

  // Trigger file input click
  const handleBrowseClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  // Handle upload
  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setError(null);
    setUploadProgress(0);

    try {
      const result = await buildingsApi.uploadFloorPlan(
        buildingId,
        selectedFile,
        floorNumber,
        floorName || undefined,
        (progress) => setUploadProgress(progress)
      );

      onUploadComplete(result);

      // Reset form
      setSelectedFile(null);
      setPreview(null);
      setFloorName('');
      setUploadProgress(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  }, [buildingId, selectedFile, floorNumber, floorName, onUploadComplete]);

  // Clear selected file
  const handleClear = useCallback(() => {
    setSelectedFile(null);
    setPreview(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  return (
    <div className={cn('bg-white rounded-lg', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="text-lg font-semibold text-gray-900">Upload Floor Plan</h3>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      <div className="p-4 space-y-4">
        {/* Floor selection */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Floor Number
            </label>
            <select
              value={floorNumber}
              onChange={(e) => setFloorNumber(parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={isUploading}
            >
              {floorOptions.map((opt) => (
                <option key={opt.value} value={opt.value} disabled={opt.disabled}>
                  {opt.label} {opt.disabled && '(uploaded)'}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Floor Name (optional)
            </label>
            <input
              type="text"
              value={floorName}
              onChange={(e) => setFloorName(e.target.value)}
              placeholder="e.g., Lobby, Mechanical"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={isUploading}
            />
          </div>
        </div>

        {/* Drop zone */}
        <div
          className={cn(
            'border-2 border-dashed rounded-lg p-8 text-center transition-colors',
            isDragging
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400',
            isUploading && 'pointer-events-none opacity-50'
          )}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".png,.jpg,.jpeg,.pdf,.svg"
            onChange={handleInputChange}
            className="hidden"
            disabled={isUploading}
          />

          {selectedFile ? (
            <div className="space-y-4">
              {/* Preview */}
              {preview && (
                <div className="mx-auto max-w-xs">
                  <img
                    src={preview}
                    alt="Preview"
                    className="max-h-48 mx-auto rounded shadow"
                  />
                </div>
              )}

              {/* File info */}
              <div className="flex items-center justify-center gap-3">
                <div className="flex items-center gap-2">
                  <svg className="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <div className="text-left">
                    <p className="font-medium text-gray-900">{selectedFile.name}</p>
                    <p className="text-sm text-gray-500">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                {!isUploading && (
                  <button
                    onClick={handleClear}
                    className="p-1 text-gray-400 hover:text-gray-600"
                    title="Remove file"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>

              {/* Upload progress */}
              {isUploading && (
                <div className="w-full max-w-xs mx-auto">
                  <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                    <span>Uploading...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          ) : (
            <>
              <svg
                className="w-12 h-12 mx-auto text-gray-400 mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              <p className="text-gray-600 mb-2">
                Drag and drop your floor plan here
              </p>
              <p className="text-sm text-gray-500 mb-4">
                or
              </p>
              <button
                onClick={handleBrowseClick}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Browse Files
              </button>
              <p className="text-xs text-gray-400 mt-4">
                Supported formats: PNG, JPG, PDF, SVG (max 50MB)
              </p>
            </>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-2">
          {onClose && (
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              disabled={isUploading}
            >
              Cancel
            </button>
          )}
          <button
            onClick={handleUpload}
            disabled={!selectedFile || isUploading}
            className={cn(
              'px-4 py-2 text-white rounded-lg transition-colors',
              selectedFile && !isUploading
                ? 'bg-blue-600 hover:bg-blue-700'
                : 'bg-gray-300 cursor-not-allowed'
            )}
          >
            {isUploading ? 'Uploading...' : 'Upload Floor Plan'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default FloorPlanUpload;
