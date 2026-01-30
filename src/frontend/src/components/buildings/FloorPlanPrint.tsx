/**
 * FloorPlanPrint Component
 *
 * Print-optimized floor plan view with:
 * - Header with building info and print date
 * - Floor plan image with all markers
 * - Legend showing marker types
 * - Marker list with details
 * - Footer with branding
 * - Print button (hidden when printing)
 */

import { useMemo } from 'react';
import { cn } from '../../utils';
import { toAbsoluteApiUrl } from '../../services/api';
import type { Building, FloorPlan, FloorKeyLocation, LocationMarkerCategory } from '../../types';
import { MARKER_TYPE_CATEGORIES, getMarkerConfig } from '../../types';
import { MARKER_TYPES, type MarkerType } from './LocationMarker';

// --- Props ---

export interface FloorPlanPrintProps {
  building: Building;
  floorPlan: FloorPlan;
  markers: FloorKeyLocation[];
  className?: string;
}

// --- Category labels for display ---

const CATEGORY_LABELS: Record<LocationMarkerCategory, string> = {
  fire_equipment: 'Fire Equipment',
  access: 'Access Points',
  utilities: 'Utilities',
  hazards: 'Hazards',
  medical: 'Medical',
};

// --- Helper to format date/time ---

function formatDateTime(date: Date): string {
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// --- Helper to get marker icon and color ---

function getMarkerDisplay(type: string): { icon: string; color: string; label: string } {
  // Try DEFAULT_MARKER_CONFIGS first
  const config = getMarkerConfig(type);
  if (config) {
    return { icon: config.icon, color: config.color, label: config.label };
  }

  // Fall back to MARKER_TYPES from LocationMarker
  const markerConfig = MARKER_TYPES[type as MarkerType];
  if (markerConfig) {
    return { icon: markerConfig.icon, color: markerConfig.color, label: markerConfig.label };
  }

  // Default for custom/unknown types
  return { icon: '\u{1F4CD}', color: 'bg-gray-500', label: type };
}

// --- Component ---

export function FloorPlanPrint({
  building,
  floorPlan,
  markers,
  className,
}: FloorPlanPrintProps) {
  // Get unique marker types used on this floor
  const usedMarkerTypes = useMemo(() => {
    const types = new Set<string>();
    markers.forEach((marker) => {
      types.add(marker.type);
    });
    return Array.from(types);
  }, [markers]);

  // Group markers by category
  const markersByCategory = useMemo(() => {
    const grouped: Record<string, FloorKeyLocation[]> = {};

    markers.forEach((marker) => {
      const category = MARKER_TYPE_CATEGORIES[marker.type as keyof typeof MARKER_TYPE_CATEGORIES] || 'access';
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(marker);
    });

    return grouped;
  }, [markers]);

  // Sort markers for the list
  const sortedMarkers = useMemo(() => {
    return [...markers].sort((a, b) => {
      const catA = MARKER_TYPE_CATEGORIES[a.type as keyof typeof MARKER_TYPE_CATEGORIES] || 'access';
      const catB = MARKER_TYPE_CATEGORIES[b.type as keyof typeof MARKER_TYPE_CATEGORIES] || 'access';
      if (catA !== catB) {
        return catA.localeCompare(catB);
      }
      return a.name.localeCompare(b.name);
    });
  }, [markers]);

  // Handle print
  const handlePrint = () => {
    window.print();
  };

  // Floor display name
  const floorDisplayName = floorPlan.floor_name
    ? `Floor ${floorPlan.floor_number}: ${floorPlan.floor_name}`
    : `Floor ${floorPlan.floor_number}`;

  return (
    <div className={cn('bg-white min-h-screen', className)}>
      {/* Print Button - Hidden when printing */}
      <div className="print:hidden fixed bottom-6 right-6 z-50">
        <button
          onClick={handlePrint}
          className={cn(
            'flex items-center gap-2 px-6 py-3',
            'bg-blue-600 text-white rounded-lg shadow-lg',
            'hover:bg-blue-700 transition-colors',
            'font-medium text-base'
          )}
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
            />
          </svg>
          Print Floor Plan
        </button>
      </div>

      {/* Main Content */}
      <div className="max-w-[11in] mx-auto p-8 print:p-4 print:max-w-none">
        {/* Header Section */}
        <header className="border-b-2 border-gray-800 pb-4 mb-6 print:mb-4">
          <div className="flex justify-between items-start">
            <div className="flex-1">
              {/* Building Name */}
              <h1 className="text-3xl font-bold text-gray-900 print:text-2xl">
                {building.name}
              </h1>

              {/* Building Address */}
              <p className="text-lg text-gray-700 mt-1 print:text-base">
                {building.full_address}
              </p>

              {/* Floor Information */}
              <p className="text-xl font-semibold text-gray-800 mt-2 print:text-lg">
                {floorDisplayName}
              </p>
            </div>

            {/* Right side - Logo placeholder and print date */}
            <div className="text-right">
              {/* Agency Logo Placeholder */}
              <div className="w-24 h-24 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center text-gray-400 text-xs mb-2 print:w-20 print:h-20">
                Agency Logo
              </div>

              {/* Print Date/Time */}
              <p className="text-sm text-gray-600">
                Printed: {formatDateTime(new Date())}
              </p>
            </div>
          </div>

          {/* Additional Building Info */}
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm print:grid-cols-4">
            <div>
              <span className="font-medium text-gray-700">Building Type:</span>{' '}
              <span className="text-gray-900 capitalize">
                {building.building_type.replace(/_/g, ' ')}
              </span>
            </div>
            <div>
              <span className="font-medium text-gray-700">Total Floors:</span>{' '}
              <span className="text-gray-900">{building.total_floors}</span>
            </div>
            <div>
              <span className="font-medium text-gray-700">Hazard Level:</span>{' '}
              <span
                className={cn(
                  'capitalize font-medium',
                  building.hazard_level === 'extreme' && 'text-red-600',
                  building.hazard_level === 'high' && 'text-orange-600',
                  building.hazard_level === 'moderate' && 'text-yellow-600',
                  building.hazard_level === 'low' && 'text-green-600'
                )}
              >
                {building.hazard_level}
              </span>
            </div>
            <div>
              <span className="font-medium text-gray-700">Knox Box:</span>{' '}
              <span className="text-gray-900">
                {building.knox_box ? 'Yes' : 'No'}
              </span>
            </div>
          </div>
        </header>

        {/* Floor Plan Image Section */}
        <section className="mb-6 print:mb-4 print:break-inside-avoid">
          <h2 className="text-xl font-bold text-gray-800 mb-3 print:text-lg">
            Floor Plan
          </h2>

          <div className="relative border-2 border-gray-400 rounded-lg overflow-hidden bg-gray-100">
            {/* Floor Plan Image */}
            {floorPlan.plan_file_url ? (
              <div className="relative">
                <img
                  src={toAbsoluteApiUrl(floorPlan.plan_file_url)}
                  alt={`Floor plan for ${floorDisplayName}`}
                  className="w-full h-auto max-h-[60vh] object-contain print:max-h-[7in]"
                />

                {/* Markers Overlay */}
                <div className="absolute inset-0">
                  {markers.map((marker, index) => {
                    if (marker.x === undefined || marker.y === undefined) {
                      return null;
                    }
                    const display = getMarkerDisplay(marker.type);
                    return (
                      <div
                        key={marker.id || index}
                        className="absolute transform -translate-x-1/2 -translate-y-1/2"
                        style={{
                          left: `${marker.x}%`,
                          top: `${marker.y}%`,
                        }}
                      >
                        <div
                          className={cn(
                            'w-6 h-6 rounded-full flex items-center justify-center',
                            'text-white text-xs border-2 border-white shadow-md',
                            'print:w-5 print:h-5 print:text-[10px]',
                            display.color
                          )}
                          title={marker.name}
                        >
                          {display.icon}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-500">
                No floor plan image available
              </div>
            )}

            {/* Scale and North Arrow (optional indicators) */}
            <div className="absolute bottom-2 left-2 flex items-center gap-4 bg-white/90 px-2 py-1 rounded text-xs text-gray-600">
              {floorPlan.floor_area_sqm && (
                <span>Area: {floorPlan.floor_area_sqm.toLocaleString()} sqm</span>
              )}
              {floorPlan.ceiling_height_m && (
                <span>Ceiling: {floorPlan.ceiling_height_m}m</span>
              )}
            </div>

            {/* North Arrow */}
            <div className="absolute top-2 right-2 bg-white/90 p-1 rounded">
              <div className="flex flex-col items-center text-gray-700">
                <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2l4 8h-3v12h-2V10H8l4-8z" />
                </svg>
                <span className="text-[10px] font-bold">N</span>
              </div>
            </div>
          </div>
        </section>

        {/* Legend Section */}
        {usedMarkerTypes.length > 0 && (
          <section className="mb-6 print:mb-4 print:break-inside-avoid">
            <h2 className="text-xl font-bold text-gray-800 mb-3 print:text-lg">
              Legend
            </h2>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 print:grid-cols-5">
              {Object.entries(markersByCategory).map(([category, categoryMarkers]) => {
                const categoryTypes = new Set(categoryMarkers.map((m) => m.type));
                return (
                  <div
                    key={category}
                    className="border border-gray-300 rounded-lg p-3 print:p-2"
                  >
                    <h3 className="font-semibold text-sm text-gray-700 mb-2 border-b pb-1">
                      {CATEGORY_LABELS[category as LocationMarkerCategory] || category}
                    </h3>
                    <div className="space-y-1.5">
                      {Array.from(categoryTypes).map((type) => {
                        const display = getMarkerDisplay(type);
                        return (
                          <div key={type} className="flex items-center gap-2">
                            <div
                              className={cn(
                                'w-5 h-5 rounded-full flex items-center justify-center',
                                'text-white text-[10px] border border-white shadow-sm',
                                display.color
                              )}
                            >
                              {display.icon}
                            </div>
                            <span className="text-xs text-gray-700">
                              {display.label}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Marker List Section */}
        {sortedMarkers.length > 0 && (
          <section className="mb-6 print:mb-4">
            <h2 className="text-xl font-bold text-gray-800 mb-3 print:text-lg">
              Marker Details
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="border border-gray-300 px-3 py-2 text-left font-semibold text-gray-700 w-12">
                      Icon
                    </th>
                    <th className="border border-gray-300 px-3 py-2 text-left font-semibold text-gray-700">
                      Name
                    </th>
                    <th className="border border-gray-300 px-3 py-2 text-left font-semibold text-gray-700 w-40">
                      Type
                    </th>
                    <th className="border border-gray-300 px-3 py-2 text-left font-semibold text-gray-700">
                      Description / Notes
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sortedMarkers.map((marker, index) => {
                    const display = getMarkerDisplay(marker.type);
                    const notes = [marker.description, marker.notes]
                      .filter(Boolean)
                      .join(' | ');

                    return (
                      <tr
                        key={marker.id || index}
                        className={cn(index % 2 === 0 ? 'bg-white' : 'bg-gray-50')}
                      >
                        <td className="border border-gray-300 px-3 py-2 text-center">
                          <div
                            className={cn(
                              'w-6 h-6 rounded-full flex items-center justify-center mx-auto',
                              'text-white text-xs border border-white shadow-sm',
                              display.color
                            )}
                          >
                            {display.icon}
                          </div>
                        </td>
                        <td className="border border-gray-300 px-3 py-2 font-medium text-gray-900">
                          {marker.name}
                        </td>
                        <td className="border border-gray-300 px-3 py-2 text-gray-700">
                          {display.label}
                        </td>
                        <td className="border border-gray-300 px-3 py-2 text-gray-600">
                          {notes || '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <p className="text-xs text-gray-500 mt-2">
              Total markers: {sortedMarkers.length}
            </p>
          </section>
        )}

        {/* Footer */}
        <footer className="border-t-2 border-gray-300 pt-4 mt-8 print:mt-4 print:pt-2">
          <div className="flex justify-between items-center text-sm text-gray-600">
            <p>
              Printed from{' '}
              <span className="font-semibold text-gray-800">
                Vigilia Emergency Response Platform
              </span>
            </p>
            <p className="text-xs text-gray-500">
              CONFIDENTIAL - For Emergency Response Personnel Only
            </p>
          </div>
        </footer>
      </div>

      {/* Print-specific styles */}
      <style>
        {`
          @media print {
            body {
              -webkit-print-color-adjust: exact !important;
              print-color-adjust: exact !important;
            }

            @page {
              margin: 0.5in;
              size: auto;
            }

            .print\\:hidden {
              display: none !important;
            }

            /* Force background colors to print */
            * {
              -webkit-print-color-adjust: exact !important;
              print-color-adjust: exact !important;
            }

            /* Remove shadows for cleaner print */
            .shadow-md,
            .shadow-lg {
              box-shadow: none !important;
            }

            /* Ensure proper page breaks */
            section {
              page-break-inside: avoid;
            }

            /* Table page breaks */
            tr {
              page-break-inside: avoid;
            }

            /* Header on each page */
            header {
              page-break-after: avoid;
            }
          }
        `}
      </style>
    </div>
  );
}

export default FloorPlanPrint;
