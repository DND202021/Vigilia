/**
 * AlertSeverityChart Component
 *
 * Displays alert breakdown with horizontal bar chart showing severity distribution,
 * status summary, and recent alerts list.
 */

import { useEffect, useState } from 'react';
import { cn, formatRelativeTime } from '../../utils';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';

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

interface AlertSeverityChartProps {
  data: AlertBreakdownData | null;
  isLoading?: boolean;
  onAlertClick?: (id: string) => void;
  className?: string;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#dc2626',
  high: '#f97316',
  medium: '#eab308',
  low: '#3b82f6',
  info: '#6b7280',
};

const SEVERITY_LABELS: Record<string, string> = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  info: 'Info',
};

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info'] as const;

function LoadingSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="h-6 w-36 bg-gray-200 rounded animate-pulse" />
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Bar chart skeleton */}
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-16 h-4 bg-gray-200 rounded animate-pulse" />
                <div className="flex-1 h-6 bg-gray-100 rounded animate-pulse" />
                <div className="w-12 h-4 bg-gray-200 rounded animate-pulse" />
              </div>
            ))}
          </div>

          {/* Status summary skeleton */}
          <div className="border-t pt-4 mt-4">
            <div className="h-4 w-28 bg-gray-200 rounded animate-pulse mb-3" />
            <div className="flex gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-6 w-24 bg-gray-100 rounded animate-pulse" />
              ))}
            </div>
          </div>

          {/* Recent alerts skeleton */}
          <div className="border-t pt-4">
            <div className="h-4 w-24 bg-gray-200 rounded animate-pulse mb-3" />
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-12 bg-gray-100 rounded animate-pulse" />
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const color = SEVERITY_COLORS[severity] || SEVERITY_COLORS.info;
  const label = SEVERITY_LABELS[severity] || severity;

  return (
    <span
      className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full text-white"
      style={{ backgroundColor: color }}
    >
      {label}
    </span>
  );
}

export function AlertSeverityChart({
  data,
  isLoading = false,
  onAlertClick,
  className,
}: AlertSeverityChartProps) {
  const [animatedWidths, setAnimatedWidths] = useState<Record<string, number>>({});

  // Calculate max value for scaling
  const maxCount = data
    ? Math.max(...Object.values(data.by_severity), 1)
    : 1;

  // Animate bar widths on mount/data change
  useEffect(() => {
    if (!data) return;

    // Start with zero widths
    setAnimatedWidths(
      SEVERITY_ORDER.reduce((acc, sev) => ({ ...acc, [sev]: 0 }), {})
    );

    // Animate to actual widths
    const timeout = setTimeout(() => {
      setAnimatedWidths(
        SEVERITY_ORDER.reduce((acc, sev) => ({
          ...acc,
          [sev]: (data.by_severity[sev] / maxCount) * 100,
        }), {})
      );
    }, 50);

    return () => clearTimeout(timeout);
  }, [data, maxCount]);

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (!data) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Alert Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
            No alert data available
          </div>
        </CardContent>
      </Card>
    );
  }

  const recentAlerts = data.recent.slice(0, 3);

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle>Alert Breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Total count */}
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Total Alerts</span>
            <span className="font-semibold text-gray-900">{data.total}</span>
          </div>

          {/* Horizontal bar chart */}
          <div className="space-y-3">
            {SEVERITY_ORDER.map((severity) => {
              const count = data.by_severity[severity];
              const percentage = data.total > 0 ? ((count / data.total) * 100).toFixed(1) : '0.0';
              const barWidth = animatedWidths[severity] || 0;

              return (
                <div key={severity} className="flex items-center gap-3">
                  <span className="w-16 text-sm text-gray-600 capitalize">{severity}</span>
                  <div className="flex-1 relative">
                    <svg
                      viewBox="0 0 200 24"
                      className="w-full h-6"
                      preserveAspectRatio="none"
                    >
                      {/* Background bar */}
                      <rect
                        x="0"
                        y="4"
                        width="200"
                        height="16"
                        rx="4"
                        fill="#f3f4f6"
                      />
                      {/* Foreground bar */}
                      <rect
                        x="0"
                        y="4"
                        width={barWidth * 2}
                        height="16"
                        rx="4"
                        fill={SEVERITY_COLORS[severity]}
                        style={{
                          transition: 'width 0.5s ease-out',
                        }}
                      />
                    </svg>
                  </div>
                  <div className="w-20 text-right">
                    <span className="text-sm font-medium text-gray-900">{count}</span>
                    <span className="text-xs text-gray-500 ml-1">({percentage}%)</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Status summary */}
          <div className="border-t pt-4 mt-4">
            <h4 className="text-sm font-medium text-gray-700 mb-3">Status Summary</h4>
            <div className="flex flex-wrap gap-4">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-yellow-500" />
                <span className="text-sm text-gray-600">
                  Pending: <span className="font-medium text-gray-900">{data.by_status.pending}</span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                <span className="text-sm text-gray-600">
                  Acknowledged: <span className="font-medium text-gray-900">{data.by_status.acknowledged}</span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500" />
                <span className="text-sm text-gray-600">
                  Resolved: <span className="font-medium text-gray-900">{data.by_status.resolved}</span>
                </span>
              </div>
            </div>
          </div>

          {/* Recent alerts */}
          {recentAlerts.length > 0 && (
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium text-gray-700 mb-3">Recent Alerts</h4>
              <div className="space-y-2">
                {recentAlerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={cn(
                      'flex items-center gap-3 p-2 rounded-lg bg-gray-50',
                      onAlertClick && 'cursor-pointer hover:bg-gray-100 transition-colors'
                    )}
                    onClick={() => onAlertClick?.(alert.id)}
                    role={onAlertClick ? 'button' : undefined}
                    tabIndex={onAlertClick ? 0 : undefined}
                    onKeyDown={(e) => {
                      if (onAlertClick && (e.key === 'Enter' || e.key === ' ')) {
                        e.preventDefault();
                        onAlertClick(alert.id);
                      }
                    }}
                  >
                    <SeverityBadge severity={alert.severity} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-900 truncate">{alert.title}</p>
                      <p className="text-xs text-gray-500">
                        {formatRelativeTime(alert.created_at)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default AlertSeverityChart;
