/**
 * Bulk Provisioning Progress Component
 *
 * Displays per-device provisioning results with summary stats.
 * Allows downloading failed rows for re-upload.
 */
import { useBulkProvisioningStore } from '../../stores/bulkProvisioningStore';
import { Button } from '../ui/Button';

export default function BulkProvisioningProgress() {
  const {
    results,
    successCount,
    failCount,
    totalRows,
    downloadFailedRows,
    reset,
  } = useBulkProvisioningStore();

  if (!results) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-gray-900">Bulk Provisioning Results</h2>
        <p className="text-sm text-gray-600 mt-1">
          Provisioning completed. Review the results below.
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        {/* Total */}
        <div className="bg-white border border-gray-300 rounded-lg shadow-sm p-4">
          <div className="text-sm font-medium text-gray-500">Total Devices</div>
          <div className="mt-1 text-3xl font-bold text-gray-900">{totalRows}</div>
        </div>

        {/* Successful */}
        <div className="bg-white border border-green-300 rounded-lg shadow-sm p-4">
          <div className="text-sm font-medium text-green-600">Successful</div>
          <div className="mt-1 text-3xl font-bold text-green-700">{successCount}</div>
        </div>

        {/* Failed */}
        <div className="bg-white border border-red-300 rounded-lg shadow-sm p-4">
          <div className="text-sm font-medium text-red-600">Failed</div>
          <div className="mt-1 text-3xl font-bold text-red-700">{failCount}</div>
        </div>
      </div>

      {/* Security note */}
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-sm text-yellow-800">
          <span className="font-semibold">Note:</span> Credentials are not included in bulk results for security reasons.
          Use single-device provisioning to obtain device credentials.
        </p>
      </div>

      {/* Results table */}
      <div className="border border-gray-300 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-300">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Row</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Name</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Status</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Device ID</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Error</th>
              </tr>
            </thead>
            <tbody>
              {results.map((result) => (
                <tr
                  key={result.row}
                  className={`border-b border-gray-200 last:border-0 ${
                    result.status === 'error' ? 'bg-red-50' : ''
                  }`}
                >
                  <td className="px-4 py-3 text-gray-600">{result.row}</td>
                  <td className="px-4 py-3 text-gray-900">{result.name || '-'}</td>
                  <td className="px-4 py-3">
                    {result.status === 'success' ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        Success
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        Error
                      </span>
                    )}
                  </td>
                  <td
                    className="px-4 py-3 text-xs font-mono text-gray-600"
                    title={result.device_id || undefined}
                  >
                    {result.device_id ? (
                      <>
                        {result.device_id.substring(0, 8)}...
                      </>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-red-700">
                    {result.error || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex items-center justify-between">
        <div>
          {failCount > 0 && (
            <Button onClick={downloadFailedRows} variant="secondary">
              Download Failed Rows
            </Button>
          )}
        </div>
        <Button onClick={reset}>
          Upload Another File
        </Button>
      </div>
    </div>
  );
}
