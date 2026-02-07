/**
 * TelemetryChart Component
 *
 * Recharts LineChart wrapper for real-time telemetry data visualization.
 * Reads data from telemetryStore and renders with performance optimizations
 * (animations disabled, no dots, memoized configuration).
 */
import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { format } from 'date-fns';
import { useTelemetryStore } from '../../stores/telemetryStore';

interface TelemetryChartProps {
  deviceId: string;
  metricName: string;
  color?: string;
  height?: number;
}

export function TelemetryChart({
  deviceId,
  metricName,
  color = '#8884d8',
  height = 400,
}: TelemetryChartProps) {
  // Read data from telemetryStore
  const data = useTelemetryStore((state) => state.getDeviceMetricData(deviceId, metricName));

  // Memoize chart configuration to prevent unnecessary re-renders
  const chartConfig = useMemo(() => {
    return {
      margin: { top: 5, right: 30, left: 20, bottom: 5 },
    };
  }, []);

  // Memoize tick formatter functions
  const xAxisTickFormatter = useMemo(() => {
    return (tick: string | number) => {
      try {
        return format(new Date(tick), 'HH:mm:ss');
      } catch {
        return String(tick);
      }
    };
  }, []);

  const tooltipLabelFormatter = useMemo(() => {
    return (label: any) => {
      try {
        return format(new Date(label), 'PPpp');
      } catch {
        return String(label);
      }
    };
  }, []);

  // Handle empty data
  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200"
        style={{ height }}
      >
        <p className="text-gray-500 text-sm">No telemetry data available</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={chartConfig.margin}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="time"
          tickFormatter={xAxisTickFormatter}
          tick={{ fontSize: 12 }}
          minTickGap={50}
        />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip labelFormatter={tooltipLabelFormatter} />
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          isAnimationActive={false}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export default TelemetryChart;
