/**
 * Audit Logs Page
 *
 * Displays system audit logs with filtering and pagination.
 * Only accessible to users with system:audit permission.
 */

import { useEffect, useState, useCallback } from 'react';
import { auditApi } from '../services/api';
import {
  Card,
  CardContent,
  Badge,
  Button,
  Select,
  Input,
  Spinner,
} from '../components/ui';
import { formatRelativeTime, cn } from '../utils';
import type { AuditLog, AuditAction, AuditLogListResponse } from '../types';

const ACTION_LABELS: Record<AuditAction, string> = {
  login: 'Login',
  logout: 'Logout',
  login_failed: 'Login Failed',
  password_changed: 'Password Changed',
  mfa_enabled: 'MFA Enabled',
  mfa_disabled: 'MFA Disabled',
  user_created: 'User Created',
  user_updated: 'User Updated',
  user_deleted: 'User Deleted',
  user_role_changed: 'Role Changed',
  incident_created: 'Incident Created',
  incident_updated: 'Incident Updated',
  incident_assigned: 'Incident Assigned',
  incident_escalated: 'Incident Escalated',
  incident_closed: 'Incident Closed',
  alert_received: 'Alert Received',
  alert_acknowledged: 'Alert Acknowledged',
  alert_dismissed: 'Alert Dismissed',
  alert_to_incident: 'Alert to Incident',
  resource_created: 'Resource Created',
  resource_updated: 'Resource Updated',
  resource_deleted: 'Resource Deleted',
  resource_assigned: 'Resource Assigned',
  resource_status_changed: 'Resource Status Changed',
  system_config_changed: 'Config Changed',
  api_access: 'API Access',
  permission_denied: 'Permission Denied',
};

const ACTION_COLORS: Partial<Record<AuditAction, string>> = {
  login: 'bg-green-100 text-green-800',
  logout: 'bg-gray-100 text-gray-800',
  login_failed: 'bg-red-100 text-red-800',
  password_changed: 'bg-yellow-100 text-yellow-800',
  mfa_enabled: 'bg-blue-100 text-blue-800',
  mfa_disabled: 'bg-orange-100 text-orange-800',
  user_created: 'bg-green-100 text-green-800',
  user_updated: 'bg-blue-100 text-blue-800',
  user_deleted: 'bg-red-100 text-red-800',
  incident_created: 'bg-purple-100 text-purple-800',
  incident_closed: 'bg-gray-100 text-gray-800',
  alert_received: 'bg-yellow-100 text-yellow-800',
  alert_acknowledged: 'bg-blue-100 text-blue-800',
  permission_denied: 'bg-red-100 text-red-800',
};

const actionOptions = [
  { value: '', label: 'All Actions' },
  { value: 'login', label: 'Login' },
  { value: 'logout', label: 'Logout' },
  { value: 'login_failed', label: 'Login Failed' },
  { value: 'password_changed', label: 'Password Changed' },
  { value: 'user_created', label: 'User Created' },
  { value: 'user_updated', label: 'User Updated' },
  { value: 'user_deleted', label: 'User Deleted' },
  { value: 'incident_created', label: 'Incident Created' },
  { value: 'incident_updated', label: 'Incident Updated' },
  { value: 'alert_acknowledged', label: 'Alert Acknowledged' },
  { value: 'permission_denied', label: 'Permission Denied' },
];

const entityTypeOptions = [
  { value: '', label: 'All Entity Types' },
  { value: 'user', label: 'User' },
  { value: 'incident', label: 'Incident' },
  { value: 'alert', label: 'Alert' },
  { value: 'resource', label: 'Resource' },
  { value: 'building', label: 'Building' },
];

