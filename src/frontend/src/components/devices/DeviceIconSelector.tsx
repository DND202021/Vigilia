/**
 * DeviceIconSelector Component
 *
 * A UI component for selecting device icons and colors.
 * Supports categorized icon selection and color customization.
 */

import { useState, useMemo } from 'react';
import {
  DEFAULT_DEVICE_ICON_CONFIGS,
  DEVICE_ICON_COLORS,
  getDeviceIconsByCategory,
  type DeviceIconType,
  type DeviceIconCategory,
} from '../../types';
import { cn } from '../../utils';

interface DeviceIconSelectorProps {
  selectedIconType?: DeviceIconType | string;
  selectedColor?: string;
  onIconTypeChange: (iconType: DeviceIconType) => void;
  onColorChange: (color: string) => void;
  className?: string;
}

const CATEGORIES: { value: DeviceIconCategory; label: string; icon: string }[] = [
  { value: 'surveillance', label: 'Surveillance', icon: '📹' },
  { value: 'motion', label: 'Motion', icon: '👁️' },
  { value: 'access', label: 'Access', icon: '🚪' },
  { value: 'environmental', label: 'Environmental', icon: '🌡️' },
  { value: 'communication', label: 'Communication', icon: '📡' },
  { value: 'tactical', label: 'Tactical', icon: '🎯' },
];

export function DeviceIconSelector({
  selectedIconType,
  selectedColor,
  onIconTypeChange,
  onColorChange,
  className,
}: DeviceIconSelectorProps) {
  const [activeCategory, setActiveCategory] = useState<DeviceIconCategory>('surveillance');
  const [showColorPicker, setShowColorPicker] = useState(false);

  const categoryIcons = useMemo(() => {
    return getDeviceIconsByCategory(activeCategory);
  }, [activeCategory]);

  const selectedConfig = useMemo(() => {
    return DEFAULT_DEVICE_ICON_CONFIGS.find((c) => c.type === selectedIconType);
  }, [selectedIconType]);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Current Selection Preview */}
      <div className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
        <div
          className={cn(
            'w-12 h-12 rounded-full flex items-center justify-center text-xl',
            'ring-2 ring-gray-300 shadow-md',
            selectedColor || selectedConfig?.color || 'bg-gray-400'
          )}
        >
          {selectedConfig?.icon || '📍'}
        </div>
        <div className="flex-1">
          <div className="font-medium text-gray-900">
            {selectedConfig?.label || 'Select an icon'}
          </div>
          <div className="text-sm text-gray-500">
            {selectedConfig?.description || 'Choose from the options below'}
          </div>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex flex-wrap gap-1 border-b">
        {CATEGORIES.map((category) => (
          <button
            key={category.value}
            onClick={() => setActiveCategory(category.value)}
            className={cn(
              'px-3 py-2 text-sm font-medium rounded-t-lg transition-colors',
              'flex items-center gap-1.5',
              activeCategory === category.value
                ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-500'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
            )}
          >
            <span>{category.icon}</span>
            <span className="hidden sm:inline">{category.label}</span>
          </button>
        ))}
      </div>

      {/* Icon Grid */}
      <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
        {categoryIcons.map((config) => (
          <button
            key={config.type}
            onClick={() => onIconTypeChange(config.type)}
            className={cn(
              'p-2 rounded-lg border-2 transition-all',
              'flex flex-col items-center gap-1',
              'hover:border-blue-300 hover:bg-blue-50',
              selectedIconType === config.type
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 bg-white'
            )}
            title={config.description}
          >
            <span className="text-2xl">{config.icon}</span>
            <span className="text-[10px] text-gray-600 truncate w-full text-center">
              {config.label}
            </span>
          </button>
        ))}
      </div>

      {/* Color Selection */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700">Custom Color</label>
          <button
            type="button"
            onClick={() => setShowColorPicker(!showColorPicker)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {showColorPicker ? 'Hide colors' : 'Change color'}
          </button>
        </div>

        {showColorPicker && (
          <div className="grid grid-cols-6 sm:grid-cols-9 gap-2 p-2 bg-gray-50 rounded-lg">
            {/* Default (no custom color) */}
            <button
              onClick={() => onColorChange('')}
              className={cn(
                'w-8 h-8 rounded-full border-2 flex items-center justify-center',
                'bg-gradient-to-br from-gray-200 to-gray-400',
                !selectedColor
                  ? 'border-blue-500 ring-2 ring-blue-200'
                  : 'border-gray-300 hover:border-gray-400'
              )}
              title="Use default color"
            >
              {!selectedColor && (
                <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </button>

            {DEVICE_ICON_COLORS.map((color) => (
              <button
                key={color.value}
                onClick={() => onColorChange(color.value)}
                className={cn(
                  'w-8 h-8 rounded-full border-2 transition-transform hover:scale-110',
                  color.value,
                  selectedColor === color.value
                    ? 'border-blue-500 ring-2 ring-blue-200'
                    : 'border-transparent hover:border-gray-400'
                )}
                title={color.name}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Compact version for inline use in forms
 */
export function DeviceIconSelectorCompact({
  selectedIconType,
  selectedColor,
  onIconTypeChange,
  onColorChange,
}: DeviceIconSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);

  const selectedConfig = useMemo(() => {
    return DEFAULT_DEVICE_ICON_CONFIGS.find((c) => c.type === selectedIconType);
  }, [selectedIconType]);

  return (
    <div className="relative">
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 px-3 py-2 border rounded-lg',
          'hover:border-blue-300 hover:bg-gray-50 transition-colors',
          isOpen ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
        )}
      >
        <span
          className={cn(
            'w-6 h-6 rounded-full flex items-center justify-center text-sm',
            selectedColor || selectedConfig?.color || 'bg-gray-400'
          )}
        >
          {selectedConfig?.icon || '📍'}
        </span>
        <span className="text-sm text-gray-700">
          {selectedConfig?.label || 'Select icon'}
        </span>
        <svg
          className={cn('w-4 h-4 text-gray-400 transition-transform', isOpen && 'rotate-180')}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute z-20 mt-1 w-80 bg-white rounded-lg shadow-lg border p-3">
            <DeviceIconSelector
              selectedIconType={selectedIconType}
              selectedColor={selectedColor}
              onIconTypeChange={(type) => {
                onIconTypeChange(type);
                setIsOpen(false);
              }}
              onColorChange={onColorChange}
            />
          </div>
        </>
      )}
    </div>
  );
}

export default DeviceIconSelector;
