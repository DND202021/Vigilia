/**
 * IncidentTrendChart Component
 *
 * SVG-based chart showing incidents over time with priority breakdown.
 * Supports configurable time ranges and displays summary statistics.
 */

import { useState, useMemo } from 'react';
import { cn } from '../../utils';

interface IncidentTrendData {
  total: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_priority: Record<string, number>;
  trend: Array<{ date: string; count: number }>;
}

interface IncidentTrendChartProps {
  data: IncidentTrendData | null;
  isLoading?: boolean;
  timeRange?: '7d' | '30d' | '90d';
  onTimeRangeChange?: (range: '7d' | '30d' | '90d') => void;
  className?: string;
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: '#dc2626',
  high: '#f97316',
  medium: '#eab308',
  low: '#3b82f6',
  minimal: '#6b7280',
};

const TIME_RANGE_OPTIONS: Array<{ value: '7d' | '30d' | '90d'; label: string }> = [
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
  { value: '90d', label: '90d' },
];

// Loading skeleton component
function LoadingSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="flex items-center justify-between mb-4">
        <div className="h-5 bg-gray-200 rounded w-32" />
        <div className="flex gap-1">
          <div className="h-7 w-10 bg-gray-200 rounded" />
          <div className="h-7 w-10 bg-gray-200 rounded" />
          <div className="h-7 w-10 bg-gray-200 rounded" />
        </div>
      </div>
      <div className="h-48 bg-gray-100 rounded mb-4" />
      <div className="grid grid-cols-5 gap-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-12 bg-gray-100 rounded" />
        ))}
      </div>
    </div>
  );
}

