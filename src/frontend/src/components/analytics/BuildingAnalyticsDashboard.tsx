/**
 * BuildingAnalyticsDashboard Component
 *
 * Combines all analytics widgets into a unified dashboard for building analytics.
 * Supports configurable time ranges and provides refresh functionality.
 */

import { useState, useEffect, useCallback } from 'react';
import { cn } from '../../utils';
import { BuildingStatsCards } from './BuildingStatsCards';
import { DeviceHealthChart, type DeviceHealthData } from './DeviceHealthChart';
import { IncidentTrendChart } from './IncidentTrendChart';
import { InspectionComplianceWidget } from './InspectionComplianceWidget';
import { AlertSeverityChart } from './AlertSeverityChart';

// Types
type TimeRange = '7d' | '30d' | '90d';

interface BuildingStats {
  devices: {
    total: number;
    online: number;
    health_percentage: number;
  };
  incidents: {
    total: number;
    active: number;
  };
  alerts: {
    total: number;
    pending: number;
  };
  inspections: {
    compliance_rate: number;
    overdue: number;
  };
}

interface IncidentTrendData {
  total: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_priority: Record<string, number>;
  trend: Array<{ date: string; count: number }>;
}

interface InspectionComplianceData {
  total: number;
  completed: number;
  scheduled: number;
  overdue: number;
  compliance_rate: number;
  upcoming: Array<{ id: string; type: string; scheduled_date: string }>;
  overdue_list: Array<{ id: string; type: string; scheduled_date: string }>;
}

interface AlertBreakdownData {
  total: number;
  pending: number;
  by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
  by_status: {
    pending: number;
    acknowledged: number;
    resolved: number;
    dismissed: number;
  };
  recent: Array<{ id: string; severity: string; created_at: string; title: string }>;
}

interface AnalyticsData {
  stats: BuildingStats | null;
  deviceHealth: DeviceHealthData | null;
  incidentTrend: IncidentTrendData | null;
  inspectionCompliance: InspectionComplianceData | null;
  alertBreakdown: AlertBreakdownData | null;
}

export interface BuildingAnalyticsDashboardProps {
  buildingId: string;
  className?: string;
}

// Time range options
const TIME_RANGE_OPTIONS: Array<{ value: TimeRange; label: string }> = [
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
  { value: '90d', label: '90d' },
];

// Convert time range to days
function timeRangeToDays(range: TimeRange): number {
  switch (range) {
    case '7d':
      return 7;
    case '30d':
      return 30;
    case '90d':
      return 90;
    default:
      return 7;
  }
}

// Refresh icon component
function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
      />
    </svg>
  );
}

// Error message component
function ErrorMessage({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
      <svg
        className="w-5 h-5 text-red-500 flex-shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <div className="flex-1">
        <p className="text-sm text-red-800">{message}</p>
      </div>
      <button
        onClick={onRetry}
        className="px-3 py-1 text-sm font-medium text-red-700 hover:text-red-900 hover:bg-red-100 rounded transition-colors"
      >
        Retry
      </button>
    </div>
  );
}

