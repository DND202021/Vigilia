/**
 * Device Health Chart Component
 *
 * Displays device health status distribution using an SVG donut chart.
 * Shows health percentage in center, status legend, and device type badges.
 */

import { useEffect, useState, useRef } from 'react';
import { cn } from '../../utils';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';

// Types
export interface DeviceHealthData {
  total: number;
  by_status: {
    online: number;
    offline: number;
    alert: number;
    maintenance: number;
    error: number;
  };
  by_type: {
    microphone: number;
    camera: number;
    sensor: number;
    gateway: number;
    other: number;
  };
  health_percentage: number;
}

export interface DeviceHealthChartProps {
  data: DeviceHealthData | null;
  isLoading?: boolean;
  className?: string;
}

// Status colors
const STATUS_COLORS: Record<keyof DeviceHealthData['by_status'], string> = {
  online: '#22c55e',
  offline: '#9ca3af',
  alert: '#ef4444',
  maintenance: '#eab308',
  error: '#f97316',
};

// Status labels
const STATUS_LABELS: Record<keyof DeviceHealthData['by_status'], string> = {
  online: 'Online',
  offline: 'Offline',
  alert: 'Alert',
  maintenance: 'Maintenance',
  error: 'Error',
};

// Device type icons (using simple text/emoji representation)
const DEVICE_TYPE_LABELS: Record<keyof DeviceHealthData['by_type'], { label: string; icon: string }> = {
  microphone: { label: 'Microphone', icon: 'M' },
  camera: { label: 'Camera', icon: 'C' },
  sensor: { label: 'Sensor', icon: 'S' },
  gateway: { label: 'Gateway', icon: 'G' },
  other: { label: 'Other', icon: 'O' },
};

// Loading skeleton component
function LoadingSkeleton() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Device Health</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center">
          {/* Donut chart skeleton */}
          <div className="relative w-48 h-48 mb-4">
            <div className="absolute inset-0 rounded-full bg-gray-200 animate-pulse" />
            <div className="absolute inset-8 rounded-full bg-white" />
          </div>

          {/* Legend skeleton */}
          <div className="w-full space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-gray-200 animate-pulse" />
                <div className="h-4 w-20 bg-gray-200 rounded animate-pulse" />
                <div className="h-4 w-8 bg-gray-200 rounded animate-pulse ml-auto" />
              </div>
            ))}
          </div>

          {/* Type badges skeleton */}
          <div className="flex flex-wrap gap-2 mt-4 justify-center">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-6 w-20 bg-gray-200 rounded-full animate-pulse" />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Donut chart segment interface
interface DonutSegment {
  key: keyof DeviceHealthData['by_status'];
  value: number;
  color: string;
  percentage: number;
  startAngle: number;
  endAngle: number;
}

// Calculate donut chart segments
function calculateSegments(data: DeviceHealthData['by_status'], total: number): DonutSegment[] {
  const segments: DonutSegment[] = [];
  let currentAngle = -90; // Start from top

  const statusOrder: (keyof DeviceHealthData['by_status'])[] = [
    'online',
    'alert',
    'error',
    'maintenance',
    'offline',
  ];

  for (const status of statusOrder) {
    const value = data[status];
    if (value > 0) {
      const percentage = (value / total) * 100;
      const angle = (value / total) * 360;

      segments.push({
        key: status,
        value,
        color: STATUS_COLORS[status],
        percentage,
        startAngle: currentAngle,
        endAngle: currentAngle + angle,
      });

      currentAngle += angle;
    }
  }

  return segments;
}

// Tooltip component
interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  content: {
    label: string;
    value: number;
    percentage: number;
    color: string;
  } | null;
}

