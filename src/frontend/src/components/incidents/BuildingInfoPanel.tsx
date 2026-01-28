/**
 * BuildingInfoPanel Component
 *
 * A collapsible panel displaying detailed building information for incident response.
 * Shows building details, safety features, pre-incident plans, tactical notes,
 * and emergency contacts.
 */

import { useState } from 'react';
import type { Building, BuildingType, HazardLevel } from '../../types';
import { cn } from '../../utils';

export interface BuildingInfoPanelProps {
  building: Building;
  isCollapsed?: boolean;
  onToggle?: () => void;
  onViewFloorPlans?: () => void;
  className?: string;
}

const HAZARD_LEVEL_STYLES: Record<HazardLevel, { bg: string; text: string }> = {
  low: { bg: 'bg-green-100', text: 'text-green-700' },
  moderate: { bg: 'bg-yellow-100', text: 'text-yellow-700' },
  high: { bg: 'bg-orange-100', text: 'text-orange-700' },
  extreme: { bg: 'bg-red-100', text: 'text-red-700' },
};

const HAZARD_LEVEL_LABELS: Record<HazardLevel, string> = {
  low: 'Low',
  moderate: 'Moderate',
  high: 'High',
  extreme: 'Extreme',
};

const BUILDING_TYPE_LABELS: Record<BuildingType, string> = {
  residential_single: 'Residential Single',
  residential_multi: 'Residential Multi',
  commercial: 'Commercial',
  industrial: 'Industrial',
  institutional: 'Institutional',
  healthcare: 'Healthcare',
  educational: 'Educational',
  government: 'Government',
  religious: 'Religious',
  mixed_use: 'Mixed Use',
  parking: 'Parking',
  warehouse: 'Warehouse',
  high_rise: 'High Rise',
  other: 'Other',
};

