/**
 * Analytics Dashboard Page
 * Displays incident statistics, resource utilization, and performance metrics
 */

import { useState, useEffect } from 'react';
import { Card, Spinner, Badge } from '../components/ui';
import api from '../services/api';

type TimeRange = 'hour' | 'day' | 'week' | 'month' | 'quarter' | 'year';

interface IncidentStats {
  total: number;
  open: number;
  closed: number;
  by_category: Record<string, number>;
  by_priority: Record<number, number>;
  by_status: Record<string, number>;
  avg_resolution_minutes: number;
  avg_response_minutes: number;
}

interface ResourceStats {
  total: number;
  available: number;
  dispatched: number;
  on_scene: number;
  out_of_service: number;
  by_type: Record<string, number>;
  utilization_rate: number;
}

interface AlertStats {
  total: number;
  pending: number;
  acknowledged: number;
  resolved: number;
  by_severity: Record<string, number>;
}

interface DashboardSummary {
  period_start: string;
  period_end: string;
  incidents: IncidentStats;
  resources: ResourceStats;
  alerts: AlertStats;
  key_metrics: Record<string, number>;
}

interface TimeSeriesPoint {
  timestamp: string;
  value: number;
}

interface TimeSeries {
  name: string;
  metric_type: string;
  unit: string;
  points: TimeSeriesPoint[];
}

