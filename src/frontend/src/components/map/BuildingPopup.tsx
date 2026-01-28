/**
 * BuildingPopup Component
 *
 * Renders building information inside a Leaflet map popup.
 * Pure React component with no Leaflet dependencies.
 */

import { Badge } from '../ui';
import { cn } from '../../utils';
import type { Building, HazardLevel } from '../../types';

export interface BuildingPopupProps {
  building: Building;
  distance?: number;
  onViewDetails: (building: Building) => void;
  onViewFloorPlans: (building: Building) => void;
}

const hazardStyles: Record<HazardLevel, string> = {
  low: 'bg-green-100 text-green-700',
  moderate: 'bg-yellow-100 text-yellow-700',
  high: 'bg-orange-100 text-orange-700',
  extreme: 'bg-red-100 text-red-700',
};

const safetyFeatures = [
  { key: 'has_sprinkler_system', label: 'Sprinkler', icon: '\u{1F6BF}' },
  { key: 'has_fire_alarm', label: 'Fire Alarm', icon: '\u{1F514}' },
  { key: 'has_standpipe', label: 'Standpipe', icon: '\u{1F6B0}' },
  { key: 'has_elevator', label: 'Elevator', icon: '\u{1F6D7}' },
  { key: 'has_generator', label: 'Generator', icon: '\u26A1' },
  { key: 'knox_box', label: 'Knox Box', icon: '\u{1F511}' },
] as const;

export function BuildingPopup({
  building,
  distance,
  onViewDetails,
  onViewFloorPlans,
}: BuildingPopupProps) {
  const floorLabel = building.total_floors === 1 ? 'floor' : 'floors';
  const basementText =
    building.basement_levels > 0
      ? ` (${building.basement_levels} basement)`
      : '';

  const truncatedNotes =
    building.tactical_notes && building.tactical_notes.length > 100
      ? `${building.tactical_notes.slice(0, 100)}...`
      : building.tactical_notes;

  return (
    <div className="max-w-[320px] space-y-2">
      {/* Header: Name + Building Type */}
      <div className="flex items-start justify-between gap-2">
        <p className="font-bold text-sm text-gray-900 leading-tight">
          {building.name}
        </p>
        <Badge size="sm" variant="secondary" className="capitalize shrink-0">
          {building.building_type.replace(/_/g, ' ')}
        </Badge>
      </div>

      {/* Address */}
      <p className="text-xs text-gray-600">{building.full_address}</p>

      {/* Hazard Level + Distance */}
      <div className="flex items-center gap-2 flex-wrap">
        <Badge size="sm" className={hazardStyles[building.hazard_level]}>
          {building.hazard_level.charAt(0).toUpperCase() +
            building.hazard_level.slice(1)}{' '}
          Hazard
        </Badge>
        {distance !== undefined && (
          <span className="text-xs text-gray-500">
            {distance.toFixed(1)} km away
          </span>
        )}
      </div>

      {/* Building Info: Floors + Occupancy */}
      <div className="text-xs text-gray-700">
        <span>
          {building.total_floors} {floorLabel}
          {basementText}
        </span>
        {building.occupancy_type && (
          <>
            <span className="mx-1 text-gray-300">|</span>
            <span className="capitalize">
              {building.occupancy_type.replace(/_/g, ' ')}
            </span>
          </>
        )}
      </div>

      {/* Safety Features */}
      <div className="flex flex-wrap gap-1">
        {safetyFeatures.map(({ key, label, icon }) => {
          const value = building[key as keyof Building];
          if (!value) return null;
          return (
            <span
              key={key}
              title={label}
              className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700"
            >
              <span>{icon}</span>
              {label}
            </span>
          );
        })}
        {building.has_hazmat && (
          <span
            title="Hazardous Materials"
            className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-red-50 text-red-700"
          >
            <span>{'\u2622\uFE0F'}</span>
            HAZMAT
          </span>
        )}
      </div>

      {/* Tactical Notes */}
      {building.tactical_notes && (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-1.5">
          <p className="text-[10px] font-semibold text-yellow-800 mb-0.5">
            Tactical Notes
          </p>
          <p className="text-[10px] text-yellow-700 leading-snug">
            {truncatedNotes}
          </p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-2 pt-1">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onViewDetails(building);
          }}
          className={cn(
            'flex-1 px-3 py-1.5 text-xs font-medium rounded',
            'bg-blue-600 text-white hover:bg-blue-700',
            'transition-colors'
          )}
        >
          View Details
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onViewFloorPlans(building);
          }}
          className={cn(
            'flex-1 px-3 py-1.5 text-xs font-medium rounded',
            'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300',
            'transition-colors'
          )}
        >
          Floor Plans
        </button>
      </div>
    </div>
  );
}

export default BuildingPopup;