export function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [totalPages, setTotalPages] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [actionFilter, setActionFilter] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState('');
  const [userIdFilter, setUserIdFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Selected log for detail view
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize };
      if (actionFilter) params.action = actionFilter;
      if (entityTypeFilter) params.entity_type = entityTypeFilter;
      if (userIdFilter) params.user_id = userIdFilter;
      if (startDate) params.start_date = new Date(startDate).toISOString();
      if (endDate) params.end_date = new Date(endDate).toISOString();

      const response: AuditLogListResponse = await auditApi.list(params);
      setLogs(response.items);
      setTotal(response.total);
      setTotalPages(response.total_pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit logs');
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, actionFilter, entityTypeFilter, userIdFilter, startDate, endDate]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const clearFilters = () => {
    setActionFilter('');
    setEntityTypeFilter('');
    setUserIdFilter('');
    setStartDate('');
    setEndDate('');
    setPage(1);
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Audit Logs</h1>
          <p className="text-gray-600 mt-1">
            System activity and security events ({total.toLocaleString()} total)
          </p>
        </div>
        <Button onClick={fetchLogs} variant="outline" disabled={isLoading}>
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <Select
              value={actionFilter}
              onChange={(e) => {
                setActionFilter(e.target.value);
                setPage(1);
              }}
              options={actionOptions}
              label="Action"
            />
            <Select
              value={entityTypeFilter}
              onChange={(e) => {
                setEntityTypeFilter(e.target.value);
                setPage(1);
              }}
              options={entityTypeOptions}
              label="Entity Type"
            />
            <Input
              value={userIdFilter}
              onChange={(e) => {
                setUserIdFilter(e.target.value);
                setPage(1);
              }}
              placeholder="User ID"
              label="User ID"
            />
            <Input
              type="date"
              value={startDate}
              onChange={(e) => {
                setStartDate(e.target.value);
                setPage(1);
              }}
              label="Start Date"
            />
            <Input
              type="date"
              value={endDate}
              onChange={(e) => {
                setEndDate(e.target.value);
                setPage(1);
              }}
              label="End Date"
            />
            <div className="flex items-end">
              <Button onClick={clearFilters} variant="outline" size="sm">
                Clear Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      {/* Logs Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Spinner size="lg" />
            </div>
          ) : logs.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              No audit logs found matching the filters.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Timestamp
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Action
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Description
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Entity
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      IP Address
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Details
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {logs.map((log) => (
                    <tr
                      key={log.id}
                      className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => setSelectedLog(log)}
                    >
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        <div>{formatTimestamp(log.timestamp)}</div>
                        <div className="text-xs text-gray-400">
                          {formatRelativeTime(log.timestamp)}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <Badge
                          className={cn(
                            'text-xs',
                            ACTION_COLORS[log.action] || 'bg-gray-100 text-gray-800'
                          )}
                        >
                          {ACTION_LABELS[log.action] || log.action}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 max-w-md truncate">
                        {log.description || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {log.entity_type ? (
                          <span>
                            {log.entity_type}
                            {log.entity_id && (
                              <span className="text-gray-400 ml-1">
                                #{log.entity_id.slice(0, 8)}
                              </span>
                            )}
                          </span>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500 font-mono">
                        {log.ip_address || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedLog(log);
                          }}
                        >
                          View
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-600">
            Showing {(page - 1) * pageSize + 1} to{' '}
            {Math.min(page * pageSize, total)} of {total} logs
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
            >
              Previous
            </Button>
            <span className="px-3 py-1 text-sm text-gray-600">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page === totalPages}
              onClick={() => setPage(page + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {selectedLog && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setSelectedLog(null)}
        >
          <div
            className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Audit Log Details</h2>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedLog(null)}
                >
                  Close
                </Button>
              </div>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase">
                    Timestamp
                  </label>
                  <p className="mt-1 text-sm">{formatTimestamp(selectedLog.timestamp)}</p>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase">
                    Action
                  </label>
                  <Badge
                    className={cn(
                      'mt-1',
                      ACTION_COLORS[selectedLog.action] || 'bg-gray-100 text-gray-800'
                    )}
                  >
                    {ACTION_LABELS[selectedLog.action] || selectedLog.action}
                  </Badge>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase">
                    User ID
                  </label>
                  <p className="mt-1 text-sm font-mono">
                    {selectedLog.user_id || 'System'}
                  </p>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase">
                    IP Address
                  </label>
                  <p className="mt-1 text-sm font-mono">
                    {selectedLog.ip_address || '-'}
                  </p>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase">
                    Entity Type
                  </label>
                  <p className="mt-1 text-sm">{selectedLog.entity_type || '-'}</p>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase">
                    Entity ID
                  </label>
                  <p className="mt-1 text-sm font-mono">
                    {selectedLog.entity_id || '-'}
                  </p>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase">
                  Description
                </label>
                <p className="mt-1 text-sm">{selectedLog.description || '-'}</p>
              </div>

              {selectedLog.old_values && Object.keys(selectedLog.old_values).length > 0 && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase">
                    Previous Values
                  </label>
                  <pre className="mt-1 text-xs bg-red-50 p-3 rounded-lg overflow-x-auto">
                    {JSON.stringify(selectedLog.old_values, null, 2)}
                  </pre>
                </div>
              )}

              {selectedLog.new_values && Object.keys(selectedLog.new_values).length > 0 && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase">
                    New Values
                  </label>
                  <pre className="mt-1 text-xs bg-green-50 p-3 rounded-lg overflow-x-auto">
                    {JSON.stringify(selectedLog.new_values, null, 2)}
                  </pre>
                </div>
              )}

              {selectedLog.metadata && Object.keys(selectedLog.metadata).length > 0 && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase">
                    Additional Data
                  </label>
                  <pre className="mt-1 text-xs bg-gray-50 p-3 rounded-lg overflow-x-auto">
                    {JSON.stringify(selectedLog.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AuditLogsPage;
