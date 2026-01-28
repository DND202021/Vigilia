/**
 * BuildingSelector Component
 *
 * A comprehensive building selection component with search, geolocation,
 * and keyboard navigation support.
 */

import React, { useRef, useState, useEffect, useCallback } from 'react';
import { buildingsApi } from '../../services/api';
import type { Building, HazardLevel, BuildingType } from '../../types';
import { cn } from '../../utils';
import { Badge } from '../ui/Badge';

export interface BuildingSelectorProps {
  onSelect: (building: Building | null) => void;
  initialValue?: Building | null;
  nearbyRadius?: number; // km for "near me" suggestions
  className?: string;
  disabled?: boolean;
  error?: string;
  label?: string;
}

const DEBOUNCE_MS = 300;

const hazardDotColor: Record<HazardLevel, string> = {
  low: 'bg-green-500',
  moderate: 'bg-yellow-500',
  high: 'bg-orange-500',
  extreme: 'bg-red-500',
};

const hazardBadgeVariant: Record<HazardLevel, 'success' | 'warning' | 'danger' | 'info'> = {
  low: 'success',
  moderate: 'warning',
  high: 'danger',
  extreme: 'danger',
};

const buildingTypeLabels: Partial<Record<BuildingType, string>> = {
  residential_single: 'Residential',
  residential_multi: 'Multi-Res',
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

export function BuildingSelector({
  onSelect,
  initialValue = null,
  nearbyRadius = 5,
  className,
  disabled = false,
  error,
  label,
}: BuildingSelectorProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Building[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isGeoLoading, setIsGeoLoading] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [selectedBuilding, setSelectedBuilding] = useState<Building | null>(initialValue);
  const [geoError, setGeoError] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Update internal state when initialValue changes
  useEffect(() => {
    setSelectedBuilding(initialValue);
  }, [initialValue]);

  // Debounced search
  const performSearch = useCallback(async (searchQuery: string) => {
    const trimmed = searchQuery.trim();
    if (!trimmed) {
      setResults([]);
      setIsOpen(false);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const data = await buildingsApi.search(trimmed, 10);
      setResults(data);
      setIsOpen(true);
      setHighlightedIndex(-1);
    } catch {
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setQuery(value);
      setGeoError(null);

      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      if (!value.trim()) {
        setResults([]);
        setIsOpen(false);
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      debounceTimerRef.current = setTimeout(() => {
        performSearch(value);
      }, DEBOUNCE_MS);
    },
    [performSearch],
  );

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setHighlightedIndex(-1);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightedIndex >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll('[data-result-item]');
      const item = items[highlightedIndex];
      if (item) {
        item.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [highlightedIndex]);

  const selectBuilding = useCallback(
    (building: Building) => {
      setSelectedBuilding(building);
      onSelect(building);
      setQuery('');
      setIsOpen(false);
      setHighlightedIndex(-1);
      setResults([]);
    },
    [onSelect],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (!isOpen || results.length === 0) {
        if (e.key === 'Escape') {
          setIsOpen(false);
          inputRef.current?.blur();
        }
        return;
      }

      switch (e.key) {
        case 'ArrowDown': {
          e.preventDefault();
          setHighlightedIndex((prev) =>
            prev < results.length - 1 ? prev + 1 : 0,
          );
          break;
        }
        case 'ArrowUp': {
          e.preventDefault();
          setHighlightedIndex((prev) =>
            prev > 0 ? prev - 1 : results.length - 1,
          );
          break;
        }
        case 'Enter': {
          e.preventDefault();
          if (highlightedIndex >= 0 && highlightedIndex < results.length) {
            selectBuilding(results[highlightedIndex]);
          }
          break;
        }
        case 'Escape': {
          e.preventDefault();
          setIsOpen(false);
          setHighlightedIndex(-1);
          inputRef.current?.blur();
          break;
        }
      }
    },
    [isOpen, results, highlightedIndex, selectBuilding],
  );

  const handleClear = useCallback(() => {
    setSelectedBuilding(null);
    onSelect(null);
    setQuery('');
    setResults([]);
    setIsOpen(false);
    setHighlightedIndex(-1);
    setGeoError(null);
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    inputRef.current?.focus();
  }, [onSelect]);

  const handleChangeBuilding = useCallback(() => {
    setSelectedBuilding(null);
    setQuery('');
    setResults([]);
    setIsOpen(false);
    setHighlightedIndex(-1);
    setGeoError(null);
    // Focus input after state update
    setTimeout(() => inputRef.current?.focus(), 0);
  }, []);

  const handleNearMe = useCallback(async () => {
    if (!navigator.geolocation) {
      setGeoError('Geolocation is not supported by your browser');
      return;
    }

    setIsGeoLoading(true);
    setGeoError(null);

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const { latitude, longitude } = position.coords;
          const data = await buildingsApi.getNearLocation(latitude, longitude, nearbyRadius);
          setResults(data);
          setIsOpen(true);
          setHighlightedIndex(-1);
        } catch {
          setGeoError('Failed to fetch nearby buildings');
        } finally {
          setIsGeoLoading(false);
        }
      },
      (geoError) => {
        setIsGeoLoading(false);
        switch (geoError.code) {
          case geoError.PERMISSION_DENIED:
            setGeoError('Location permission denied');
            break;
          case geoError.POSITION_UNAVAILABLE:
            setGeoError('Location unavailable');
            break;
          case geoError.TIMEOUT:
            setGeoError('Location request timed out');
            break;
          default:
            setGeoError('Failed to get your location');
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000,
      },
    );
  }, [nearbyRadius]);

  // If a building is selected, show the summary card
  if (selectedBuilding) {
    return (
      <div className={cn('w-full', className)}>
        {label && (
          <label className="mb-1.5 block text-sm font-medium text-gray-700">
            {label}
          </label>
        )}
        <div
          className={cn(
            'rounded-lg border border-gray-200 bg-white p-4 shadow-sm',
            disabled && 'opacity-50',
          )}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              {/* Building Name */}
              <div className="truncate text-base font-semibold text-gray-900">
                {selectedBuilding.name}
              </div>

              {/* Address */}
              <div className="mt-1 truncate text-sm text-gray-500">
                {selectedBuilding.full_address}
              </div>

              {/* Details Row */}
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {/* Hazard Level Badge */}
                <Badge
                  variant={hazardBadgeVariant[selectedBuilding.hazard_level] ?? 'default'}
                  size="sm"
                >
                  {selectedBuilding.hazard_level.charAt(0).toUpperCase() +
                    selectedBuilding.hazard_level.slice(1)}{' '}
                  Hazard
                </Badge>

                {/* Floor Count */}
                <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                  {selectedBuilding.total_floors}{' '}
                  {selectedBuilding.total_floors === 1 ? 'Floor' : 'Floors'}
                  {selectedBuilding.basement_levels > 0 &&
                    ` + ${selectedBuilding.basement_levels} Basement`}
                </span>

                {/* Building Type */}
                <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                  {buildingTypeLabels[selectedBuilding.building_type] ??
                    selectedBuilding.building_type}
                </span>
              </div>
            </div>

            {/* Change Button */}
            {!disabled && (
              <button
                type="button"
                onClick={handleChangeBuilding}
                className={cn(
                  'shrink-0 rounded-md bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-700',
                  'hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20',
                  'transition-colors',
                )}
                aria-label="Change building selection"
              >
                Change
              </button>
            )}
          </div>
        </div>
        {error && <p className="mt-1.5 text-sm text-red-600">{error}</p>}
      </div>
    );
  }

  // Search mode
  return (
    <div ref={containerRef} className={cn('relative w-full', className)}>
      {label && (
        <label
          htmlFor="building-selector-input"
          className="mb-1.5 block text-sm font-medium text-gray-700"
        >
          {label}
        </label>
      )}

      {/* Search Input */}
      <div className="relative">
        {/* Search Icon */}
        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
          <svg
            className="h-4 w-4 text-gray-400"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
            />
          </svg>
        </div>

        <input
          ref={inputRef}
          id="building-selector-input"
          type="text"
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (results.length > 0 && query.trim()) {
              setIsOpen(true);
            }
          }}
          placeholder="Search buildings..."
          disabled={disabled}
          className={cn(
            'w-full rounded-lg border bg-white py-2 pl-9 pr-24 text-sm shadow-sm',
            'placeholder:text-gray-400',
            'focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20',
            'transition-colors',
            disabled && 'cursor-not-allowed bg-gray-50 opacity-50',
            error
              ? 'border-red-300 focus:border-red-500 focus:ring-red-500/20'
              : 'border-gray-300',
          )}
          role="combobox"
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          aria-autocomplete="list"
          aria-controls="building-selector-results"
          aria-invalid={!!error}
          aria-describedby={error ? 'building-selector-error' : undefined}
        />

        {/* Right side buttons */}
        <div className="absolute inset-y-0 right-0 flex items-center gap-1 pr-2">
          {/* Loading Spinner */}
          {isLoading && (
            <svg
              className="h-4 w-4 animate-spin text-gray-400"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
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
          )}

          {/* Clear Button */}
          {query && !isLoading && (
            <button
              type="button"
              onClick={handleClear}
              disabled={disabled}
              className={cn(
                'rounded p-0.5 text-gray-400 hover:text-gray-600',
                'focus:outline-none focus:ring-2 focus:ring-blue-500/20',
                disabled && 'cursor-not-allowed',
              )}
              aria-label="Clear search"
            >
              <svg
                className="h-4 w-4"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          )}

          {/* Near Me Button */}
          <button
            type="button"
            onClick={handleNearMe}
            disabled={disabled || isGeoLoading}
            className={cn(
              'ml-1 rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-700',
              'hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20',
              'transition-colors',
              (disabled || isGeoLoading) && 'cursor-not-allowed opacity-50',
            )}
            aria-label="Find buildings near my location"
          >
            {isGeoLoading ? (
              <svg
                className="h-3.5 w-3.5 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
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
            ) : (
              <span className="flex items-center gap-1">
                <svg
                  className="h-3.5 w-3.5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"
                  />
                </svg>
                Near Me
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Error Messages */}
      {(error || geoError) && (
        <p
          id="building-selector-error"
          className="mt-1.5 text-sm text-red-600"
          role="alert"
        >
          {error || geoError}
        </p>
      )}

      {/* Results Dropdown */}
      {isOpen && (
        <div
          className={cn(
            'absolute left-0 right-0 top-full z-50 mt-1',
            'overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg',
          )}
        >
          {results.length === 0 && !isLoading ? (
            <div className="px-4 py-3 text-center text-sm text-gray-500">
              No buildings found
            </div>
          ) : (
            <ul
              ref={listRef}
              id="building-selector-results"
              role="listbox"
              className="max-h-[300px] overflow-y-auto"
              aria-label="Building search results"
            >
              {results.map((building, index) => (
                <li
                  key={building.id}
                  data-result-item
                  role="option"
                  aria-selected={highlightedIndex === index}
                  className={cn(
                    'cursor-pointer border-b border-gray-100 px-4 py-2.5 last:border-b-0',
                    'transition-colors',
                    highlightedIndex === index
                      ? 'bg-blue-50'
                      : 'hover:bg-gray-50',
                  )}
                  onClick={() => selectBuilding(building)}
                  onMouseEnter={() => setHighlightedIndex(index)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      {/* Building Name */}
                      <div className="truncate text-sm font-semibold text-gray-900">
                        {building.name}
                      </div>

                      {/* Address */}
                      <div className="mt-0.5 truncate text-xs text-gray-500">
                        {building.full_address}
                      </div>
                    </div>

                    <div className="flex shrink-0 items-center gap-1.5">
                      {/* Building Type Badge */}
                      <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                        {buildingTypeLabels[building.building_type] ??
                          building.building_type}
                      </span>

                      {/* Hazard Level Dot */}
                      <span
                        className={cn(
                          'inline-block h-2.5 w-2.5 shrink-0 rounded-full',
                          hazardDotColor[building.hazard_level] ?? 'bg-gray-400',
                        )}
                        title={`Hazard: ${building.hazard_level}`}
                        aria-label={`Hazard level: ${building.hazard_level}`}
                      />
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export default BuildingSelector;
