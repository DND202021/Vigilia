/**
 * DeviceTelemetryPage - Main dashboard page for viewing device telemetry
 *
 * Features:
 * - Device selector with status display
 * - Metric selector (auto-populated from device)
 * - Time range picker (1h, 6h, 24h, 7d)
 * - Live telemetry chart with real-time updates
 * - Device status indicator with sync state
 */
import { useEffect, useState } from 'react';
import { useDeviceStore } from '../stores/deviceStore';
import { useTelemetryStore } from '../stores/telemetryStore';
import { telemetryApi } from '../services/api';
import { TelemetryChart } from '../components/telemetry/TelemetryChart';
import { TimeRangePicker } from '../components/telemetry/TimeRangePicker';
import { DeviceStatusIndicator } from '../components/telemetry/DeviceStatusIndicator';
import { useTelemetrySubscription } from '../hooks/useTelemetrySubscription';
import type { DeviceStatus } from '../types';

interface DeviceTwinResponse {
  device_id: string;
  desired_config: Record<string, any>;
  reported_config: Record<string, any>;
  metadata: {
    last_updated: string;
    is_synced: boolean;
  };
}

export function DeviceTelemetryPage() {
  const { devices, fetchDevices, isLoading: isLoadingDevices } = useDeviceStore();
  const {
    availableMetrics,
    isLoadingMetrics,
    isLoadingHistory,
    fetchAvailableMetrics,
    fetchHistoricalData,
    getDeviceMetricData,
  } = useTelemetryStore();

  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');
  const [selectedMetric, setSelectedMetric] = useState<string>('');
  const [timeRange, setTimeRange] = useState<{ start: Date; end: Date }>({
    start: new Date(Date.now() - 60 * 60 * 1000), // Last 1 hour
    end: new Date(),
  });
  const [deviceTwin, setDeviceTwin] = useState<DeviceTwinResponse | null>(null);
  const [isFetchingTwin, setIsFetchingTwin] = useState(false);

  // Subscribe to telemetry updates for selected device+metric
  useTelemetrySubscription({
    deviceId: selectedDeviceId || null,
    metricName: selectedMetric || null,
  });

  // Load devices on mount
  useEffect(() => {
    fetchDevices();
  }, [fetchDevices]);

  // Handle device selection
  const handleDeviceSelect = async (deviceId: string) => {
    setSelectedDeviceId(deviceId);
    setSelectedMetric(''); // Clear previous metric selection
    setDeviceTwin(null);

    if (deviceId) {
      // Fetch available metrics for this device
      await fetchAvailableMetrics(deviceId);

      // Fetch device twin for status indicator
      setIsFetchingTwin(true);
      try {
        const twin = await telemetryApi.getDeviceTwin(deviceId);
        setDeviceTwin(twin);
      } catch (error) {
        console.error('Failed to fetch device twin:', error);
      } finally {
        setIsFetchingTwin(false);
      }
    }
  };

  // Handle metric selection
  const handleMetricSelect = async (metricName: string) => {
    setSelectedMetric(metricName);

    if (selectedDeviceId && metricName) {
      // Fetch historical data for initial chart load
      await fetchHistoricalData(
        selectedDeviceId,
        metricName,
        timeRange.start.toISOString(),
        timeRange.end.toISOString()
      );
    }
  };

  // Handle time range change
  const handleTimeRangeChange = async (start: Date, end: Date) => {
    setTimeRange({ start, end });

    if (selectedDeviceId && selectedMetric) {
      // Re-fetch historical data with new time range
      await fetchHistoricalData(
        selectedDeviceId,
        selectedMetric,
        start.toISOString(),
        end.toISOString()
      );
    }
  };

  // Get selected device object
  const selectedDevice = devices.find((d) => d.id === selectedDeviceId);

  // Get current data for selected device+metric
  const currentData = selectedDeviceId && selectedMetric
    ? getDeviceMetricData(selectedDeviceId, selectedMetric)
    : [];

  // Get latest value from data
  const latestDataPoint = currentData.length > 0 ? currentData[currentData.length - 1] : null;

  // Get available metrics for selected device
  const deviceMetrics = selectedDeviceId ? availableMetrics[selectedDeviceId] || [] : [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Device Telemetry</h1>
        <p className="text-sm text-gray-500 mt-1">Real-time telemetry streams from IoT devices</p>
      </div>

      {/* Controls Row */}
      <div className="flex flex-wrap gap-4 items-end">
        {/* Device Selector */}
        <div className="flex-1 min-w-[200px]">
          <label className="block text-sm font-medium text-gray-700 mb-1">Device</label>
          <select
            value={selectedDeviceId}
            onChange={(e) => handleDeviceSelect(e.target.value)}
            disabled={isLoadingDevices}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">Select a device...</option>
            {devices.map((device) => (
              <option key={device.id} value={device.id}>
                {device.name} ({device.status})
              </option>
            ))}
          </select>
        </div>

        {/* Metric Selector */}
        <div className="flex-1 min-w-[200px]">
          <label className="block text-sm font-medium text-gray-700 mb-1">Metric</label>
          <select
            value={selectedMetric}
            onChange={(e) => handleMetricSelect(e.target.value)}
            disabled={!selectedDeviceId || isLoadingMetrics || deviceMetrics.length === 0}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          >
            <option value="">
              {isLoadingMetrics ? 'Loading metrics...' : 'Select a metric...'}
            </option>
            {deviceMetrics.map((metric) => (
              <option key={metric} value={metric}>
                {metric}
              </option>
            ))}
          </select>
        </div>

        {/* Time Range Picker */}
        <div className="flex-1 min-w-[300px]">
          <label className="block text-sm font-medium text-gray-700 mb-1">Time Range</label>
          <TimeRangePicker onRangeChange={handleTimeRangeChange} />
        </div>

        {/* Device Status Indicator */}
        {selectedDevice && deviceTwin && (
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <DeviceStatusIndicator
              status={selectedDevice.status as DeviceStatus}
              lastSeen={selectedDevice.last_seen || null}
              isSynced={deviceTwin.metadata.is_synced}
              size="md"
            />
          </div>
        )}
        {selectedDevice && isFetchingTwin && (
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <div className="text-sm text-gray-500">Loading status...</div>
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <div className="bg-white rounded-lg shadow-sm border p-4">
        {/* No device selected */}
        {!selectedDeviceId && (
          <div className="py-12 text-center">
            <div className="text-gray-400 text-5xl mb-4">📊</div>
            <p className="text-gray-600 text-lg font-medium">Select a device to view telemetry data</p>
            <p className="text-gray-500 text-sm mt-2">Choose a device from the dropdown above to get started</p>
          </div>
        )}

        {/* Device selected but no metric */}
        {selectedDeviceId && !selectedMetric && (
          <div className="py-12">
            {isLoadingMetrics ? (
              <div className="text-center">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-blue-600 mb-4"></div>
                <p className="text-gray-600">Loading available metrics...</p>
              </div>
            ) : deviceMetrics.length === 0 ? (
              <div className="text-center">
                <p className="text-gray-600 text-lg font-medium">No metrics available</p>
                <p className="text-gray-500 text-sm mt-2">This device hasn't reported any telemetry data yet</p>
              </div>
            ) : (
              <div className="text-center">
                <p className="text-gray-600 text-lg font-medium mb-4">Available Metrics</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {deviceMetrics.map((metric) => (
                    <button
                      key={metric}
                      onClick={() => handleMetricSelect(metric)}
                      className="px-4 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors border border-blue-200 font-medium"
                    >
                      {metric}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Device and metric selected - show chart */}
        {selectedDeviceId && selectedMetric && (
          <div className="space-y-4">
            {/* Loading indicator */}
            {isLoadingHistory && (
              <div className="text-center py-4">
                <div className="inline-block animate-spin rounded-full h-6 w-6 border-4 border-gray-300 border-t-blue-600"></div>
                <span className="ml-2 text-gray-600">Loading telemetry data...</span>
              </div>
            )}

            {/* Chart */}
            {!isLoadingHistory && (
              <>
                <div className="mb-2">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {selectedDevice?.name} - {selectedMetric}
                  </h3>
                </div>
                <TelemetryChart
                  deviceId={selectedDeviceId}
                  metricName={selectedMetric}
                  height={400}
                />

                {/* Data Summary */}
                {currentData.length > 0 && (
                  <div className="grid grid-cols-3 gap-4 pt-4 border-t">
                    <div>
                      <p className="text-sm text-gray-500">Data Points</p>
                      <p className="text-lg font-semibold text-gray-900">{currentData.length}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Latest Value</p>
                      <p className="text-lg font-semibold text-gray-900">
                        {latestDataPoint?.value !== null && latestDataPoint?.value !== undefined
                          ? typeof latestDataPoint.value === 'number'
                            ? latestDataPoint.value.toFixed(2)
                            : String(latestDataPoint.value)
                          : '—'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Latest Timestamp</p>
                      <p className="text-lg font-semibold text-gray-900">
                        {latestDataPoint
                          ? new Date(latestDataPoint.time).toLocaleTimeString()
                          : '—'}
                      </p>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default DeviceTelemetryPage;
