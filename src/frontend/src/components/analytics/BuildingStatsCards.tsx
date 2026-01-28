/**
 * BuildingStatsCards Component
 * Displays key building metrics in a responsive card grid layout.
 * Shows devices, incidents, alerts, and inspection stats with visual indicators.
 */

import { cn } from '../../utils';

// Types
interface BuildingStats {
  devices: {
    total: number;
    online: number;
    health_percentage: number;
  };
  incidents: {
    total: number;
    active: number; // new + assigned + en_route + on_scene
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

interface BuildingStatsCardsProps {
  stats: BuildingStats | null;
  isLoading?: boolean;
  className?: string;
}

// Icon components (inline SVG for no external dependencies)
function DeviceIcon({ className }: { className?: string }) {
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
        d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
      />
    </svg>
  );
}

function IncidentIcon({ className }: { className?: string }) {
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
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      />
    </svg>
  );
}

function AlertIcon({ className }: { className?: string }) {
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
        d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
      />
    </svg>
  );
}

function InspectionIcon({ className }: { className?: string }) {
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
        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
      />
    </svg>
  );
}

// Progress Ring Component for health percentage
function ProgressRing({
  percentage,
  size = 40,
  strokeWidth = 4,
  className,
}: {
  percentage: number;
  size?: number;
  strokeWidth?: number;
  className?: string;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  const getColor = (pct: number) => {
    if (pct >= 90) return 'text-green-500';
    if (pct >= 70) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="none"
          className="text-gray-200"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="none"
          strokeLinecap="round"
          className={getColor(percentage)}
          style={{
            strokeDasharray: circumference,
            strokeDashoffset,
            transition: 'stroke-dashoffset 0.5s ease-in-out',
          }}
        />
      </svg>
      <span className="absolute text-xs font-semibold text-gray-700">
        {Math.round(percentage)}%
      </span>
    </div>
  );
}

// Loading Skeleton
function StatCardSkeleton() {
  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4 animate-pulse">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="h-4 bg-gray-200 rounded w-20 mb-3" />
          <div className="h-8 bg-gray-200 rounded w-16 mb-2" />
          <div className="h-3 bg-gray-200 rounded w-24" />
        </div>
        <div className="w-10 h-10 bg-gray-200 rounded-full" />
      </div>
    </div>
  );
}

// Individual Stat Card
interface StatCardProps {
  icon: React.ReactNode;
  iconBgColor: string;
  label: string;
  value: number | string;
  secondaryLabel: string;
  secondaryValue: number | string;
  secondaryVariant?: 'default' | 'success' | 'warning' | 'danger';
  extraContent?: React.ReactNode;
}

function StatCard({
  icon,
  iconBgColor,
  label,
  value,
  secondaryLabel,
  secondaryValue,
  secondaryVariant = 'default',
  extraContent,
}: StatCardProps) {
  const secondaryColors = {
    default: 'text-gray-600',
    success: 'text-green-600',
    warning: 'text-yellow-600',
    danger: 'text-red-600',
  };

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500 mb-1">{label}</p>
          <p className="text-3xl font-bold text-gray-900">{value}</p>
          <p className={cn('text-sm mt-1', secondaryColors[secondaryVariant])}>
            <span className="font-medium">{secondaryValue}</span> {secondaryLabel}
          </p>
        </div>
        <div className={cn('p-2.5 rounded-full', iconBgColor)}>
          {icon}
        </div>
      </div>
      {extraContent && <div className="mt-3 pt-3 border-t border-gray-100">{extraContent}</div>}
    </div>
  );
}

// Main Component
export function BuildingStatsCards({
  stats,
  isLoading = false,
  className,
}: BuildingStatsCardsProps) {
  if (isLoading) {
    return (
      <div className={cn('grid grid-cols-2 lg:grid-cols-4 gap-4', className)}>
        <StatCardSkeleton />
        <StatCardSkeleton />
        <StatCardSkeleton />
        <StatCardSkeleton />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className={cn('grid grid-cols-2 lg:grid-cols-4 gap-4', className)}>
        <div className="col-span-full text-center py-8 text-gray-500">
          No statistics available
        </div>
      </div>
    );
  }

  const getDeviceHealthVariant = (health: number): 'success' | 'warning' | 'danger' => {
    if (health >= 90) return 'success';
    if (health >= 70) return 'warning';
    return 'danger';
  };

  const getIncidentVariant = (active: number): 'success' | 'warning' | 'danger' => {
    if (active === 0) return 'success';
    if (active <= 2) return 'warning';
    return 'danger';
  };

  const getAlertVariant = (pending: number): 'success' | 'warning' | 'danger' => {
    if (pending === 0) return 'success';
    if (pending <= 5) return 'warning';
    return 'danger';
  };

  return (
    <div className={cn('grid grid-cols-2 lg:grid-cols-4 gap-4', className)}>
      {/* Devices Card */}
      <StatCard
        icon={<DeviceIcon className="w-5 h-5 text-blue-600" />}
        iconBgColor="bg-blue-100"
        label="Devices"
        value={stats.devices.total}
        secondaryLabel="online"
        secondaryValue={stats.devices.online}
        secondaryVariant={getDeviceHealthVariant(stats.devices.health_percentage)}
        extraContent={
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">Health</span>
            <ProgressRing percentage={stats.devices.health_percentage} size={36} strokeWidth={3} />
          </div>
        }
      />

      {/* Incidents Card */}
      <StatCard
        icon={<IncidentIcon className="w-5 h-5 text-orange-600" />}
        iconBgColor="bg-orange-100"
        label="Incidents"
        value={stats.incidents.total}
        secondaryLabel="active"
        secondaryValue={stats.incidents.active}
        secondaryVariant={getIncidentVariant(stats.incidents.active)}
        extraContent={
          stats.incidents.active > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
              <span className="text-xs text-orange-600 font-medium">
                {stats.incidents.active} requiring attention
              </span>
            </div>
          )
        }
      />

      {/* Alerts Card */}
      <StatCard
        icon={<AlertIcon className="w-5 h-5 text-purple-600" />}
        iconBgColor="bg-purple-100"
        label="Alerts"
        value={stats.alerts.total}
        secondaryLabel="pending"
        secondaryValue={stats.alerts.pending}
        secondaryVariant={getAlertVariant(stats.alerts.pending)}
        extraContent={
          stats.alerts.pending > 0 && (
            <div
              className={cn(
                'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                stats.alerts.pending > 5
                  ? 'bg-red-100 text-red-700'
                  : 'bg-yellow-100 text-yellow-700'
              )}
            >
              {stats.alerts.pending} need review
            </div>
          )
        }
      />

      {/* Inspections Card */}
      <StatCard
        icon={<InspectionIcon className="w-5 h-5 text-green-600" />}
        iconBgColor="bg-green-100"
        label="Compliance"
        value={`${Math.round(stats.inspections.compliance_rate)}%`}
        secondaryLabel="overdue"
        secondaryValue={stats.inspections.overdue}
        secondaryVariant={stats.inspections.overdue > 0 ? 'danger' : 'success'}
        extraContent={
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">Inspections</span>
            {stats.inspections.overdue > 0 ? (
              <span className="inline-flex items-center gap-1 text-xs text-red-600 font-medium">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                {stats.inspections.overdue} overdue
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs text-green-600 font-medium">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                Up to date
              </span>
            )}
          </div>
        }
      />
    </div>
  );
}

export default BuildingStatsCards;