export function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState<TimeRange>('week');
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [incidentTrend, setIncidentTrend] = useState<TimeSeries | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);

    try {
      const [summaryRes, trendRes] = await Promise.all([
        api.get<DashboardSummary>(`/analytics/dashboard?time_range=${timeRange}`),
        api.get<TimeSeries>(`/analytics/incidents/trend?time_range=${timeRange}`),
      ]);

      setSummary(summaryRes.data);
      setIncidentTrend(trendRes.data);
    } catch (err) {
      setError('Failed to load analytics data');
      console.error('Analytics error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value as TimeRange)}
          className="w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
        >
          <option value="hour">Last Hour</option>
          <option value="day">Last 24 Hours</option>
          <option value="week">Last Week</option>
          <option value="month">Last Month</option>
          <option value="quarter">Last Quarter</option>
          <option value="year">Last Year</option>
        </select>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          title="Total Incidents"
          value={summary?.incidents.total || 0}
          subtitle={`${summary?.incidents.open || 0} open`}
          color="blue"
        />
        <MetricCard
          title="Resource Utilization"
          value={`${summary?.resources.utilization_rate || 0}%`}
          subtitle={`${summary?.resources.available || 0} available`}
          color="green"
        />
        <MetricCard
          title="Pending Alerts"
          value={summary?.alerts.pending || 0}
          subtitle={`of ${summary?.alerts.total || 0} total`}
          color="yellow"
        />
        <MetricCard
          title="Avg Response Time"
          value={`${Math.round(summary?.incidents.avg_response_minutes || 0)} min`}
          subtitle="from dispatch"
          color="purple"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Incident Trend */}
        <Card>
          <h3 className="text-lg font-semibold mb-4">Incident Trend</h3>
          <div className="h-64">
            {incidentTrend && incidentTrend.points.length > 0 ? (
              <SimpleBarChart data={incidentTrend.points} />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                No data available
              </div>
            )}
          </div>
        </Card>

        {/* Incidents by Category */}
        <Card>
          <h3 className="text-lg font-semibold mb-4">Incidents by Category</h3>
          <div className="space-y-3">
            {summary?.incidents.by_category &&
              Object.entries(summary.incidents.by_category).map(([category, count]) => (
                <div key={category} className="flex items-center justify-between">
                  <span className="text-sm capitalize">{category.replace('_', ' ')}</span>
                  <div className="flex items-center gap-2">
                    <div
                      className="h-2 bg-blue-500 rounded-full"
                      style={{
                        width: `${(count / (summary?.incidents.total || 1)) * 100}px`,
                        minWidth: '4px',
                      }}
                    />
                    <span className="text-sm font-medium w-8 text-right">{count}</span>
                  </div>
                </div>
              ))}
          </div>
        </Card>
      </div>

      {/* Resource & Alert Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Resource Status */}
        <Card>
          <h3 className="text-lg font-semibold mb-4">Resource Status</h3>
          <div className="grid grid-cols-2 gap-4">
            <StatusItem
              label="Available"
              value={summary?.resources.available || 0}
              color="green"
            />
            <StatusItem
              label="Dispatched"
              value={summary?.resources.dispatched || 0}
              color="blue"
            />
            <StatusItem
              label="On Scene"
              value={summary?.resources.on_scene || 0}
              color="purple"
            />
            <StatusItem
              label="Out of Service"
              value={summary?.resources.out_of_service || 0}
              color="gray"
            />
          </div>

          <div className="mt-4 pt-4 border-t">
            <h4 className="text-sm font-medium text-gray-600 mb-2">By Type</h4>
            <div className="flex flex-wrap gap-2">
              {summary?.resources.by_type &&
                Object.entries(summary.resources.by_type).map(([type, count]) => (
                  <Badge key={type} variant="secondary">
                    {type}: {count}
                  </Badge>
                ))}
            </div>
          </div>
        </Card>

        {/* Alert Severity */}
        <Card>
          <h3 className="text-lg font-semibold mb-4">Alerts by Severity</h3>
          <div className="space-y-3">
            {['critical', 'high', 'medium', 'low', 'info'].map((severity) => {
              const count = summary?.alerts.by_severity?.[severity] || 0;
              const total = summary?.alerts.total || 1;
              return (
                <div key={severity} className="flex items-center gap-3">
                  <Badge variant={getSeverityVariant(severity)} className="w-20 justify-center">
                    {severity}
                  </Badge>
                  <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${getSeverityColor(severity)}`}
                      style={{ width: `${(count / total) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium w-8 text-right">{count}</span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Incident Priority Distribution */}
      <Card>
        <h3 className="text-lg font-semibold mb-4">Incidents by Priority</h3>
        <div className="flex items-end gap-2 h-32">
          {[1, 2, 3, 4, 5].map((priority) => {
            const count = summary?.incidents.by_priority?.[priority] || 0;
            const maxCount = Math.max(
              ...Object.values(summary?.incidents.by_priority || { 1: 1 })
            );
            const height = maxCount > 0 ? (count / maxCount) * 100 : 0;

            return (
              <div key={priority} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className={`w-full rounded-t ${getPriorityColor(priority)}`}
                  style={{ height: `${height}%`, minHeight: count > 0 ? '8px' : '0' }}
                />
                <span className="text-xs font-medium">P{priority}</span>
                <span className="text-xs text-gray-500">{count}</span>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

// Helper Components
function MetricCard({
  title,
  value,
  subtitle,
  color,
}: {
  title: string;
  value: string | number;
  subtitle: string;
  color: 'blue' | 'green' | 'yellow' | 'purple';
}) {
  const colorClasses = {
    blue: 'bg-blue-50 border-blue-200',
    green: 'bg-green-50 border-green-200',
    yellow: 'bg-yellow-50 border-yellow-200',
    purple: 'bg-purple-50 border-purple-200',
  };

  return (
    <div className={`rounded-lg border p-4 ${colorClasses[color]}`}>
      <p className="text-sm text-gray-600">{title}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
    </div>
  );
}

function StatusItem({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: 'green' | 'blue' | 'purple' | 'gray';
}) {
  const dotColors = {
    green: 'bg-green-500',
    blue: 'bg-blue-500',
    purple: 'bg-purple-500',
    gray: 'bg-gray-400',
  };

  return (
    <div className="flex items-center gap-2">
      <div className={`w-3 h-3 rounded-full ${dotColors[color]}`} />
      <span className="text-sm">{label}</span>
      <span className="ml-auto font-semibold">{value}</span>
    </div>
  );
}

function SimpleBarChart({ data }: { data: TimeSeriesPoint[] }) {
  if (data.length === 0) return null;

  const maxValue = Math.max(...data.map((p) => p.value), 1);

  return (
    <div className="flex items-end gap-1 h-full p-4">
      {data.map((point, idx) => {
        const height = (point.value / maxValue) * 100;
        const date = new Date(point.timestamp);
        const label = date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });

        return (
          <div
            key={idx}
            className="flex-1 flex flex-col items-center justify-end gap-1 min-w-0"
          >
            <span className="text-xs font-medium">{point.value}</span>
            <div
              className="w-full bg-blue-500 rounded-t transition-all"
              style={{ height: `${height}%`, minHeight: point.value > 0 ? '4px' : '0' }}
            />
            <span className="text-xs text-gray-500 truncate w-full text-center">{label}</span>
          </div>
        );
      })}
    </div>
  );
}

function getSeverityVariant(severity: string): 'danger' | 'warning' | 'secondary' | 'info' {
  switch (severity) {
    case 'critical':
      return 'danger';
    case 'high':
      return 'warning';
    case 'medium':
      return 'info';
    default:
      return 'secondary';
  }
}

function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'bg-red-500';
    case 'high':
      return 'bg-orange-500';
    case 'medium':
      return 'bg-yellow-500';
    case 'low':
      return 'bg-blue-500';
    default:
      return 'bg-gray-400';
  }
}

function getPriorityColor(priority: number): string {
  switch (priority) {
    case 1:
      return 'bg-red-500';
    case 2:
      return 'bg-orange-500';
    case 3:
      return 'bg-yellow-500';
    case 4:
      return 'bg-blue-500';
    case 5:
      return 'bg-gray-400';
    default:
      return 'bg-gray-300';
  }
}
