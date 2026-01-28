/**
 * InspectionComplianceWidget Component
 *
 * Displays inspection compliance status with circular progress indicator,
 * status counts, upcoming inspections list, and overdue warnings.
 */

import { cn } from '../../utils';

interface InspectionComplianceData {
  total: number;
  completed: number;
  scheduled: number;
  overdue: number;
  compliance_rate: number;
  upcoming: Array<{ id: string; type: string; scheduled_date: string }>;
  overdue_list: Array<{ id: string; type: string; scheduled_date: string }>;
}

interface InspectionComplianceWidgetProps {
  data: InspectionComplianceData | null;
  isLoading?: boolean;
  onInspectionClick?: (id: string) => void;
  className?: string;
}

// Get compliance rate color based on percentage
function getComplianceColor(rate: number): { stroke: string; text: string; bg: string } {
  if (rate >= 80) {
    return { stroke: '#22c55e', text: 'text-green-600', bg: 'bg-green-100' };
  }
  if (rate >= 50) {
    return { stroke: '#eab308', text: 'text-yellow-600', bg: 'bg-yellow-100' };
  }
  return { stroke: '#ef4444', text: 'text-red-600', bg: 'bg-red-100' };
}

// Circular progress component
function CircularProgress({ percentage, size = 120 }: { percentage: number; size?: number }) {
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;
  const colors = getComplianceColor(percentage);

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="-rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={strokeWidth}
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={colors.stroke}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-500 ease-out"
        />
      </svg>
      {/* Percentage text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn('text-2xl font-bold', colors.text)}>
          {percentage.toFixed(0)}%
        </span>
        <span className="text-xs text-gray-500">Compliance</span>
      </div>
    </div>
  );
}

// Format date for display
function formatScheduledDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

// Get days until/since a date
function getDaysLabel(dateStr: string): { label: string; isOverdue: boolean } {
  const date = new Date(dateStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  date.setHours(0, 0, 0, 0);

  const diffTime = date.getTime() - today.getTime();
  const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return { label: 'Today', isOverdue: false };
  if (diffDays === 1) return { label: 'Tomorrow', isOverdue: false };
  if (diffDays > 0) return { label: `In ${diffDays} days`, isOverdue: false };
  if (diffDays === -1) return { label: '1 day overdue', isOverdue: true };
  return { label: `${Math.abs(diffDays)} days overdue`, isOverdue: true };
}

// Inspection type labels
const TYPE_LABELS: Record<string, string> = {
  fire_safety: 'Fire Safety',
  structural: 'Structural',
  hazmat: 'Hazmat',
  general: 'General',
};

// Loading skeleton
function LoadingSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="flex items-center gap-6 mb-6">
        {/* Circular progress skeleton */}
        <div className="w-[120px] h-[120px] rounded-full bg-gray-200" />
        {/* Stats skeleton */}
        <div className="flex-1 space-y-3">
          <div className="h-5 bg-gray-200 rounded w-24" />
          <div className="h-4 bg-gray-200 rounded w-32" />
          <div className="h-4 bg-gray-200 rounded w-28" />
        </div>
      </div>
      {/* List skeleton */}
      <div className="space-y-2">
        <div className="h-4 bg-gray-200 rounded w-full" />
        <div className="h-4 bg-gray-200 rounded w-3/4" />
        <div className="h-4 bg-gray-200 rounded w-5/6" />
      </div>
    </div>
  );
}

export function InspectionComplianceWidget({
  data,
  isLoading = false,
  onInspectionClick,
  className,
}: InspectionComplianceWidgetProps) {
  const hasOverdue = data && data.overdue > 0;

  return (
    <div className={cn('bg-white rounded-lg shadow-md overflow-hidden', className)}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Inspection Compliance</h3>
      </div>

      {/* Content */}
      <div className="px-6 py-4">
        {isLoading ? (
          <LoadingSkeleton />
        ) : !data ? (
          <div className="text-center py-8 text-gray-500">
            <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            <p className="text-sm">No inspection data available</p>
          </div>
        ) : (
          <>
            {/* Overdue warning banner */}
            {hasOverdue && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
                <div className="flex-shrink-0">
                  <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-red-800">
                    {data.overdue} overdue inspection{data.overdue > 1 ? 's' : ''} require attention
                  </p>
                </div>
              </div>
            )}

            {/* Main content: Circular progress and stats */}
            <div className="flex items-center gap-6 mb-6">
              <CircularProgress percentage={data.compliance_rate} />

              {/* Status counts */}
              <div className="flex-1 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Total Inspections</span>
                  <span className="text-sm font-semibold text-gray-900">{data.total}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Completed</span>
                  <span className="text-sm font-semibold text-green-600">{data.completed}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Scheduled</span>
                  <span className="text-sm font-semibold text-blue-600">{data.scheduled}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Overdue</span>
                  <span className={cn(
                    'text-sm font-bold px-2 py-0.5 rounded',
                    data.overdue > 0 ? 'text-red-700 bg-red-100' : 'text-gray-600'
                  )}>
                    {data.overdue}
                  </span>
                </div>
              </div>
            </div>

            {/* Upcoming inspections list */}
            {data.upcoming.length > 0 && (
              <div className="border-t border-gray-100 pt-4">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Upcoming Inspections</h4>
                <ul className="space-y-2">
                  {data.upcoming.slice(0, 3).map((inspection) => {
                    const { label: daysLabel, isOverdue } = getDaysLabel(inspection.scheduled_date);
                    return (
                      <li
                        key={inspection.id}
                        className={cn(
                          'flex items-center justify-between p-2 rounded-lg transition-colors',
                          onInspectionClick ? 'cursor-pointer hover:bg-gray-50' : ''
                        )}
                        onClick={() => onInspectionClick?.(inspection.id)}
                      >
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full bg-blue-500" />
                          <span className="text-sm text-gray-900">
                            {TYPE_LABELS[inspection.type] || inspection.type}
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="text-xs text-gray-500">
                            {formatScheduledDate(inspection.scheduled_date)}
                          </span>
                          <span className={cn(
                            'ml-2 text-xs',
                            isOverdue ? 'text-red-600 font-medium' : 'text-gray-400'
                          )}>
                            {daysLabel}
                          </span>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}

            {/* Overdue list */}
            {data.overdue_list.length > 0 && (
              <div className="border-t border-gray-100 pt-4 mt-4">
                <h4 className="text-sm font-medium text-red-700 mb-3 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Overdue Inspections
                </h4>
                <ul className="space-y-2">
                  {data.overdue_list.slice(0, 3).map((inspection) => {
                    const { label: daysLabel } = getDaysLabel(inspection.scheduled_date);
                    return (
                      <li
                        key={inspection.id}
                        className={cn(
                          'flex items-center justify-between p-2 rounded-lg bg-red-50 transition-colors',
                          onInspectionClick ? 'cursor-pointer hover:bg-red-100' : ''
                        )}
                        onClick={() => onInspectionClick?.(inspection.id)}
                      >
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                          <span className="text-sm text-red-900 font-medium">
                            {TYPE_LABELS[inspection.type] || inspection.type}
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="text-xs text-red-600 font-medium">
                            {daysLabel}
                          </span>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}

            {/* Empty state for no inspections */}
            {data.total === 0 && (
              <div className="text-center py-4 text-gray-500">
                <p className="text-sm">No inspections recorded</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default InspectionComplianceWidget;
