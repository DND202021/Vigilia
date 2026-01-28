/**
 * Analytics Components
 *
 * This module exports all building analytics components for use throughout the application.
 */

// Main dashboard component
export { BuildingAnalyticsDashboard, default as BuildingAnalyticsDashboardDefault } from './BuildingAnalyticsDashboard';
export type { BuildingAnalyticsDashboardProps } from './BuildingAnalyticsDashboard';

// Stats cards component
export { BuildingStatsCards, default as BuildingStatsCardsDefault } from './BuildingStatsCards';

// Device health donut chart
export { DeviceHealthChart, default as DeviceHealthChartDefault } from './DeviceHealthChart';
export type { DeviceHealthData, DeviceHealthChartProps } from './DeviceHealthChart';

// Incident trend bar chart
export { IncidentTrendChart, default as IncidentTrendChartDefault } from './IncidentTrendChart';

// Inspection compliance widget
export { InspectionComplianceWidget, default as InspectionComplianceWidgetDefault } from './InspectionComplianceWidget';

// Alert severity bar chart
export { AlertSeverityChart, default as AlertSeverityChartDefault } from './AlertSeverityChart';