export function BuildingAnalyticsDashboard({
  buildingId,
  className,
}: BuildingAnalyticsDashboardProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('7d');
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalyticsData>({
    stats: null,
    deviceHealth: null,
    incidentTrend: null,
    inspectionCompliance: null,
    alertBreakdown: null,
  });

  // Fetch analytics data
  const fetchAnalytics = useCallback(
    async (showRefreshIndicator = false) => {
      if (showRefreshIndicator) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      const days = timeRangeToDays(timeRange);
      const baseUrl = import.meta.env.VITE_API_URL || '/api/v1';

      try {
        // Fetch all analytics data in parallel
        const response = await fetch(
          `${baseUrl}/buildings/${buildingId}/analytics?days=${days}`,
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem('eriop_access_token')}`,
              'Content-Type': 'application/json',
            },
          }
        );

        if (!response.ok) {
          // If the combined endpoint doesn't exist, try fetching individual endpoints
          if (response.status === 404) {
            // Fetch individual endpoints
            const [statsRes, devicesRes, incidentsRes, inspectionsRes, alertsRes] =
              await Promise.allSettled([
                fetch(`${baseUrl}/buildings/${buildingId}/stats`, {
                  headers: {
                    Authorization: `Bearer ${localStorage.getItem('eriop_access_token')}`,
                  },
                }),
                fetch(`${baseUrl}/buildings/${buildingId}/devices/health?days=${days}`, {
                  headers: {
                    Authorization: `Bearer ${localStorage.getItem('eriop_access_token')}`,
                  },
                }),
                fetch(`${baseUrl}/buildings/${buildingId}/incidents/analytics?days=${days}`, {
                  headers: {
                    Authorization: `Bearer ${localStorage.getItem('eriop_access_token')}`,
                  },
                }),
                fetch(`${baseUrl}/buildings/${buildingId}/inspections/analytics`, {
                  headers: {
                    Authorization: `Bearer ${localStorage.getItem('eriop_access_token')}`,
                  },
                }),
                fetch(`${baseUrl}/buildings/${buildingId}/alerts/analytics?days=${days}`, {
                  headers: {
                    Authorization: `Bearer ${localStorage.getItem('eriop_access_token')}`,
                  },
                }),
              ]);

            const analyticsData: AnalyticsData = {
              stats: null,
              deviceHealth: null,
              incidentTrend: null,
              inspectionCompliance: null,
              alertBreakdown: null,
            };

            // Process stats
            if (statsRes.status === 'fulfilled' && statsRes.value.ok) {
              analyticsData.stats = await statsRes.value.json();
            }

            // Process device health
            if (devicesRes.status === 'fulfilled' && devicesRes.value.ok) {
              analyticsData.deviceHealth = await devicesRes.value.json();
            }

            // Process incident trend
            if (incidentsRes.status === 'fulfilled' && incidentsRes.value.ok) {
              analyticsData.incidentTrend = await incidentsRes.value.json();
            }

            // Process inspection compliance
            if (inspectionsRes.status === 'fulfilled' && inspectionsRes.value.ok) {
              analyticsData.inspectionCompliance = await inspectionsRes.value.json();
            }

            // Process alert breakdown
            if (alertsRes.status === 'fulfilled' && alertsRes.value.ok) {
              analyticsData.alertBreakdown = await alertsRes.value.json();
            }

            setData(analyticsData);
          } else {
            throw new Error(`Failed to fetch analytics: ${response.statusText}`);
          }
        } else {
          // Combined endpoint response
          const analyticsResponse = await response.json();
          setData({
            stats: analyticsResponse.stats || null,
            deviceHealth: analyticsResponse.device_health || null,
            incidentTrend: analyticsResponse.incident_trend || null,
            inspectionCompliance: analyticsResponse.inspection_compliance || null,
            alertBreakdown: analyticsResponse.alert_breakdown || null,
          });
        }
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to load analytics data';
        setError(errorMessage);
        console.error('Analytics fetch error:', err);
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [buildingId, timeRange]
  );

  // Fetch data on mount and when time range changes
  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  // Handle refresh
  const handleRefresh = () => {
    fetchAnalytics(true);
  };

  // Handle time range change
  const handleTimeRangeChange = (range: TimeRange) => {
    setTimeRange(range);
  };

  // Handle incident trend time range change (internal to chart)
  const handleIncidentTimeRangeChange = (range: '7d' | '30d' | '90d') => {
    setTimeRange(range);
  };

  // Handle inspection click
  const handleInspectionClick = (id: string) => {
    // Navigate to inspection detail or open modal
    console.log('Inspection clicked:', id);
  };

  // Handle alert click
  const handleAlertClick = (id: string) => {
    // Navigate to alert detail or open modal
    console.log('Alert clicked:', id);
  };

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header with time range selector and refresh button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">Time Range:</span>
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            {TIME_RANGE_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => handleTimeRangeChange(option.value)}
                className={cn(
                  'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                  timeRange === option.value
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className={cn(
            'inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border transition-colors',
            'bg-white text-gray-700 border-gray-300 hover:bg-gray-50',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <RefreshIcon
            className={cn('w-4 h-4', isRefreshing && 'animate-spin')}
          />
          Refresh
        </button>
      </div>

      {/* Error message */}
      {error && <ErrorMessage message={error} onRetry={handleRefresh} />}

      {/* Stats Cards - Full width, 4 cards in row */}
      <BuildingStatsCards stats={data.stats} isLoading={isLoading} />

      {/* Device Health and Alert Severity - Side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DeviceHealthChart data={data.deviceHealth} isLoading={isLoading} />
        <AlertSeverityChart
          data={data.alertBreakdown}
          isLoading={isLoading}
          onAlertClick={handleAlertClick}
        />
      </div>

      {/* Incident Trend - Full width */}
      <IncidentTrendChart
        data={data.incidentTrend}
        isLoading={isLoading}
        timeRange={timeRange}
        onTimeRangeChange={handleIncidentTimeRangeChange}
      />

      {/* Inspection Compliance - Full width */}
      <InspectionComplianceWidget
        data={data.inspectionCompliance}
        isLoading={isLoading}
        onInspectionClick={handleInspectionClick}
      />
    </div>
  );
}

export default BuildingAnalyticsDashboard;
