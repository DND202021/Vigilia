/**
 * Bulk Provisioning Upload Component
 *
 * CSV drag-drop upload with Papa Parse validation and preview table.
 * Client-side validation against backend schema before upload.
 */
import { useState, useRef } from 'react';
import { usePapaParse } from 'react-papaparse';
import { useBulkProvisioningStore } from '../../stores/bulkProvisioningStore';
import { Button } from '../ui/Button';
import { cn } from '../../utils';
import BulkProvisioningProgress from './BulkProvisioningProgress';

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const VALID_DEVICE_TYPES = ['microphone', 'camera', 'sensor', 'gateway'];
const VALID_CREDENTIAL_TYPES = ['access_token', 'x509'];
const MAX_ROWS = 1000;

export function BulkProvisioningUpload() {
  const { readString } = usePapaParse();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    csvFile,
    csvData,
    validationErrors,
    validRows,
    isUploading,
    results,
    uploadError,
    setCSVFile,
    setCSVData,
    uploadCSV,
    downloadTemplate,
    clearUploadError,
  } = useBulkProvisioningStore();

  const [isDragging, setIsDragging] = useState(false);

  // Validate individual CSV row
  const validateRow = (row: any): string | null => {
    if (!row.name || row.name.trim().length === 0) {
      return 'Missing required field: name';
    }
    if (!VALID_DEVICE_TYPES.includes(row.device_type)) {
      return `Invalid device_type: ${row.device_type} (must be ${VALID_DEVICE_TYPES.join(', ')})`;
    }
    if (!row.building_id || !UUID_REGEX.test(row.building_id)) {
      return `Invalid building_id UUID format: ${row.building_id}`;
    }
    if (!VALID_CREDENTIAL_TYPES.includes(row.credential_type)) {
      return `Invalid credential_type: ${row.credential_type} (must be ${VALID_CREDENTIAL_TYPES.join(', ')})`;
    }
    if (row.profile_id && !UUID_REGEX.test(row.profile_id)) {
      return `Invalid profile_id UUID format: ${row.profile_id}`;
    }
    return null;
  };

  // Handle CSV file content
  const handleFileContent = (content: string, file: File) => {
    readString(content, {
      header: true,
      skipEmptyLines: true,
      transformHeader: (h) => h.trim().toLowerCase(),
      complete: (results) => {
        const errors: Record<number, string> = {};
        const validData: any[] = [];
        const headers = results.meta.fields || [];

        // Check required columns
        const requiredColumns = ['name', 'device_type', 'building_id', 'credential_type'];
        const missingColumns = requiredColumns.filter((col) => !headers.includes(col));
        if (missingColumns.length > 0) {
          errors[1] = `Missing required columns: ${missingColumns.join(', ')}`;
          setCSVData([], headers, errors);
          return;
        }

        // Check row limit
        if (results.data.length > MAX_ROWS) {
          errors[1] = `CSV exceeds ${MAX_ROWS} row limit. Please split into smaller files.`;
          setCSVData([], headers, errors);
          return;
        }

        // Validate each row
        results.data.forEach((row: any, index: number) => {
          const rowNum = index + 2; // Row 1 is header
          const error = validateRow(row);

          if (error) {
            errors[rowNum] = error;
          } else {
            validData.push({ ...row, _rowNum: rowNum });
          }
        });

        setCSVData(validData, headers, errors);
        setCSVFile(file);
      },
      error: (error) => {
        const errors = { 1: `CSV parse error: ${error.message}` };
        setCSVData([], [], errors);
      },
    });
  };

  // Handle drag-drop
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      const errors = { 1: 'Please upload a CSV file' };
      setCSVData([], [], errors);
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      handleFileContent(content, file);
    };
    reader.readAsText(file);
  };

  // Handle file input change
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      handleFileContent(content, file);
    };
    reader.readAsText(file);
  };

  // Handle browse files button
  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  // Handle upload
  const handleUpload = async () => {
    clearUploadError();
    try {
      await uploadCSV();
    } catch (error) {
      // Error already set in store
    }
  };

  // If results exist, show progress component instead
  if (results) {
    return <BulkProvisioningProgress />;
  }

  const hasValidationErrors = Object.keys(validationErrors).length > 0;
  const canUpload = validRows > 0 && !hasValidationErrors && !isUploading;
  const rowLimitExceeded = validationErrors[1]?.includes('exceeds');

  return (
    <div className="space-y-6">
      {/* Header with template download */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Bulk Device Provisioning</h2>
          <p className="text-sm text-gray-600 mt-1">
            Upload a CSV file to provision multiple devices at once (max {MAX_ROWS} devices)
          </p>
        </div>
        <Button onClick={downloadTemplate} variant="secondary" size="sm">
          Download CSV Template
        </Button>
      </div>

      {/* Drag-drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={cn(
          'border-2 border-dashed rounded-lg p-12 text-center transition-colors',
          isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400',
          hasValidationErrors && 'border-red-300'
        )}
      >
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          stroke="currentColor"
          fill="none"
          viewBox="0 0 48 48"
          aria-hidden="true"
        >
          <path
            d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <p className="mt-4 text-lg text-gray-700">
          Drag and drop CSV file here
        </p>
        <p className="mt-2 text-sm text-gray-500">or</p>
        <Button onClick={handleBrowseClick} variant="secondary" size="sm" className="mt-4">
          Browse Files
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileInputChange}
          className="hidden"
        />
      </div>

      {/* Upload error */}
      {uploadError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{uploadError}</p>
        </div>
      )}

      {/* Validation errors */}
      {hasValidationErrors && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <h3 className="font-bold text-red-800">
            Validation Errors ({Object.keys(validationErrors).length})
          </h3>
          <ul className="mt-2 space-y-1 max-h-48 overflow-y-auto">
            {Object.entries(validationErrors).map(([rowNum, error]) => (
              <li key={rowNum} className="text-sm text-red-700">
                Row {rowNum}: {error}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Preview table */}
      {csvData.length > 0 && !rowLimitExceeded && (
        <div>
          <h3 className="font-bold text-gray-900 mb-2">
            Preview ({validRows} valid rows)
          </h3>
          <div className="border border-gray-300 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-300">
                <tr>
                  <th className="px-4 py-2 text-left font-semibold text-gray-700">Row</th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-700">Name</th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-700">Type</th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-700">Building ID</th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-700">Credential Type</th>
                </tr>
              </thead>
              <tbody>
                {csvData.slice(0, 10).map((row) => (
                  <tr key={row._rowNum} className="border-b border-gray-200 last:border-0">
                    <td className="px-4 py-2 text-gray-600">{row._rowNum}</td>
                    <td className="px-4 py-2 text-gray-900">{row.name}</td>
                    <td className="px-4 py-2 text-gray-600">{row.device_type}</td>
                    <td className="px-4 py-2 text-xs font-mono text-gray-600" title={row.building_id}>
                      {row.building_id.substring(0, 8)}...
                    </td>
                    <td className="px-4 py-2 text-gray-600">{row.credential_type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {csvData.length > 10 && (
            <p className="text-sm text-gray-500 mt-2">
              ... and {csvData.length - 10} more rows
            </p>
          )}
        </div>
      )}

      {/* Upload button */}
      {csvFile && (
        <div className="flex justify-end">
          <Button
            onClick={handleUpload}
            disabled={!canUpload || rowLimitExceeded}
            size="lg"
          >
            {isUploading ? 'Uploading...' : `Upload ${validRows} Device${validRows !== 1 ? 's' : ''}`}
          </Button>
        </div>
      )}
    </div>
  );
}