export function BuildingInfoPanel({
  building,
  isCollapsed: controlledIsCollapsed,
  onToggle,
  onViewFloorPlans,
  className,
}: BuildingInfoPanelProps) {
  const [internalIsCollapsed, setInternalIsCollapsed] = useState(false);

  // Support both controlled and uncontrolled modes
  const isCollapsed = controlledIsCollapsed ?? internalIsCollapsed;

  const handleToggle = () => {
    if (onToggle) {
      onToggle();
    } else {
      setInternalIsCollapsed((prev) => !prev);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const hazardStyles = HAZARD_LEVEL_STYLES[building.hazard_level];
  const hazardLabel = HAZARD_LEVEL_LABELS[building.hazard_level];
  const buildingTypeLabel =
    BUILDING_TYPE_LABELS[building.building_type] || building.building_type;

  const hasEmergencyContacts =
    building.owner_name ||
    building.owner_phone ||
    building.manager_name ||
    building.manager_phone ||
    building.emergency_contact_name ||
    building.emergency_contact_phone;

  return (
    <div
      className={cn(
        'bg-white rounded-lg shadow-lg overflow-hidden transition-all duration-300',
        className
      )}
    >
      {/* Header - Always Visible */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b border-gray-200 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={handleToggle}
      >
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <h3 className="text-sm font-bold text-gray-900 truncate">
            {building.name}
          </h3>
          <span
            className={cn(
              'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium flex-shrink-0',
              hazardStyles.bg,
              hazardStyles.text
            )}
          >
            {hazardLabel}
          </span>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleToggle();
          }}
          className="ml-2 p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0"
          aria-label={isCollapsed ? 'Expand panel' : 'Collapse panel'}
        >
          <svg
            className={cn(
              'w-5 h-5 transition-transform duration-200',
              isCollapsed ? '' : 'rotate-180'
            )}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>
      </div>

      {/* Collapsible Content */}
      <div
        className={cn(
          'transition-all duration-300 ease-in-out overflow-hidden',
          isCollapsed ? 'max-h-0' : 'max-h-[2000px]'
        )}
      >
        <div className="p-4 space-y-4">
          {/* Address & Type */}
          <div className="space-y-1">
            <p className="text-sm text-gray-700">{building.full_address}</p>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
              {buildingTypeLabel}
            </span>
          </div>

          {/* Quick Stats */}
          <div className="flex items-center gap-4 py-2 border-t border-b border-gray-100">
            {/* Floor Count */}
            <div className="flex items-center gap-1.5" title="Total floors">
              <svg
                className="w-4 h-4 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                />
              </svg>
              <span className="text-xs font-medium text-gray-700">
                {building.total_floors}{' '}
                {building.total_floors === 1 ? 'floor' : 'floors'}
              </span>
            </div>

            {/* Occupancy Type */}
            {building.occupancy_type && (
              <div
                className="flex items-center gap-1.5"
                title="Occupancy type"
              >
                <svg
                  className="w-4 h-4 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
                <span className="text-xs font-medium text-gray-700 capitalize">
                  {building.occupancy_type.replace(/_/g, ' ')}
                </span>
              </div>
            )}

            {/* Sprinkler System */}
            <div
              className={cn(
                'flex items-center gap-1',
                building.has_sprinkler_system
                  ? 'text-blue-600'
                  : 'text-gray-300'
              )}
              title={
                building.has_sprinkler_system
                  ? 'Sprinkler system present'
                  : 'No sprinkler system'
              }
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 3v1m0 16v1m-8-9H3m18 0h-1m-2.636-5.364l-.707.707M6.343 17.657l-.707.707m12.728 0l-.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z"
                />
              </svg>
            </div>

            {/* Fire Alarm */}
            <div
              className={cn(
                'flex items-center gap-1',
                building.has_fire_alarm ? 'text-red-500' : 'text-gray-300'
              )}
              title={
                building.has_fire_alarm
                  ? 'Fire alarm present'
                  : 'No fire alarm'
              }
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                />
              </svg>
            </div>
          </div>

          {/* Pre-Incident Plan */}
          {building.pre_incident_plan && (
            <div className="space-y-1.5">
              <h4 className="text-xs font-semibold text-gray-900 uppercase tracking-wide">
                Pre-Incident Plan
              </h4>
              <div className="bg-amber-50 border border-amber-200 rounded p-3">
                <p className="text-sm text-amber-900 whitespace-pre-wrap leading-relaxed">
                  {building.pre_incident_plan}
                </p>
              </div>
            </div>
          )}

          {/* Tactical Notes */}
          {building.tactical_notes && (
            <div className="space-y-1.5">
              <h4 className="text-xs font-semibold text-gray-900 uppercase tracking-wide">
                Tactical Notes
              </h4>
              <div className="bg-gray-100 border border-gray-200 rounded p-3">
                <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                  {building.tactical_notes}
                </p>
              </div>
            </div>
          )}

          {/* Emergency Contacts */}
          {hasEmergencyContacts && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-gray-900 uppercase tracking-wide">
                Emergency Contacts
              </h4>
              <div className="space-y-2">
                {/* Owner */}
                {(building.owner_name || building.owner_phone) && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">Owner:</span>
                    <div className="text-right">
                      {building.owner_name && (
                        <span className="text-gray-900">
                          {building.owner_name}
                        </span>
                      )}
                      {building.owner_phone && (
                        <a
                          href={`tel:${building.owner_phone}`}
                          className="ml-2 text-blue-600 hover:text-blue-800 hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {building.owner_phone}
                        </a>
                      )}
                    </div>
                  </div>
                )}

                {/* Manager */}
                {(building.manager_name || building.manager_phone) && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">Manager:</span>
                    <div className="text-right">
                      {building.manager_name && (
                        <span className="text-gray-900">
                          {building.manager_name}
                        </span>
                      )}
                      {building.manager_phone && (
                        <a
                          href={`tel:${building.manager_phone}`}
                          className="ml-2 text-blue-600 hover:text-blue-800 hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {building.manager_phone}
                        </a>
                      )}
                    </div>
                  </div>
                )}

                {/* Emergency Contact */}
                {(building.emergency_contact_name ||
                  building.emergency_contact_phone) && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">Emergency:</span>
                    <div className="text-right">
                      {building.emergency_contact_name && (
                        <span className="text-gray-900">
                          {building.emergency_contact_name}
                        </span>
                      )}
                      {building.emergency_contact_phone && (
                        <a
                          href={`tel:${building.emergency_contact_phone}`}
                          className="ml-2 text-blue-600 hover:text-blue-800 hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {building.emergency_contact_phone}
                        </a>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Actions Footer */}
          <div className="flex gap-2 pt-2 border-t border-gray-100">
            {onViewFloorPlans && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onViewFloorPlans();
                }}
                className={cn(
                  'flex-1 px-3 py-2 text-sm font-medium rounded',
                  'bg-blue-600 text-white hover:bg-blue-700',
                  'transition-colors'
                )}
              >
                View Floor Plans
              </button>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                handlePrint();
              }}
              className={cn(
                'flex-1 px-3 py-2 text-sm font-medium rounded',
                'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300',
                'transition-colors'
              )}
            >
              Print
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BuildingInfoPanel;
