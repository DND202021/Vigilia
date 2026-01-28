/**
 * BIMImport Component
 * Drag-and-drop file upload for BIM/IFC files with preview and progress.
 */

import { useState, useCallback, useRef } from 'react';
import { cn } from '../../utils';
import { buildingsApi } from '../../services/api';
import type { BIMImportResult } from '../../types';

interface BIMImportProps {
  buildingId: string;
  onImportComplete?: (result: BIMImportResult) => void;
  onCancel?: () => void;
  className?: string;
}

type ImportState = 'idle' | 'uploading' | 'preview' | 'success' | 'error';

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB for BIM files

export function BIMImport({
  buildingId,
  onImportComplete,
  onCancel,
  className,
}: BIMImportProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [importState, setImportState] = useState<ImportState>('idle');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<BIMImportResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Validate file
  const validateFile = useCallback((file: File): string | null => {
    const validExtensions = ['.ifc'];
    const extension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));

    if (!validExtensions.includes(extension)) {
      return 'Invalid file type. Only IFC files are supported.';
    }
    if (file.size > MAX_FILE_SIZE) {
      return 'File too large. Maximum size is 100MB.';
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

    setImportState('uploading');
    setError(null);
    setUploadProgress(0);

    // Create abort controller for cancellation
    abortControllerRef.current = new AbortController();

    try {
      // Simulate progress for parsing phase
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return prev;
          }
          return prev + 10;
        });
      }, 300);

      const result = await buildingsApi.importBIM(buildingId, selectedFile);

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (result.success && result.bim_data) {
        setImportResult(result);
        setImportState('preview');
      } else {
        setError(result.message || 'Failed to parse BIM file');
        setImportState('error');
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Upload was cancelled
        setImportState('idle');
        setSelectedFile(null);
      } else {
        setError(err instanceof Error ? err.message : 'Upload failed');
        setImportState('error');
      }
    }
  }, [buildingId, selectedFile]);

  // Handle cancel during upload
  const handleCancelUpload = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setImportState('idle');
    setSelectedFile(null);
    setUploadProgress(0);
  }, []);

  // Handle final import confirmation
  const handleConfirmImport = useCallback(() => {
    if (importResult) {
      setImportState('success');
    }
  }, [importResult]);

  // Handle done
  const handleDone = useCallback(() => {
    if (importResult && onImportComplete) {
      onImportComplete(importResult);
    }
  }, [importResult, onImportComplete]);

  // Clear selected file
  const handleClear = useCallback(() => {
    setSelectedFile(null);
    setError(null);
    setImportState('idle');
    setImportResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  // Try again after error
  const handleTryAgain = useCallback(() => {
    setError(null);
    setImportState('idle');
    setSelectedFile(null);
    setImportResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  };

  return (
    <div className={cn('bg-white rounded-lg', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="text-lg font-semibold text-gray-900">Import BIM/IFC File</h3>
        {onCancel && importState !== 'uploading' && (
          <button
            onClick={onCancel}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      <div className="p-4 space-y-4">
        {/* Idle State - File Selection */}
        {importState === 'idle' && (
          <>
            {/* Drop zone */}
            <div
              className={cn(
                'border-2 border-dashed rounded-lg p-8 text-center transition-colors',
                isDragging
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-300 hover:border-gray-400'
              )}
              onDragEnter={handleDragEnter}
              onDragLeave={handleDragLeave}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".ifc"
                onChange={handleInputChange}
                className="hidden"
              />

              {selectedFile ? (
                <div className="space-y-4">
                  {/* File info */}
                  <div className="flex items-center justify-center gap-3">
                    <div className="flex items-center gap-2">
                      <svg className="w-10 h-10 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                      </svg>
                      <div className="text-left">
                        <p className="font-medium text-gray-900">{selectedFile.name}</p>
                        <p className="text-sm text-gray-500">
                          {formatFileSize(selectedFile.size)}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={handleClear}
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="Remove file"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
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
                      d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                    />
                  </svg>
                  <p className="text-gray-600 mb-2">
                    Drag and drop your BIM/IFC file here
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
                    Supported format: IFC (max 100MB)
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
              {onCancel && (
                <button
                  onClick={onCancel}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
              )}
              <button
                onClick={handleUpload}
                disabled={!selectedFile}
                className={cn(
                  'px-4 py-2 text-white rounded-lg transition-colors',
                  selectedFile
                    ? 'bg-blue-600 hover:bg-blue-700'
                    : 'bg-gray-300 cursor-not-allowed'
                )}
              >
                Upload & Parse
              </button>
            </div>
          </>
        )}

        {/* Uploading State */}
        {importState === 'uploading' && (
          <div className="py-8 text-center space-y-4">
            <div className="w-16 h-16 mx-auto relative">
              <svg className="animate-spin text-blue-500" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            </div>

            <div>
              <p className="font-medium text-gray-900">
                {uploadProgress < 50 ? 'Uploading file...' : 'Parsing BIM data...'}
              </p>
              <p className="text-sm text-gray-500 mt-1">
                {selectedFile?.name}
              </p>
            </div>

            {/* Progress bar */}
            <div className="w-full max-w-xs mx-auto">
              <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                <span>Progress</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>

            <button
              onClick={handleCancelUpload}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
          </div>
        )}

        {/* Preview State */}
        {importState === 'preview' && importResult?.bim_data && (
          <div className="space-y-4">
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-3">BIM Data Preview</h4>

              <div className="grid grid-cols-2 gap-4 text-sm">
                {importResult.bim_data.building_name && (
                  <div>
                    <span className="text-gray-500">Building Name:</span>
                    <p className="font-medium text-gray-900">{importResult.bim_data.building_name}</p>
                  </div>
                )}

                <div>
                  <span className="text-gray-500">Floors:</span>
                  <p className="font-medium text-gray-900">{importResult.bim_data.floors?.length || 0}</p>
                </div>

                <div>
                  <span className="text-gray-500">Key Locations:</span>
                  <p className="font-medium text-gray-900">{importResult.bim_data.key_locations?.length || 0}</p>
                </div>

                <div>
                  <span className="text-gray-500">Materials:</span>
                  <p className="font-medium text-gray-900">{importResult.bim_data.materials?.length || 0}</p>
                </div>

                {importResult.bim_data.total_area_sqm && (
                  <div>
                    <span className="text-gray-500">Total Area:</span>
                    <p className="font-medium text-gray-900">{importResult.bim_data.total_area_sqm.toLocaleString()} sqm</p>
                  </div>
                )}

                {importResult.bim_data.building_height_m && (
                  <div>
                    <span className="text-gray-500">Building Height:</span>
                    <p className="font-medium text-gray-900">{importResult.bim_data.building_height_m} m</p>
                  </div>
                )}
              </div>
            </div>

            {/* Floor details */}
            {importResult.bim_data.floors && importResult.bim_data.floors.length > 0 && (
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
                  <h5 className="font-medium text-gray-700">Floors to be created</h5>
                </div>
                <div className="max-h-40 overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="text-left px-4 py-2 text-gray-500">Floor</th>
                        <th className="text-left px-4 py-2 text-gray-500">Name</th>
                        <th className="text-right px-4 py-2 text-gray-500">Area</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {importResult.bim_data.floors.map((floor, idx) => (
                        <tr key={idx}>
                          <td className="px-4 py-2">{floor.floor_number}</td>
                          <td className="px-4 py-2">{floor.floor_name || '-'}</td>
                          <td className="px-4 py-2 text-right">
                            {floor.area_sqm ? `${floor.area_sqm.toLocaleString()} sqm` : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={handleClear}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmImport}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Import
              </button>
            </div>
          </div>
        )}

        {/* Success State */}
        {importState === 'success' && importResult && (
          <div className="py-8 text-center space-y-4">
            <div className="w-16 h-16 mx-auto bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>

            <div>
              <p className="font-medium text-gray-900 text-lg">Import Successful!</p>
              <p className="text-sm text-gray-500 mt-2">
                {importResult.floors_created || 0} floor{(importResult.floors_created || 0) !== 1 ? 's' : ''} created, {importResult.locations_found || 0} location{(importResult.locations_found || 0) !== 1 ? 's' : ''} found
              </p>
            </div>

            <button
              onClick={handleDone}
              className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              Done
            </button>
          </div>
        )}

        {/* Error State */}
        {importState === 'error' && (
          <div className="py-8 text-center space-y-4">
            <div className="w-16 h-16 mx-auto bg-red-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>

            <div>
              <p className="font-medium text-gray-900 text-lg">Import Failed</p>
              <p className="text-sm text-red-600 mt-2">
                {error || 'An unexpected error occurred'}
              </p>
            </div>

            <button
              onClick={handleTryAgain}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default BIMImport;
