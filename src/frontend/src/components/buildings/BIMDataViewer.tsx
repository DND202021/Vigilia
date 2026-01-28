/**
 * BIMDataViewer Component
 * Displays imported BIM (Building Information Modeling) metadata for a building.
 * Shows building properties, floors, materials, and key locations extracted from BIM files.
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, Badge } from '../ui';
import { cn, formatDate } from '../../utils';
import type { Building } from '../../types';

/**
 * BIM data structure expected from the parser.
 * This represents the JSON structure stored in the building's bim_data field.
 */
export interface BIMData {
  // Import metadata
  import_date?: string;
  source_file_name?: string;
  format_version?: string;
  ifc_schema?: string;

  // Building properties from BIM
  building_name?: string;
  construction_type?: string;
  construction_year?: number;
  total_gross_area_sqm?: number;
  number_of_floors?: number;
  building_height_m?: number;

  // Floors summary
  floors?: BIMFloor[];

  // Materials
  materials?: BIMMaterial[];

  // Key locations extracted
  key_locations?: BIMKeyLocations;

  // Additional metadata
  project_name?: string;
  author?: string;
  organization?: string;
  application?: string;
}

export interface BIMFloor {
  name: string;
  level?: number;
  elevation_m?: number;
  area_sqm?: number;
}

export interface BIMMaterial {
  name: string;
  category?: string;
  quantity?: number;
  unit?: string;
}

export interface BIMKeyLocations {
  doors?: number;
  stairs?: number;
  elevators?: number;
  windows?: number;
  fire_exits?: number;
  fire_equipment?: number;
  utilities?: number;
}

interface BIMDataViewerProps {
  building: Building;
  className?: string;
}

/**
 * Collapsible section component for organizing BIM data
 */
function CollapsibleSection({
  title,
  icon,
  children,
  defaultOpen = true,
  badge,
}: {
  title: string;
  icon: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  badge?: React.ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-gray-100 last:border-b-0">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between py-3 px-1 text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">{icon}</span>
          <span className="text-sm font-medium text-gray-700">{title}</span>
          {badge}
        </div>
        <svg
          className={cn(
            'w-4 h-4 text-gray-400 transition-transform',
            isOpen && 'transform rotate-180'
          )}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && <div className="pb-3 px-1">{children}</div>}
    </div>
  );
}

/**
 * Info row component for displaying key-value pairs
 */
function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  if (value === null || value === undefined || value === '') return null;

  return (
    <div className="flex justify-between py-1">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-medium text-gray-900">{value}</span>
    </div>
  );
}

