/**
 * BuildingInfoPanel Component
 * Sidebar panel showing building specs, safety features, access info, and contacts.
 * Extracted from BuildingsPage BuildingDetailModal.
 */

import { Badge } from '../ui';
import { cn } from '../../utils';
import type { Building, HazardLevel } from '../../types';

interface BuildingInfoPanelProps {
  building: Building;
  className?: string;
}

const hazardLevelConfig: Record<HazardLevel, { color: string; bgColor: string }> = {
  low: { color: 'text-green-700', bgColor: 'bg-green-100' },
  moderate: { color: 'text-yellow-700', bgColor: 'bg-yellow-100' },
  high: { color: 'text-orange-700', bgColor: 'bg-orange-100' },
  extreme: { color: 'text-red-700', bgColor: 'bg-red-100' },
};

export function BuildingInfoPanel({ building, className }: BuildingInfoPanelProps) {
  const hazardStyle = hazardLevelConfig[building.hazard_level];

  return (
    <div className={cn('space-y-5', className)}>
      {/* Building Specs */}
      <div className="grid grid-cols-3 gap-3 p-3 bg-gray-50 rounded-lg">
        <div>
          <p className="text-xs text-gray-500">Floors</p>
          <p className="font-semibold text-sm">{building.total_floors}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Basements</p>
          <p className="font-semibold text-sm">{building.basement_levels}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Year Built</p>
          <p className="font-semibold text-sm">{building.year_built || 'Unknown'}</p>
        </div>
      </div>

      {/* Hazard Level */}
      <div>
        <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Hazard Level</h4>
        <Badge className={cn(hazardStyle.bgColor, hazardStyle.color)}>
          {building.hazard_level}
        </Badge>
      </div>

      {/* Safety Features */}
      <div>
        <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Safety Features</h4>
        <div className="flex flex-wrap gap-1.5">
          {building.has_sprinkler_system && (
            <Badge className="bg-blue-100 text-blue-700" size="sm">Sprinkler</Badge>
          )}
          {building.has_fire_alarm && (
            <Badge className="bg-blue-100 text-blue-700" size="sm">Fire Alarm</Badge>
          )}
          {building.has_standpipe && (
            <Badge className="bg-blue-100 text-blue-700" size="sm">Standpipe</Badge>
          )}
          {building.has_elevator && (
            <Badge className="bg-blue-100 text-blue-700" size="sm">
              Elevator ({building.elevator_count || 1})
            </Badge>
          )}
          {building.has_generator && (
            <Badge className="bg-blue-100 text-blue-700" size="sm">Generator</Badge>
          )}
          {building.knox_box && (
            <Badge className="bg-blue-100 text-blue-700" size="sm">Knox Box</Badge>
          )}
          {building.has_hazmat && (
            <Badge className="bg-red-100 text-red-700" size="sm">HAZMAT</Badge>
          )}
          {!building.has_sprinkler_system && !building.has_fire_alarm && !building.has_standpipe &&
           !building.has_elevator && !building.has_generator && !building.knox_box && !building.has_hazmat && (
            <span className="text-sm text-gray-400">None recorded</span>
          )}
        </div>
      </div>

      {/* Access Information */}
      {(building.primary_entrance || building.staging_area || building.key_box_location) && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Access</h4>
          <div className="space-y-1.5 text-sm">
            {building.primary_entrance && (
              <p><span className="text-gray-500">Entrance:</span> {building.primary_entrance}</p>
            )}
            {building.staging_area && (
              <p><span className="text-gray-500">Staging:</span> {building.staging_area}</p>
            )}
            {building.key_box_location && (
              <p><span className="text-gray-500">Key Box:</span> {building.key_box_location}</p>
            )}
          </div>
        </div>
      )}

      {/* Contacts */}
      {(building.emergency_contact_name || building.owner_name) && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Contacts</h4>
          <div className="space-y-1.5 text-sm">
            {building.emergency_contact_name && (
              <p>
                <span className="text-gray-500">Emergency:</span> {building.emergency_contact_name}
                {building.emergency_contact_phone && ` - ${building.emergency_contact_phone}`}
              </p>
            )}
            {building.owner_name && (
              <p>
                <span className="text-gray-500">Owner:</span> {building.owner_name}
                {building.owner_phone && ` - ${building.owner_phone}`}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Tactical Notes */}
      {building.tactical_notes && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Tactical Notes</h4>
          <p className="text-sm text-gray-700 bg-yellow-50 p-2.5 rounded">{building.tactical_notes}</p>
        </div>
      )}
    </div>
  );
}
