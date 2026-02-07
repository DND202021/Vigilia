/**
 * TimeRangePicker Component
 *
 * Preset time range selector with buttons for common intervals.
 * Uses date-fns for date calculations and calls onRangeChange callback
 * when user selects a preset.
 */
import { useState } from 'react';
import { subHours, subDays } from 'date-fns';

interface TimeRangePickerProps {
  onRangeChange: (start: Date, end: Date) => void;
  className?: string;
}

interface TimeRangePreset {
  label: string;
  value: () => [Date, Date];
}

const PRESETS: TimeRangePreset[] = [
  {
    label: 'Last 1 hour',
    value: () => [subHours(new Date(), 1), new Date()],
  },
  {
    label: 'Last 6 hours',
    value: () => [subHours(new Date(), 6), new Date()],
  },
  {
    label: 'Last 24 hours',
    value: () => [subHours(new Date(), 24), new Date()],
  },
  {
    label: 'Last 7 days',
    value: () => [subDays(new Date(), 7), new Date()],
  },
];

export function TimeRangePicker({ onRangeChange, className = '' }: TimeRangePickerProps) {
  const [activePreset, setActivePreset] = useState<string>('Last 1 hour');

  const handlePresetClick = (preset: TimeRangePreset) => {
    setActivePreset(preset.label);
    const [start, end] = preset.value();
    onRangeChange(start, end);
  };

  return (
    <div className={`flex gap-2 ${className}`}>
      {PRESETS.map((preset) => {
        const isActive = activePreset === preset.label;
        return (
          <button
            key={preset.label}
            onClick={() => handlePresetClick(preset)}
            className={`px-3 py-1.5 text-sm border rounded-md transition-colors ${
              isActive
                ? 'bg-blue-500 text-white border-blue-600'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-100'
            }`}
          >
            {preset.label}
          </button>
        );
      })}
    </div>
  );
}

export default TimeRangePicker;