// Main component
export function DeviceHealthChart({
  data,
  isLoading = false,
  className,
}: DeviceHealthChartProps) {
  const [animationProgress, setAnimationProgress] = useState(0);
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    content: null,
  });
  const svgRef = useRef<SVGSVGElement>(null);

  // Animate on mount/data change
  useEffect(() => {
    if (!data || isLoading) {
      setAnimationProgress(0);
      return;
    }

    let animationFrame: number;
    const duration = 800;
    const startTime = performance.now();

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      // Easing function (ease-out-cubic)
      const easedProgress = 1 - Math.pow(1 - progress, 3);
      setAnimationProgress(easedProgress);

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      }
    };

    animationFrame = requestAnimationFrame(animate);

    return () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
    };
  }, [data, isLoading]);

  // Handle segment hover
  const handleSegmentHover = (
    event: React.MouseEvent<SVGPathElement>,
    segment: DonutSegment
  ) => {
    const svgRect = svgRef.current?.getBoundingClientRect();
    if (!svgRect) return;

    setTooltip({
      visible: true,
      x: event.clientX - svgRect.left,
      y: event.clientY - svgRect.top,
      content: {
        label: STATUS_LABELS[segment.key],
        value: segment.value,
        percentage: segment.percentage,
        color: segment.color,
      },
    });
  };

  const handleSegmentLeave = () => {
    setTooltip((prev) => ({ ...prev, visible: false }));
  };

  // Loading state
  if (isLoading) {
    return <LoadingSkeleton />;
  }

  // No data state
  if (!data || data.total === 0) {
    return (
      <Card className={cn(className)}>
        <CardHeader>
          <CardTitle>Device Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-gray-400">
            <svg
              className="w-12 h-12 mb-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
              />
            </svg>
            <p className="text-sm">No devices found</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Calculate segments
  const segments = calculateSegments(data.by_status, data.total);

  // Chart dimensions
  const size = 180;
  const center = size / 2;
  const outerRadius = 75;
  const innerRadius = 50;
  const strokeWidth = outerRadius - innerRadius;
  const chartRadius = (outerRadius + innerRadius) / 2;

  // Calculate stroke-dasharray values
  const circumference = 2 * Math.PI * chartRadius;

  // Get health color based on percentage
  const getHealthColor = (percentage: number): string => {
    if (percentage >= 90) return '#22c55e'; // green
    if (percentage >= 70) return '#eab308'; // yellow
    if (percentage >= 50) return '#f97316'; // orange
    return '#ef4444'; // red
  };

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle>Device Health</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center">
          {/* Donut Chart */}
          <div className="relative">
            <svg
              ref={svgRef}
              width={size}
              height={size}
              viewBox={`0 0 ${size} ${size}`}
              className="transform -rotate-90"
            >
              {/* Background circle */}
              <circle
                cx={center}
                cy={center}
                r={chartRadius}
                fill="none"
                stroke="#f3f4f6"
                strokeWidth={strokeWidth}
              />

              {/* Animated segments using stroke-dasharray */}
              {segments.map((segment, index) => {
                const segmentLength = (segment.percentage / 100) * circumference;
                const offset = segments
                  .slice(0, index)
                  .reduce((acc, s) => acc + (s.percentage / 100) * circumference, 0);

                return (
                  <circle
                    key={segment.key}
                    cx={center}
                    cy={center}
                    r={chartRadius}
                    fill="none"
                    stroke={segment.color}
                    strokeWidth={strokeWidth}
                    strokeDasharray={`${segmentLength * animationProgress} ${circumference}`}
                    strokeDashoffset={-offset * animationProgress}
                    className="transition-all duration-200 cursor-pointer hover:opacity-80"
                    style={{ transformOrigin: 'center' }}
                    onMouseMove={(e) =>
                      handleSegmentHover(e as unknown as React.MouseEvent<SVGPathElement>, segment)
                    }
                    onMouseLeave={handleSegmentLeave}
                  />
                );
              })}
            </svg>

            {/* Center text */}
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span
                className="text-3xl font-bold transition-colors duration-300"
                style={{ color: getHealthColor(data.health_percentage) }}
              >
                {Math.round(data.health_percentage * animationProgress)}%
              </span>
              <span className="text-xs text-gray-500">Health</span>
            </div>

            {/* Tooltip */}
            {tooltip.visible && tooltip.content && (
              <div
                className="absolute z-10 px-3 py-2 text-sm bg-gray-900 text-white rounded-lg shadow-lg pointer-events-none transform -translate-x-1/2 -translate-y-full"
                style={{
                  left: tooltip.x,
                  top: tooltip.y - 10,
                }}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: tooltip.content.color }}
                  />
                  <span className="font-medium">{tooltip.content.label}</span>
                </div>
                <div className="text-gray-300 text-xs mt-1">
                  {tooltip.content.value} devices ({tooltip.content.percentage.toFixed(1)}%)
                </div>
              </div>
            )}
          </div>

          {/* Total devices count */}
          <div className="text-sm text-gray-500 mt-2 mb-4">
            {data.total} total device{data.total !== 1 ? 's' : ''}
          </div>

          {/* Legend */}
          <div className="w-full space-y-1.5">
            {segments.map((segment) => (
              <div
                key={segment.key}
                className="flex items-center gap-2 text-sm hover:bg-gray-50 px-2 py-1 rounded transition-colors"
              >
                <span
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: segment.color }}
                />
                <span className="text-gray-700">{STATUS_LABELS[segment.key]}</span>
                <span className="ml-auto text-gray-500 font-medium">
                  {segment.value}
                </span>
                <span className="text-gray-400 text-xs w-12 text-right">
                  ({segment.percentage.toFixed(0)}%)
                </span>
              </div>
            ))}
          </div>

          {/* Device type badges */}
          <div className="flex flex-wrap gap-2 mt-4 justify-center">
            {(Object.entries(data.by_type) as [keyof DeviceHealthData['by_type'], number][])
              .filter(([, count]) => count > 0)
              .map(([type, count]) => (
                <span
                  key={type}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded-full"
                  title={DEVICE_TYPE_LABELS[type].label}
                >
                  <span className="w-4 h-4 flex items-center justify-center bg-gray-200 rounded-full text-[10px] font-bold">
                    {DEVICE_TYPE_LABELS[type].icon}
                  </span>
                  {DEVICE_TYPE_LABELS[type].label}: {count}
                </span>
              ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Default export
export default DeviceHealthChart;
