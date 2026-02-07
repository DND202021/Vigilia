/**
 * FloorPlanTelemetryOverlay Component
 *
 * SVG overlay that shows live telemetry values as badges next to device markers on floor plans.
 * Each badge displays the latest telemetry value for the device's primary_metric.
 * Uses React.memo for performance optimization.
 */
import React from 'react';
import { useTelemetryStore } from '../../stores/telemetryStore';
import { useTelemetrySubscription } from '../../hooks/useTelemetrySubscription';

interface DeviceInfo {
  id: string;
  name: string;
  device_type: string;
  position_x?: number;
  position_y?: number;
  status: string;
  primary_metric?: string;
}

interface FloorPlanTelemetryOverlayProps {
  floorPlanId: string;
  devices: DeviceInfo[];
  containerWidth: number;
  containerHeight: number;
  className?: string;
}

/**
 * Individual device telemetry badge component
 * Uses useTelemetrySubscription hook to auto-subscribe to device telemetry
 */
const DeviceTelemetryBadge = React.memo(
  ({
    device,
    containerWidth,
    containerHeight,
  }: {
    device: DeviceInfo;
    containerWidth: number;
    containerHeight: number;
  }) => {
    // Auto-subscribe to device telemetry if it has a primary_metric
    useTelemetrySubscription({
      deviceId: device.id,
      metricName: device.primary_metric || null,
    });

    // Get latest telemetry value from store
    const latestValue = useTelemetryStore((state) => {
      if (!device.primary_metric) return null;
      const data = state.getDeviceMetricData(device.id, device.primary_metric);
      return data.length > 0 ? data[data.length - 1].value : null;
    });

    // Skip if no position or no primary metric
    if (
      device.position_x === undefined ||
      device.position_y === undefined ||
      !device.primary_metric
    ) {
      return null;
    }

    // Calculate pixel position from percentage coordinates
    const pixelX = (device.position_x / 100) * containerWidth;
    const pixelY = (device.position_y / 100) * containerHeight;

    // Badge position: offset to the right and up from device marker
    const badgeX = pixelX + 12;
    const badgeY = pixelY - 12;

    // Format value for display
    let displayValue = '—';
    if (latestValue !== null && latestValue !== undefined) {
      if (typeof latestValue === 'number') {
        displayValue = latestValue.toFixed(1);
      } else if (typeof latestValue === 'boolean') {
        displayValue = latestValue ? 'ON' : 'OFF';
      } else {
        displayValue = String(latestValue);
      }
    }

    // Truncate long values
    if (displayValue.length > 6) {
      displayValue = displayValue.substring(0, 6) + '…';
    }

    return (
      <g transform={`translate(${badgeX}, ${badgeY})`}>
        {/* Badge background */}
        <rect
          x={0}
          y={0}
          width={Math.max(40, displayValue.length * 7)}
          height={20}
          rx={4}
          fill="white"
          stroke="#d1d5db"
          strokeWidth={1}
          opacity={0.95}
        />
        {/* Badge text */}
        <text
          x={Math.max(40, displayValue.length * 7) / 2}
          y={14}
          textAnchor="middle"
          fill="#374151"
          fontSize={11}
          fontWeight={500}
        >
          {displayValue}
        </text>
      </g>
    );
  },
  // Custom comparison: only re-render if device.id, primary_metric, or container dimensions change
  (prevProps, nextProps) => {
    return (
      prevProps.device.id === nextProps.device.id &&
      prevProps.device.primary_metric === nextProps.device.primary_metric &&
      prevProps.containerWidth === nextProps.containerWidth &&
      prevProps.containerHeight === nextProps.containerHeight
    );
  }
);

DeviceTelemetryBadge.displayName = 'DeviceTelemetryBadge';

/**
 * Main overlay component
 */
export function FloorPlanTelemetryOverlay({
  devices,
  containerWidth,
  containerHeight,
  className = '',
}: FloorPlanTelemetryOverlayProps) {
  // Filter devices that have positions and primary metrics
  const devicesWithTelemetry = devices.filter(
    (d) =>
      d.position_x !== undefined &&
      d.position_y !== undefined &&
      d.primary_metric
  );

  return (
    <svg
      className={`absolute top-0 left-0 pointer-events-none ${className}`}
      width={containerWidth}
      height={containerHeight}
      style={{ zIndex: 1000 }}
    >
      {devicesWithTelemetry.map((device) => (
        <DeviceTelemetryBadge
          key={device.id}
          device={device}
          containerWidth={containerWidth}
          containerHeight={containerHeight}
        />
      ))}
    </svg>
  );
}

export default FloorPlanTelemetryOverlay;
