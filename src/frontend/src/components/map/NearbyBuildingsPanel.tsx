import { useMemo } from 'react';
import type { Building, BuildingType, HazardLevel, Incident } from '../../types';
import { cn } from '../../utils';

/**
 * Calculate the Haversine distance between two lat/lng points.
 * Returns distance in kilometers.
 */
function calculateDistance(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number
): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

const HAZARD_LEVEL_COLORS: Record<HazardLevel, string> = {
  low: 'bg-green-500',
  moderate: 'bg-yellow-500',
  high: 'bg-orange-500',
  extreme: 'bg-red-500',
};

const HAZARD_LEVEL_LABELS: Record<HazardLevel, string> = {
  low: 'Low',
  moderate: 'Moderate',
  high: 'High',
  extreme: 'Extreme',
};

const BUILDING_TYPE_LABELS: Record<BuildingType, string> = {
  residential_single: 'Residential (Single)',
  residential_multi: 'Residential (Multi)',
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

const INCIDENT_TYPE_LABELS: Record<string, string> = {
  fire: 'Fire',
  medical: 'Medical',
  police: 'Police',
  traffic: 'Traffic',
  hazmat: 'HazMat',
  rescue: 'Rescue',
  other: 'Other',
};

interface NearbyBuildingsPanelProps {
  incident: Incident;
  buildings: Building[];
  isLoading?: boolean;
  onBuildingSelect: (building: Building) => void;
  onViewDetails: (building: Building) => void;
  onClose?: () => void;
  className?: string;
}

interface BuildingWithDistance {
  building: Building;
  distance: number;
}

export function NearbyBuildingsPanel({
  incident,
  buildings,
  isLoading = false,
  onBuildingSelect,
  onViewDetails,
  onClose,
  className,
}: NearbyBuildingsPanelProps) {
  const sortedBuildings: BuildingWithDistance[] = useMemo(() => {
    if (incident.latitude == null || incident.longitude == null) {
      return buildings.map((building) => ({
        building,
        distance: 0,
      }));
    }

    return buildings
      .map((building) => ({
        building,
        distance: calculateDistance(
          incident.latitude!,
          incident.longitude!,
          building.latitude,
          building.longitude
        ),
      }))
      .sort((a, b) => a.distance - b.distance);
  }, [incident.latitude, incident.longitude, buildings]);

  const incidentTypeLabel =
    INCIDENT_TYPE_LABELS[incident.incident_type] || incident.incident_type;

  return (
    <div
      className={cn(
        'bg-white rounded-lg shadow-lg max-h-[400px] flex flex-col overflow-hidden',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <div className="flex items-center gap-2 min-w-0">
          <h3 className="text-sm font-semibold text-gray-900 truncate">
            Buildings Near Incident
          </h3>
          <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-700 flex-shrink-0">
            {buildings.length}
          </span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="ml-2 flex-shrink-0 p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close panel"
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Incident context subtitle */}
      <div className="px-4 py-2 bg-gray-50 border-b border-gray-100">
        <p className="text-xs text-gray-500 truncate">
          <span className="font-medium text-gray-700">{incidentTypeLabel}</span>
          {incident.address && (
            <span>
              {' '}
              &mdash; {incident.address}
            </span>
          )}
        </p>
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-10">
            <svg
              className="animate-spin h-6 w-6 text-blue-500"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span className="ml-2 text-sm text-gray-500">
              Loading nearby buildings...
            </span>
          </div>
        ) : sortedBuildings.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-center px-4">
            <svg
              className="w-10 h-10 text-gray-300 mb-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
              />
            </svg>
            <p className="text-sm text-gray-500">
              No buildings found within range
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {sortedBuildings.map(({ building, distance }) => (
              <li
                key={building.id}
                className="px-3 py-2 hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => onBuildingSelect(building)}
              >
                {/* Row 1: Name + Distance */}
                <div className="flex items-start justify-between gap-2">
                  <span className="text-sm font-bold text-gray-900 truncate">
                    {building.name}
                  </span>
                  <span className="text-sm font-medium text-blue-600 flex-shrink-0 whitespace-nowrap">
                    {distance < 1
                      ? `${(distance * 1000).toFixed(0)} m`
                      : `${distance.toFixed(2)} km`}
                  </span>
                </div>

                {/* Row 2: Address */}
                <p className="text-xs text-gray-500 truncate mt-0.5">
                  {building.full_address}
                </p>

                {/* Row 3: Badges and info */}
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  {/* Building type badge */}
                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-700">
                    {BUILDING_TYPE_LABELS[building.building_type] ||
                      building.building_type}
                  </span>

                  {/* Hazard level dot */}
                  <span className="inline-flex items-center gap-1">
                    <span
                      className={cn(
                        'w-2 h-2 rounded-full flex-shrink-0',
                        HAZARD_LEVEL_COLORS[building.hazard_level]
                      )}
                      title={`Hazard: ${HAZARD_LEVEL_LABELS[building.hazard_level]}`}
                    />
                    <span className="text-[10px] text-gray-500">
                      {HAZARD_LEVEL_LABELS[building.hazard_level]}
                    </span>
                  </span>

                  {/* Floor count */}
                  <span className="text-[10px] text-gray-500">
                    {building.total_floors}{' '}
                    {building.total_floors === 1 ? 'floor' : 'floors'}
                  </span>
                </div>

                {/* Row 4: Safety icons + View button */}
                <div className="flex items-center justify-between mt-1.5">
                  <div className="flex items-center gap-2">
                    {/* Sprinkler */}
                    <span
                      className={cn(
                        'inline-flex items-center gap-0.5 text-[10px]',
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
                        className="w-3.5 h-3.5"
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
                      <span>Sprinkler</span>
                    </span>

                    {/* Fire alarm */}
                    <span
                      className={cn(
                        'inline-flex items-center gap-0.5 text-[10px]',
                        building.has_fire_alarm
                          ? 'text-red-500'
                          : 'text-gray-300'
                      )}
                      title={
                        building.has_fire_alarm
                          ? 'Fire alarm present'
                          : 'No fire alarm'
                      }
                    >
                      <svg
                        className="w-3.5 h-3.5"
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
                      <span>Alarm</span>
                    </span>

                    {/* HazMat */}
                    <span
                      className={cn(
                        'inline-flex items-center gap-0.5 text-[10px]',
                        building.has_hazmat
                          ? 'text-amber-600'
                          : 'text-gray-300'
                      )}
                      title={
                        building.has_hazmat
                          ? 'Hazardous materials present'
                          : 'No hazardous materials'
                      }
                    >
                      <svg
                        className="w-3.5 h-3.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
                        />
                      </svg>
                      <span>HazMat</span>
                    </span>
                  </div>

                  {/* View button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onViewDetails(building);
                    }}
                    className="px-2 py-0.5 text-xs font-medium text-blue-600 bg-blue-50 rounded hover:bg-blue-100 transition-colors"
                  >
                    View
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default NearbyBuildingsPanel;
