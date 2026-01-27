/**
 * FloorSelector Component
 * Horizontal floor navigation strip for multi-floor buildings.
 */

import { cn } from '../../utils';
import type { FloorPlan } from '../../types';

interface FloorSelectorProps {
  floorPlans: FloorPlan[];
  selectedFloorId: string | null;
  onSelectFloor: (floor: FloorPlan) => void;
  className?: string;
}

function getFloorLabel(plan: FloorPlan): string {
  if (plan.floor_name) return plan.floor_name;
  if (plan.floor_number < 0) return `B${Math.abs(plan.floor_number)}`;
  if (plan.floor_number === 0) return 'G';
  return `${plan.floor_number}`;
}

export function FloorSelector({
  floorPlans,
  selectedFloorId,
  onSelectFloor,
  className,
}: FloorSelectorProps) {
  if (floorPlans.length === 0) return null;

  return (
    <div className={cn('flex items-center gap-1 overflow-x-auto pb-1', className)}>
      <span className="text-xs text-gray-500 mr-2 flex-shrink-0">Floor:</span>
      {floorPlans.map((plan) => (
        <button
          key={plan.id}
          onClick={() => onSelectFloor(plan)}
          className={cn(
            'px-3 py-1.5 text-sm rounded-lg whitespace-nowrap transition-colors flex-shrink-0',
            selectedFloorId === plan.id
              ? 'bg-blue-600 text-white shadow-sm'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          )}
          title={plan.floor_name || `Floor ${plan.floor_number}`}
        >
          {getFloorLabel(plan)}
        </button>
      ))}
    </div>
  );
}
