/**
 * BuildingLayer Component
 *
 * Renders building markers on a Leaflet map with optional clustering support.
 * Uses custom SVG building icons colored by hazard level.
 * Supports both react-leaflet <Marker> mode and leaflet.markercluster mode.
 */

import { useEffect, useMemo, useRef } from 'react';
import { Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
import { BuildingPopup } from './BuildingPopup';
import type { Building, HazardLevel } from '../../types';

export interface BuildingLayerProps {
  buildings: Building[];
  selectedBuildingId?: string | null;
  onBuildingSelect: (building: Building) => void;
  onViewDetails: (building: Building) => void;
  onViewFloorPlans: (building: Building) => void;
  enableClustering?: boolean;
}

// Hazard level to marker color mapping
const hazardColors: Record<HazardLevel, string> = {
  low: '#8b5cf6',
  moderate: '#eab308',
  high: '#f97316',
  extreme: '#ef4444',
};

/**
 * Creates an SVG building icon as a Leaflet DivIcon.
 */
function createBuildingIcon(
  color: string,
  size: number = 24,
  selected: boolean = false
): L.DivIcon {
  const ringMarkup = selected
    ? `<circle cx="12" cy="12" r="11" fill="none" stroke="#3b82f6" stroke-width="2.5" opacity="0.7"/>`
    : '';

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="${size}" height="${size}">
      ${ringMarkup}
      <path d="M3 21V7l9-4 9 4v14H3zm2-2h5v-4h4v4h5V8.3l-7-3.1L5 8.3V19z" fill="${color}"/>
    </svg>
  `;

  return L.divIcon({
    html: svg,
    className: 'building-marker',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

/**
 * Returns the appropriate icon for a building based on hazard level and selection state.
 */
function getBuildingIcon(building: Building, isSelected: boolean): L.DivIcon {
  const color = hazardColors[building.hazard_level] || hazardColors.low;
  if (isSelected) {
    return createBuildingIcon(color, 28, true);
  }
  return createBuildingIcon(color, 24, false);
}

/**
 * Filters buildings to only those with valid latitude and longitude values.
 */
function filterBuildingsWithCoords(buildings: Building[]): Building[] {
  return buildings.filter(
    (b) =>
      b.latitude != null &&
      b.longitude != null &&
      !isNaN(b.latitude) &&
      !isNaN(b.longitude)
  );
}

/**
 * Clustered building markers using leaflet.markercluster.
 * Manages the MarkerClusterGroup lifecycle via the Leaflet map instance directly.
 */
function ClusteredBuildingMarkers({
  buildings,
  selectedBuildingId,
  onBuildingSelect,
  onViewDetails,
  onViewFloorPlans,
}: Omit<BuildingLayerProps, 'enableClustering'>) {
  const map = useMap();
  const clusterGroupRef = useRef<L.MarkerClusterGroup | null>(null);

  const validBuildings = useMemo(
    () => filterBuildingsWithCoords(buildings),
    [buildings]
  );

  useEffect(() => {
    const clusterGroup = L.markerClusterGroup();
    clusterGroupRef.current = clusterGroup;

    validBuildings.forEach((building) => {
      const isSelected = building.id === selectedBuildingId;
      const icon = getBuildingIcon(building, isSelected);

      const marker = L.marker([building.latitude, building.longitude], {
        icon,
      });

      // Build popup HTML content
      const popupContainer = document.createElement('div');
      popupContainer.className = 'building-cluster-popup';

      // Header
      const header = document.createElement('div');
      header.className = 'min-w-[200px]';

      const name = document.createElement('p');
      name.className = 'font-semibold text-sm text-gray-900';
      name.textContent = building.name;
      header.appendChild(name);

      const address = document.createElement('p');
      address.className = 'text-xs text-gray-600 mt-0.5';
      address.textContent = building.full_address;
      header.appendChild(address);

      // Hazard badge
      const badgeRow = document.createElement('div');
      badgeRow.className = 'mt-2 flex gap-2 flex-wrap';

      const typeBadge = document.createElement('span');
      typeBadge.className =
        'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-700 capitalize';
      typeBadge.textContent = building.building_type.replace(/_/g, ' ');
      badgeRow.appendChild(typeBadge);

      const hazardBadge = document.createElement('span');
      const hazardBgMap: Record<string, string> = {
        low: 'bg-green-100 text-green-700',
        moderate: 'bg-yellow-100 text-yellow-700',
        high: 'bg-orange-100 text-orange-700',
        extreme: 'bg-red-100 text-red-700',
      };
      hazardBadge.className = `inline-flex items-center px-2 py-0.5 text-xs font-medium rounded ${hazardBgMap[building.hazard_level] || ''}`;
      hazardBadge.textContent =
        building.hazard_level.charAt(0).toUpperCase() +
        building.hazard_level.slice(1);
      badgeRow.appendChild(hazardBadge);
      header.appendChild(badgeRow);

      // Floor info
      const info = document.createElement('div');
      info.className = 'mt-2 text-xs text-gray-500';
      info.textContent = `${building.total_floors} floor${building.total_floors !== 1 ? 's' : ''}${building.has_hazmat ? ' | HAZMAT' : ''}`;
      header.appendChild(info);

      // Action buttons
      const actions = document.createElement('div');
      actions.className = 'mt-2 flex gap-2';

      const detailsBtn = document.createElement('button');
      detailsBtn.className =
        'flex-1 px-3 py-1.5 text-xs font-medium rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors';
      detailsBtn.textContent = 'View Details';
      detailsBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        onViewDetails(building);
      });
      actions.appendChild(detailsBtn);

      const floorBtn = document.createElement('button');
      floorBtn.className =
        'flex-1 px-3 py-1.5 text-xs font-medium rounded bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300 transition-colors';
      floorBtn.textContent = 'Floor Plans';
      floorBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        onViewFloorPlans(building);
      });
      actions.appendChild(floorBtn);

      header.appendChild(actions);
      popupContainer.appendChild(header);

      marker.bindPopup(popupContainer, { maxWidth: 320 });

      marker.on('click', () => {
        onBuildingSelect(building);
      });

      clusterGroup.addLayer(marker);
    });

    map.addLayer(clusterGroup);

    return () => {
      map.removeLayer(clusterGroup);
      clusterGroupRef.current = null;
    };
  }, [
    map,
    validBuildings,
    selectedBuildingId,
    onBuildingSelect,
    onViewDetails,
    onViewFloorPlans,
  ]);

  return null;
}

/**
 * Standard (non-clustered) building markers using react-leaflet components.
 */
function StandardBuildingMarkers({
  buildings,
  selectedBuildingId,
  onBuildingSelect,
  onViewDetails,
  onViewFloorPlans,
}: Omit<BuildingLayerProps, 'enableClustering'>) {
  const validBuildings = useMemo(
    () => filterBuildingsWithCoords(buildings),
    [buildings]
  );

  return (
    <>
      {validBuildings.map((building) => {
        const isSelected = building.id === selectedBuildingId;
        const icon = getBuildingIcon(building, isSelected);

        return (
          <Marker
            key={`building-${building.id}`}
            position={[building.latitude, building.longitude]}
            icon={icon}
            eventHandlers={{
              click: () => onBuildingSelect(building),
            }}
          >
            <Popup maxWidth={320}>
              <BuildingPopup
                building={building}
                onViewDetails={onViewDetails}
                onViewFloorPlans={onViewFloorPlans}
              />
            </Popup>
          </Marker>
        );
      })}
    </>
  );
}

/**
 * BuildingLayer renders building markers on a Leaflet map.
 *
 * When `enableClustering` is true, markers are grouped into clusters using
 * leaflet.markercluster for better performance with many buildings.
 * When false (default), standard react-leaflet Marker components are used.
 */
export function BuildingLayer({
  buildings,
  selectedBuildingId,
  onBuildingSelect,
  onViewDetails,
  onViewFloorPlans,
  enableClustering = false,
}: BuildingLayerProps) {
  if (enableClustering) {
    return (
      <ClusteredBuildingMarkers
        buildings={buildings}
        selectedBuildingId={selectedBuildingId}
        onBuildingSelect={onBuildingSelect}
        onViewDetails={onViewDetails}
        onViewFloorPlans={onViewFloorPlans}
      />
    );
  }

  return (
    <StandardBuildingMarkers
      buildings={buildings}
      selectedBuildingId={selectedBuildingId}
      onBuildingSelect={onBuildingSelect}
      onViewDetails={onViewDetails}
      onViewFloorPlans={onViewFloorPlans}
    />
  );
}

export default BuildingLayer;