export function IncidentTrendChart({
  data,
  isLoading = false,
  timeRange = '7d',
  onTimeRangeChange,
  className,
}: IncidentTrendChartProps) {
  const [hoveredBar, setHoveredBar] = useState<number | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<{ x: number; y: number } | null>(null);

  // Chart dimensions
  const chartWidth = 600;
  const chartHeight = 200;
  const padding = { top: 20, right: 20, bottom: 40, left: 50 };
  const plotWidth = chartWidth - padding.left - padding.right;
  const plotHeight = chartHeight - padding.top - padding.bottom;

  // Process trend data
  const { dates, maxValue, barWidth } = useMemo(() => {
    const trendData = data?.trend || [];
    const sortedDates = trendData.slice().sort((a, b) => a.date.localeCompare(b.date));

    let max = 0;
    sortedDates.forEach((point) => {
      max = Math.max(max, point.count);
    });
    if (max === 0) max = 1;

    const width = sortedDates.length > 0
      ? Math.min(plotWidth / sortedDates.length - 4, 40)
      : 20;

    return {
      dates: sortedDates,
      maxValue: max,
      barWidth: width,
    };
  }, [data?.trend, plotWidth]);

  // Calculate Y-axis scale
  const yScale = (value: number) => {
    return padding.top + plotHeight * (1 - value / maxValue);
  };

  // Calculate X position for a bar
  const xPosition = (index: number) => {
    if (dates.length === 0) return padding.left;
    const spacing = plotWidth / dates.length;
    return padding.left + spacing * index + (spacing - barWidth) / 2;
  };

  // Format date for display
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return dateString;
    }
  };

  // Handle mouse events for tooltip
  const handleMouseEnter = (index: number, event: React.MouseEvent<SVGRectElement>) => {
    setHoveredBar(index);
    const rect = event.currentTarget.getBoundingClientRect();
    const svg = event.currentTarget.closest('svg');
    if (svg) {
      const svgRect = svg.getBoundingClientRect();
      setTooltipPosition({
        x: rect.left + rect.width / 2 - svgRect.left,
        y: rect.top - svgRect.top - 8,
      });
    }
  };

  const handleMouseLeave = () => {
    setHoveredBar(null);
    setTooltipPosition(null);
  };

  // Calculate grid lines
  const gridLines = useMemo(() => {
    const lines: number[] = [];
    const step = Math.ceil(maxValue / 4);
    for (let i = 0; i <= 4; i++) {
      lines.push(i * step);
    }
    return lines;
  }, [maxValue]);

  if (isLoading) {
    return (
      <div className={cn('bg-white rounded-lg border p-4', className)}>
        <LoadingSkeleton />
      </div>
    );
  }

  const priorityBreakdown = data?.by_priority || {};
  const priorities = ['critical', 'high', 'medium', 'low', 'minimal'];

  return (
    <div className={cn('bg-white rounded-lg border p-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-800">Incident Trend</h3>
        <div className="flex gap-1">
          {TIME_RANGE_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => onTimeRangeChange?.(option.value)}
              className={cn(
                'px-2 py-1 text-xs rounded transition-colors',
                timeRange === option.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      {dates.length === 0 ? (
        <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
          No incident data for this period
        </div>
      ) : (
        <div className="relative">
          <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full">
            {/* Grid lines */}
            {gridLines.map((value, index) => {
              const y = yScale(value);
              return (
                <g key={index}>
                  <line
                    x1={padding.left}
                    y1={y}
                    x2={padding.left + plotWidth}
                    y2={y}
                    stroke="#e5e7eb"
                    strokeDasharray={index === 0 ? '0' : '4'}
                  />
                  <text
                    x={padding.left - 8}
                    y={y + 4}
                    textAnchor="end"
                    className="text-[10px] fill-gray-400"
                  >
                    {value}
                  </text>
                </g>
              );
            })}

            {/* Bars */}
            {dates.map((point, index) => {
              const x = xPosition(index);
              const barHeight = (point.count / maxValue) * plotHeight;
              const y = padding.top + plotHeight - barHeight;
              const isHovered = hoveredBar === index;

              return (
                <g key={point.date}>
                  {/* Bar */}
                  <rect
                    x={x}
                    y={y}
                    width={barWidth}
                    height={barHeight}
                    fill={isHovered ? '#2563eb' : '#3b82f6'}
                    rx={2}
                    className="cursor-pointer transition-colors"
                    onMouseEnter={(e) => handleMouseEnter(index, e)}
                    onMouseLeave={handleMouseLeave}
                  />

                  {/* Date label */}
                  {(dates.length <= 14 || index % Math.ceil(dates.length / 10) === 0) && (
                    <text
                      x={x + barWidth / 2}
                      y={padding.top + plotHeight + 16}
                      textAnchor="middle"
                      className="text-[9px] fill-gray-500"
                    >
                      {formatDate(point.date)}
                    </text>
                  )}
                </g>
              );
            })}

            {/* Y-axis line */}
            <line
              x1={padding.left}
              y1={padding.top}
              x2={padding.left}
              y2={padding.top + plotHeight}
              stroke="#d1d5db"
            />

            {/* X-axis line */}
            <line
              x1={padding.left}
              y1={padding.top + plotHeight}
              x2={padding.left + plotWidth}
              y2={padding.top + plotHeight}
              stroke="#d1d5db"
            />
          </svg>

          {/* Tooltip */}
          {hoveredBar !== null && tooltipPosition && dates[hoveredBar] && (
            <div
              className="absolute bg-gray-900 text-white text-xs px-2 py-1 rounded shadow-lg pointer-events-none transform -translate-x-1/2 -translate-y-full"
              style={{
                left: tooltipPosition.x,
                top: tooltipPosition.y,
              }}
            >
              <div className="font-medium">{formatDate(dates[hoveredBar].date)}</div>
              <div className="text-gray-300">{dates[hoveredBar].count} incidents</div>
            </div>
          )}
        </div>
      )}

      {/* Summary stats */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-500">Total Incidents</span>
          <span className="text-sm font-semibold text-gray-900">{data?.total || 0}</span>
        </div>

        {/* Priority breakdown */}
        <div className="grid grid-cols-5 gap-2">
          {priorities.map((priority) => {
            const count = priorityBreakdown[priority] || 0;
            const percentage = data?.total ? Math.round((count / data.total) * 100) : 0;

            return (
              <div
                key={priority}
                className="text-center p-2 rounded bg-gray-50"
              >
                <div
                  className="w-3 h-3 rounded-full mx-auto mb-1"
                  style={{ backgroundColor: PRIORITY_COLORS[priority] }}
                />
                <div className="text-xs font-medium text-gray-700 capitalize">
                  {priority}
                </div>
                <div className="text-sm font-semibold text-gray-900">{count}</div>
                <div className="text-[10px] text-gray-500">{percentage}%</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default IncidentTrendChart;