export function BIMDataViewer({ building, className }: BIMDataViewerProps) {
  // Parse bim_data if it exists - it's stored as a JSON field on the building
  // The building type doesn't directly have bim_data, but the API stores it
  // We access it via a type assertion since it's a dynamic JSON field
  const bimData = (building as Building & { bim_data?: BIMData }).bim_data;
  const hasBIMData = building.has_bim_data && bimData;

  // Calculate key locations total
  const keyLocationsTotal = bimData?.key_locations
    ? Object.values(bimData.key_locations).reduce((sum, count) => sum + (count || 0), 0)
    : 0;

  return (
    <Card className={cn('', className)}>
      {/* Header */}
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-2">
          <svg
            className="w-5 h-5 text-blue-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
            />
          </svg>
          <CardTitle>BIM Data</CardTitle>
        </div>
        <Badge variant={hasBIMData ? 'success' : 'secondary'}>
          {hasBIMData ? 'Imported' : 'Not Imported'}
        </Badge>
      </CardHeader>

      <CardContent className="pt-0">
        {hasBIMData && bimData ? (
          <div className="space-y-1">
            {/* Import Information */}
            <CollapsibleSection title="Import Information" icon="&#128196;" defaultOpen={true}>
              <div className="bg-gray-50 rounded-lg p-3 space-y-1">
                {bimData.import_date && (
                  <InfoRow label="Import Date" value={formatDate(bimData.import_date)} />
                )}
                {bimData.source_file_name && (
                  <InfoRow label="Source File" value={bimData.source_file_name} />
                )}
                {bimData.format_version && (
                  <InfoRow label="Format Version" value={bimData.format_version} />
                )}
                {bimData.ifc_schema && (
                  <InfoRow label="IFC Schema" value={bimData.ifc_schema} />
                )}
                {bimData.application && (
                  <InfoRow label="Application" value={bimData.application} />
                )}
                {bimData.author && (
                  <InfoRow label="Author" value={bimData.author} />
                )}
                {bimData.organization && (
                  <InfoRow label="Organization" value={bimData.organization} />
                )}
              </div>
            </CollapsibleSection>

            {/* Building Properties from BIM */}
            <CollapsibleSection title="Building Properties" icon="&#127970;" defaultOpen={true}>
              <div className="bg-gray-50 rounded-lg p-3 space-y-1">
                {bimData.building_name && (
                  <InfoRow label="Building Name (BIM)" value={bimData.building_name} />
                )}
                {bimData.construction_type && (
                  <InfoRow label="Construction Type" value={bimData.construction_type} />
                )}
                {bimData.construction_year && (
                  <InfoRow label="Construction Year" value={bimData.construction_year} />
                )}
                {bimData.total_gross_area_sqm && (
                  <InfoRow
                    label="Total Gross Area"
                    value={`${bimData.total_gross_area_sqm.toLocaleString()} m²`}
                  />
                )}
                {bimData.number_of_floors && (
                  <InfoRow label="Number of Floors" value={bimData.number_of_floors} />
                )}
                {bimData.building_height_m && (
                  <InfoRow label="Building Height" value={`${bimData.building_height_m} m`} />
                )}
                {bimData.project_name && (
                  <InfoRow label="Project Name" value={bimData.project_name} />
                )}
              </div>
            </CollapsibleSection>

            {/* Floors Summary */}
            {bimData.floors && bimData.floors.length > 0 && (
              <CollapsibleSection
                title="Floors Summary"
                icon="&#128481;"
                defaultOpen={false}
                badge={
                  <Badge variant="info" size="sm">
                    {bimData.floors.length}
                  </Badge>
                }
              >
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 uppercase">
                          Floor
                        </th>
                        <th className="text-right py-2 px-2 text-xs font-medium text-gray-500 uppercase">
                          Level
                        </th>
                        <th className="text-right py-2 px-2 text-xs font-medium text-gray-500 uppercase">
                          Elevation
                        </th>
                        <th className="text-right py-2 px-2 text-xs font-medium text-gray-500 uppercase">
                          Area
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {bimData.floors.map((floor, index) => (
                        <tr key={index} className="border-b border-gray-100 last:border-b-0">
                          <td className="py-2 px-2 font-medium text-gray-900">{floor.name}</td>
                          <td className="py-2 px-2 text-right text-gray-600">
                            {floor.level !== undefined ? floor.level : '-'}
                          </td>
                          <td className="py-2 px-2 text-right text-gray-600">
                            {floor.elevation_m !== undefined ? `${floor.elevation_m} m` : '-'}
                          </td>
                          <td className="py-2 px-2 text-right text-gray-600">
                            {floor.area_sqm ? `${floor.area_sqm.toLocaleString()} m²` : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CollapsibleSection>
            )}

            {/* Materials */}
            {bimData.materials && bimData.materials.length > 0 && (
              <CollapsibleSection
                title="Materials"
                icon="&#129521;"
                defaultOpen={false}
                badge={
                  <Badge variant="secondary" size="sm">
                    {bimData.materials.length}
                  </Badge>
                }
              >
                <div className="space-y-2">
                  {bimData.materials.map((material, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between bg-gray-50 rounded px-3 py-2"
                    >
                      <div>
                        <span className="text-sm font-medium text-gray-900">{material.name}</span>
                        {material.category && (
                          <span className="text-xs text-gray-500 ml-2">({material.category})</span>
                        )}
                      </div>
                      {material.quantity !== undefined && (
                        <span className="text-sm text-gray-600">
                          {material.quantity.toLocaleString()} {material.unit || 'units'}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </CollapsibleSection>
            )}

            {/* Key Locations Found */}
            {bimData.key_locations && keyLocationsTotal > 0 && (
              <CollapsibleSection
                title="Key Locations Found"
                icon="&#128205;"
                defaultOpen={false}
                badge={
                  <Badge variant="info" size="sm">
                    {keyLocationsTotal}
                  </Badge>
                }
              >
                <div className="grid grid-cols-2 gap-2">
                  {bimData.key_locations.doors !== undefined && bimData.key_locations.doors > 0 && (
                    <div className="flex items-center gap-2 bg-gray-50 rounded px-3 py-2">
                      <span className="text-lg">&#128682;</span>
                      <div>
                        <p className="text-xs text-gray-500">Doors</p>
                        <p className="text-sm font-semibold">{bimData.key_locations.doors}</p>
                      </div>
                    </div>
                  )}
                  {bimData.key_locations.stairs !== undefined && bimData.key_locations.stairs > 0 && (
                    <div className="flex items-center gap-2 bg-gray-50 rounded px-3 py-2">
                      <span className="text-lg">&#128694;</span>
                      <div>
                        <p className="text-xs text-gray-500">Stairs</p>
                        <p className="text-sm font-semibold">{bimData.key_locations.stairs}</p>
                      </div>
                    </div>
                  )}
                  {bimData.key_locations.elevators !== undefined && bimData.key_locations.elevators > 0 && (
                    <div className="flex items-center gap-2 bg-gray-50 rounded px-3 py-2">
                      <span className="text-lg">&#128727;</span>
                      <div>
                        <p className="text-xs text-gray-500">Elevators</p>
                        <p className="text-sm font-semibold">{bimData.key_locations.elevators}</p>
                      </div>
                    </div>
                  )}
                  {bimData.key_locations.windows !== undefined && bimData.key_locations.windows > 0 && (
                    <div className="flex items-center gap-2 bg-gray-50 rounded px-3 py-2">
                      <span className="text-lg">&#128423;</span>
                      <div>
                        <p className="text-xs text-gray-500">Windows</p>
                        <p className="text-sm font-semibold">{bimData.key_locations.windows}</p>
                      </div>
                    </div>
                  )}
                  {bimData.key_locations.fire_exits !== undefined && bimData.key_locations.fire_exits > 0 && (
                    <div className="flex items-center gap-2 bg-green-50 rounded px-3 py-2">
                      <span className="text-lg">&#128682;</span>
                      <div>
                        <p className="text-xs text-green-600">Fire Exits</p>
                        <p className="text-sm font-semibold text-green-700">
                          {bimData.key_locations.fire_exits}
                        </p>
                      </div>
                    </div>
                  )}
                  {bimData.key_locations.fire_equipment !== undefined && bimData.key_locations.fire_equipment > 0 && (
                    <div className="flex items-center gap-2 bg-red-50 rounded px-3 py-2">
                      <span className="text-lg">&#129519;</span>
                      <div>
                        <p className="text-xs text-red-600">Fire Equipment</p>
                        <p className="text-sm font-semibold text-red-700">
                          {bimData.key_locations.fire_equipment}
                        </p>
                      </div>
                    </div>
                  )}
                  {bimData.key_locations.utilities !== undefined && bimData.key_locations.utilities > 0 && (
                    <div className="flex items-center gap-2 bg-yellow-50 rounded px-3 py-2">
                      <span className="text-lg">&#9889;</span>
                      <div>
                        <p className="text-xs text-yellow-600">Utilities</p>
                        <p className="text-sm font-semibold text-yellow-700">
                          {bimData.key_locations.utilities}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </CollapsibleSection>
            )}

            {/* BIM File Link */}
            {building.bim_file_url && (
              <div className="pt-3 border-t border-gray-100">
                <a
                  href={building.bim_file_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 transition-colors"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                    />
                  </svg>
                  Download Original BIM File
                </a>
              </div>
            )}
          </div>
        ) : (
          /* Empty State */
          <div className="text-center py-8">
            <svg
              className="w-16 h-16 mx-auto text-gray-300 mb-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
              />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No BIM Data Imported</h3>
            <p className="text-sm text-gray-500 mb-4">
              Import a BIM file (IFC, RVT) to view detailed building information,
              <br />
              floor layouts, materials, and key locations.
            </p>
            <div className="inline-flex items-center gap-2 text-sm text-blue-600 bg-blue-50 px-4 py-2 rounded-lg">
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              Import BIM file to get started
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default BIMDataViewer;
