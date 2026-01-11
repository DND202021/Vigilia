/**
 * Dashboard Page
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useIncidentStore } from '../stores/incidentStore';
import { useAlertStore } from '../stores/alertStore';
import { useResourceStore } from '../stores/resourceStore';
import { usePolling } from '../hooks/useInterval';
import { Card, CardHeader, CardTitle, CardContent, Badge, Spinner } from '../components/ui';
import {
  formatRelativeTime,
  getPriorityLabel,
  getPriorityBgColor,
  getPriorityColor,
  getSeverityLabel,
  getSeverityBgColor,
  getIncidentTypeLabel,
  getAlertTypeLabel,
  getResourceStatusLabel,
  cn,
} from '../utils';
import type { Incident, Alert, Resource } from '../types';

const POLL_INTERVAL = 30000; // 30 seconds

export function DashboardPage() {
  const {
    activeIncidents,
    fetchActiveIncidents,
    isLoading: incidentsLoading,
  } = useIncidentStore();

  const {
    pendingAlerts,
    fetchPendingAlerts,
    isLoading: alertsLoading,
  } = useAlertStore();

  const {
    availableResources,
    fetchAvailableResources,
    isLoading: resourcesLoading,
  } = useResourceStore();

  // Initial fetch and polling
  usePolling(fetchActiveIncidents, POLL_INTERVAL);
  usePolling(fetchPendingAlerts, POLL_INTERVAL);
  usePolling(fetchAvailableResources, POLL_INTERVAL);

  const isLoading = incidentsLoading || alertsLoading || resourcesLoading;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-gray-500">Emergency Response IoT Platform</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatsCard
          title="Active Incidents"
          value={activeIncidents.length}
          linkTo="/incidents"
          linkText="View all"
          color="red"
          isLoading={incidentsLoading}
        />
        <StatsCard
          title="Available Units"
          value={availableResources.length}
          linkTo="/resources"
          linkText="View all"
          color="green"
          isLoading={resourcesLoading}
        />
        <StatsCard
          title="Pending Alerts"
          value={pendingAlerts.length}
          linkTo="/alerts"
          linkText="View all"
          color="yellow"
          isLoading={alertsLoading}
        />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Incidents */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Active Incidents</CardTitle>
            <Link
              to="/incidents"
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              View all
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            {incidentsLoading && activeIncidents.length === 0 ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : activeIncidents.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No active incidents
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {activeIncidents.slice(0, 5).map((incident) => (
                  <IncidentRow key={incident.id} incident={incident} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pending Alerts */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Pending Alerts</CardTitle>
            <Link
              to="/alerts"
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              View all
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            {alertsLoading && pendingAlerts.length === 0 ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : pendingAlerts.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No pending alerts
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {pendingAlerts.slice(0, 5).map((alert) => (
                  <AlertRow key={alert.id} alert={alert} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Available Resources */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Available Resources</CardTitle>
            <Link
              to="/resources"
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              View all
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            {resourcesLoading && availableResources.length === 0 ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : availableResources.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No available resources
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-gray-200">
                {availableResources.slice(0, 6).map((resource) => (
                  <ResourceCard key={resource.id} resource={resource} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Sub-components
interface StatsCardProps {
  title: string;
  value: number;
  linkTo: string;
  linkText: string;
  color: 'red' | 'green' | 'yellow' | 'blue';
  isLoading?: boolean;
}

function StatsCard({ title, value, linkTo, linkText, color, isLoading }: StatsCardProps) {
  const colorStyles = {
    red: 'text-red-600',
    green: 'text-green-600',
    yellow: 'text-yellow-600',
    blue: 'text-blue-600',
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <h3 className="text-sm font-medium text-gray-500">{title}</h3>
        <div className="mt-2 flex items-baseline">
          {isLoading ? (
            <Spinner size="sm" />
          ) : (
            <span className={cn('text-4xl font-bold', colorStyles[color])}>
              {value}
            </span>
          )}
        </div>
        <Link
          to={linkTo}
          className="mt-3 inline-block text-sm text-blue-600 hover:text-blue-700"
        >
          {linkText} →
        </Link>
      </CardContent>
    </Card>
  );
}

function IncidentRow({ incident }: { incident: Incident }) {
  return (
    <Link
      to={`/incidents/${incident.id}`}
      className="block px-6 py-4 hover:bg-gray-50 transition-colors"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Badge
              className={cn(
                getPriorityBgColor(incident.priority),
                getPriorityColor(incident.priority)
              )}
            >
              P{incident.priority}
            </Badge>
            <span className="text-sm font-medium text-gray-900 truncate">
              {incident.title}
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500 truncate">
            {incident.address || 'No address'}
          </p>
        </div>
        <div className="ml-4 text-right">
          <span className="text-xs text-gray-400">
            {formatRelativeTime(incident.reported_at)}
          </span>
          <div className="mt-1">
            <Badge variant="secondary" size="sm">
              {getIncidentTypeLabel(incident.incident_type)}
            </Badge>
          </div>
        </div>
      </div>
    </Link>
  );
}

function AlertRow({ alert }: { alert: Alert }) {
  return (
    <Link
      to="/alerts"
      className="block px-6 py-4 hover:bg-gray-50 transition-colors"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Badge className={getSeverityBgColor(alert.severity)}>
              {getSeverityLabel(alert.severity)}
            </Badge>
            <span className="text-sm font-medium text-gray-900 truncate">
              {alert.title}
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500 truncate">
            {alert.source}
          </p>
        </div>
        <div className="ml-4 text-right">
          <span className="text-xs text-gray-400">
            {formatRelativeTime(alert.created_at)}
          </span>
          <div className="mt-1">
            <Badge variant="secondary" size="sm">
              {getAlertTypeLabel(alert.alert_type)}
            </Badge>
          </div>
        </div>
      </div>
    </Link>
  );
}

function ResourceCard({ resource }: { resource: Resource }) {
  return (
    <div className="px-6 py-4">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
          <span className="text-green-700 font-semibold">
            {resource.call_sign?.[0] || resource.name[0]}
          </span>
        </div>
        <div>
          <p className="font-medium text-gray-900">
            {resource.call_sign || resource.name}
          </p>
          <p className="text-sm text-gray-500 capitalize">{resource.resource_type}</p>
        </div>
      </div>
    </div>
  );
}
