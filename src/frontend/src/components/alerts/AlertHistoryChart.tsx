/**
 * Alert History Chart - Time-series visualization of alert trends.
 *
 * Uses a simple SVG-based chart (no external chart library dependency).
 * Shows daily alert counts by severity over a configurable time period.
 */

import { useEffect, useState } from 'react';
import { useAudioStore } from '../../stores/audioStore';

interface AlertHistoryChartProps {
  buildingId?: string;
  floorPlanId?: string;
  days?: number;
  className?: string;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#3b82f6',
  info: '#6b7280',
};

export function AlertHistoryChart({
  buildingId,
  floorPlanId,
  days = 7,
  className = '',
}: AlertHistoryChartProps) {
  const { historyChart, fetchHistoryChart } = useAudioStore();
  const [selectedDays, setSelectedDays] = useState(days);

  useEffect(() => {
    fetchHistoryChart({
      building_id: buildingId,
      floor_plan_id: floorPlanId,
      days: selectedDays,
    });
  }, [fetchHistoryChart, buildingId, floorPlanId, selectedDays]);

  // Aggregate data by date
  const dateMap = new Map<string, Record<string, number>>();
  historyChart.forEach((point) => {
    if (!dateMap.has(point.date)) {
      dateMap.set(point.date, {});
    }
    const entry = dateMap.get(point.date)!;
    entry[point.severity] = (entry[point.severity] || 0) + point.count;
  });

  const dates = Array.from(dateMap.keys()).sort();
  const severities = ['critical', 'high', 'medium', 'low', 'info'];

  // Calculate max value for scaling
  let maxValue = 0;
  dates.forEach((date) => {
    const entry = dateMap.get(date)!;
    const total = Object.values(entry).reduce((sum, v) => sum + v, 0);
    maxValue = Math.max(maxValue, total);
  });
  if (maxValue === 0) maxValue = 1;

  const chartWidth = 600;
  const chartHeight = 200;
  const padding = { top: 20, right: 20, bottom: 40, left: 40 };
  const plotWidth = chartWidth - padding.left - padding.right;
  const plotHeight = chartHeight - padding.top - padding.bottom;
  const barWidth = dates.length > 0 ? Math.min(plotWidth / dates.length - 4, 40) : 20;

  return (
    <div className={`bg-white rounded-lg border p-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-800">Alert Level History</h3>
        <div className="flex gap-1">
          {[7, 14, 30].map((d) => (
            <button
              key={d}
              onClick={() => setSelectedDays(d)}
              className={`px-2 py-1 text-xs rounded ${
                selectedDays === d
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {dates.length === 0 ? (
        <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
          No alert data for this period
        </div>
      ) : (
        <>
          <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full">
            {/* Y-axis grid lines */}
            {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
              const y = padding.top + plotHeight * (1 - ratio);
              return (
                <g key={ratio}>
                  <line
                    x1={padding.left}
                    y1={y}
                    x2={padding.left + plotWidth}
                    y2={y}
                    stroke="#f3f4f6"
                    strokeDasharray={ratio === 0 ? '0' : '4'}
                  />
                  <text x={padding.left - 8} y={y + 4} textAnchor="end" className="text-[10px] fill-gray-400">
                    {Math.round(maxValue * ratio)}
                  </text>
                </g>
              );
            })}

            {/* Stacked bars */}
            {dates.map((date, i) => {
              const entry = dateMap.get(date)!;
              const x = padding.left + (plotWidth / dates.length) * i + (plotWidth / dates.length - barWidth) / 2;
              let currentY = padding.top + plotHeight;

              return (
                <g key={date}>
                  {severities.map((severity) => {
                    const value = entry[severity] || 0;
                    if (value === 0) return null;
                    const barHeight = (value / maxValue) * plotHeight;
                    currentY -= barHeight;

                    return (
                      <rect
                        key={severity}
                        x={x}
                        y={currentY}
                        width={barWidth}
                        height={barHeight}
                        fill={SEVERITY_COLORS[severity]}
                        rx={2}
                      >
                        <title>{`${date}: ${severity} = ${value}`}</title>
                      </rect>
                    );
                  })}
                  {/* Date label */}
                  <text
                    x={x + barWidth / 2}
                    y={padding.top + plotHeight + 16}
                    textAnchor="middle"
                    className="text-[9px] fill-gray-500"
                  >
                    {new Date(date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Legend */}
          <div className="flex flex-wrap gap-3 mt-2 justify-center">
            {severities.map((sev) => (
              <div key={sev} className="flex items-center gap-1.5 text-xs text-gray-600">
                <span
                  className="w-3 h-3 rounded-sm"
                  style={{ backgroundColor: SEVERITY_COLORS[sev] }}
                />
                <span className="capitalize">{sev}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
