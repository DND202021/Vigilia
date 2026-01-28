/**
 * EvacuationRouteDrawer Component
 *
 * SVG-based route drawing tool that overlays on floor plans for creating
 * and editing evacuation routes. Supports multiple route types with distinct
 * visual styles, waypoint manipulation, and direction indicators.
 *
 * Features:
 * - Route display with polylines and waypoint markers
 * - Drawing mode: click to add waypoints, double-click/Enter to finish
 * - Editing mode: drag waypoints, add/remove points, color/width customization
 * - Visual styles per route type (primary, secondary, accessible, emergency_vehicle)
 * - Arrow markers for direction indication
 * - Smooth curve option using quadratic beziers
 */

import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import { cn } from '../../utils';
import type { EvacuationRoute, RouteWaypoint, RouteType } from '../../types';

// --- Types ---

export interface EvacuationRouteDrawerProps {
  floorPlanId: string;
  floorPlanUrl: string;
  containerWidth: number;
  containerHeight: number;
  routes: EvacuationRoute[];
  selectedRouteId?: string;
  onRouteSelect?: (routeId: string) => void;
  onRouteCreate?: (waypoints: RouteWaypoint[]) => void;
  onRouteUpdate?: (routeId: string, waypoints: RouteWaypoint[]) => void;
  onRouteDelete?: (routeId: string) => void;
  isEditing?: boolean;
  className?: string;
}

interface DrawingState {
  isDrawing: boolean;
  waypoints: RouteWaypoint[];
  cursorPosition: { x: number; y: number } | null;
}

interface EditingState {
  selectedWaypointIndex: number | null;
  isDragging: boolean;
  dragOffset: { x: number; y: number };
}

// --- Route Style Configurations ---

const ROUTE_TYPE_STYLES: Record<
  RouteType,
  {
    color: string;
    dashArray?: string;
    label: string;
    icon: string;
  }
> = {
  primary: {
    color: '#dc2626', // red-600
    label: 'Primary Route',
    icon: '1',
  },
  secondary: {
    color: '#2563eb', // blue-600
    dashArray: '8,4',
    label: 'Secondary Route',
    icon: '2',
  },
  accessible: {
    color: '#16a34a', // green-600
    label: 'Accessible Route',
    icon: '\u267F', // wheelchair symbol
  },
  emergency_vehicle: {
    color: '#ea580c', // orange-600
    label: 'Emergency Vehicle',
    icon: '\u{1F691}', // ambulance emoji
  },
};

const DEFAULT_LINE_WIDTH = 3;
const WAYPOINT_RADIUS = 6;
const WAYPOINT_HANDLE_RADIUS = 8;
const ARROW_SIZE = 10;

// --- Helper Functions ---

/**
 * Convert pixel coordinates to percentage (0-100) relative to container
 */
function pixelToPercent(
  px: number,
  py: number,
  containerWidth: number,
  containerHeight: number
): { x: number; y: number } {
  return {
    x: Math.max(0, Math.min(100, (px / containerWidth) * 100)),
    y: Math.max(0, Math.min(100, (py / containerHeight) * 100)),
  };
}

/**
 * Convert percentage coordinates to pixels
 */
function percentToPixel(
  x: number,
  y: number,
  containerWidth: number,
  containerHeight: number
): { px: number; py: number } {
  return {
    px: (x / 100) * containerWidth,
    py: (y / 100) * containerHeight,
  };
}

/**
 * Generate SVG path data for a route with optional smooth curves
 */
function generatePathData(
  waypoints: RouteWaypoint[],
  containerWidth: number,
  containerHeight: number,
  smooth: boolean = false
): string {
  if (waypoints.length < 2) return '';

  const points = waypoints
    .sort((a, b) => a.order - b.order)
    .map((wp) => percentToPixel(wp.x, wp.y, containerWidth, containerHeight));

  if (!smooth || points.length < 3) {
    // Simple polyline
    return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.px} ${p.py}`).join(' ');
  }

  // Quadratic bezier smoothing
  let path = `M ${points[0].px} ${points[0].py}`;

  for (let i = 1; i < points.length - 1; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const next = points[i + 1];

    // Control point is the current point
    // End point is midway between current and next
    const midX = (curr.px + next.px) / 2;
    const midY = (curr.py + next.py) / 2;

    if (i === 1) {
      // First segment: line to midpoint before first curve
      const firstMidX = (prev.px + curr.px) / 2;
      const firstMidY = (prev.py + curr.py) / 2;
      path += ` L ${firstMidX} ${firstMidY}`;
    }

    path += ` Q ${curr.px} ${curr.py} ${midX} ${midY}`;
  }

  // Final segment to last point
  const last = points[points.length - 1];
  path += ` L ${last.px} ${last.py}`;

  return path;
}

/**
 * Calculate angle between two points for arrow rotation
 */
function calculateAngle(
  x1: number,
  y1: number,
  x2: number,
  y2: number
): number {
  return Math.atan2(y2 - y1, x2 - x1) * (180 / Math.PI);
}

// --- Component ---

export function EvacuationRouteDrawer({
  floorPlanId,
  floorPlanUrl,
  containerWidth,
  containerHeight,
  routes,
  selectedRouteId,
  onRouteSelect,
  onRouteCreate,
  onRouteUpdate,
  onRouteDelete,
  isEditing = false,
  className,
}: EvacuationRouteDrawerProps) {
  // Refs
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Drawing state (for creating new routes)
  const [drawingState, setDrawingState] = useState<DrawingState>({
    isDrawing: false,
    waypoints: [],
    cursorPosition: null,
  });

  // Editing state (for modifying existing routes)
  const [editingState, setEditingState] = useState<EditingState>({
    selectedWaypointIndex: null,
    isDragging: false,
    dragOffset: { x: 0, y: 0 },
  });

  // Toolbar state
  const [selectedRouteType, setSelectedRouteType] = useState<RouteType>('primary');
  const [selectedColor, setSelectedColor] = useState('#dc2626');
  const [lineWidth, setLineWidth] = useState(DEFAULT_LINE_WIDTH);
  const [useSmoothCurves, setUseSmoothCurves] = useState(false);

  // Selected route data
  const selectedRoute = useMemo(
    () => routes.find((r) => r.id === selectedRouteId),
    [routes, selectedRouteId]
  );

  // Update color when route type changes
  useEffect(() => {
    setSelectedColor(ROUTE_TYPE_STYLES[selectedRouteType].color);
  }, [selectedRouteType]);

  // --- Event Handlers ---

  /**
   * Get mouse position relative to SVG container
   */
  const getMousePosition = useCallback(
    (e: React.MouseEvent): { x: number; y: number } | null => {
      if (!svgRef.current) return null;

      const rect = svgRef.current.getBoundingClientRect();
      const px = e.clientX - rect.left;
      const py = e.clientY - rect.top;

      return pixelToPercent(px, py, containerWidth, containerHeight);
    },
    [containerWidth, containerHeight]
  );

  /**
   * Handle click on SVG canvas
   */
  const handleCanvasClick = useCallback(
    (e: React.MouseEvent) => {
      if (!isEditing) return;

      const pos = getMousePosition(e);
      if (!pos) return;

      // If in drawing mode, add waypoint
      if (drawingState.isDrawing) {
        const newWaypoint: RouteWaypoint = {
          order: drawingState.waypoints.length,
          x: pos.x,
          y: pos.y,
          floor_plan_id: floorPlanId,
        };

        setDrawingState((prev) => ({
          ...prev,
          waypoints: [...prev.waypoints, newWaypoint],
        }));
        return;
      }

      // If not drawing and no route selected, deselect waypoint
      if (selectedRoute && editingState.selectedWaypointIndex !== null) {
        setEditingState((prev) => ({
          ...prev,
          selectedWaypointIndex: null,
        }));
      }
    },
    [
      isEditing,
      getMousePosition,
      drawingState.isDrawing,
      drawingState.waypoints.length,
      floorPlanId,
      selectedRoute,
      editingState.selectedWaypointIndex,
    ]
  );

  /**
   * Handle double-click to finish drawing or add waypoint on line
   */
  const handleCanvasDoubleClick = useCallback(
    (_e: React.MouseEvent) => {
      if (!isEditing) return;

      if (drawingState.isDrawing && drawingState.waypoints.length >= 2) {
        // Finish drawing
        onRouteCreate?.(drawingState.waypoints);
        setDrawingState({
          isDrawing: false,
          waypoints: [],
          cursorPosition: null,
        });
      }
    },
    [isEditing, drawingState, onRouteCreate]
  );

  /**
   * Handle mouse move for preview line and dragging
   */
  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const pos = getMousePosition(e);
      if (!pos) return;

      // Update cursor position for preview line
      if (drawingState.isDrawing) {
        setDrawingState((prev) => ({
          ...prev,
          cursorPosition: pos,
        }));
      }

      // Handle waypoint dragging
      if (
        editingState.isDragging &&
        editingState.selectedWaypointIndex !== null &&
        selectedRoute
      ) {
        const updatedWaypoints = selectedRoute.waypoints.map((wp, i) =>
          i === editingState.selectedWaypointIndex
            ? { ...wp, x: pos.x, y: pos.y }
            : wp
        );
        onRouteUpdate?.(selectedRoute.id, updatedWaypoints);
      }
    },
    [
      getMousePosition,
      drawingState.isDrawing,
      editingState.isDragging,
      editingState.selectedWaypointIndex,
      selectedRoute,
      onRouteUpdate,
    ]
  );

  /**
   * Handle mouse up to end dragging
   */
  const handleMouseUp = useCallback(() => {
    if (editingState.isDragging) {
      setEditingState((prev) => ({
        ...prev,
        isDragging: false,
      }));
    }
  }, [editingState.isDragging]);

  /**
   * Handle waypoint click (select) or drag start
   */
  const handleWaypointMouseDown = useCallback(
    (e: React.MouseEvent, index: number) => {
      e.stopPropagation();

      if (!isEditing || !selectedRoute) return;

      setEditingState({
        selectedWaypointIndex: index,
        isDragging: true,
        dragOffset: { x: 0, y: 0 },
      });
    },
    [isEditing, selectedRoute]
  );

  /**
   * Handle route path click (select route)
   */
  const handleRouteClick = useCallback(
    (e: React.MouseEvent, routeId: string) => {
      e.stopPropagation();
      onRouteSelect?.(routeId);
    },
    [onRouteSelect]
  );

  /**
   * Handle line segment click to add waypoint
   */
  const handleLineClick = useCallback(
    (e: React.MouseEvent, segmentIndex: number) => {
      e.stopPropagation();

      if (!isEditing || !selectedRoute) return;

      const pos = getMousePosition(e);
      if (!pos) return;

      // Insert new waypoint between segmentIndex and segmentIndex + 1
      const newWaypoints = [...selectedRoute.waypoints];
      const newWaypoint: RouteWaypoint = {
        order: segmentIndex + 1,
        x: pos.x,
        y: pos.y,
        floor_plan_id: floorPlanId,
      };

      // Insert and reorder
      newWaypoints.splice(segmentIndex + 1, 0, newWaypoint);
      const reordered = newWaypoints.map((wp, i) => ({ ...wp, order: i }));

      onRouteUpdate?.(selectedRoute.id, reordered);
    },
    [isEditing, selectedRoute, getMousePosition, floorPlanId, onRouteUpdate]
  );

  /**
   * Handle keyboard events
   */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isEditing) return;

      // Enter to finish drawing
      if (e.key === 'Enter' && drawingState.isDrawing && drawingState.waypoints.length >= 2) {
        onRouteCreate?.(drawingState.waypoints);
        setDrawingState({
          isDrawing: false,
          waypoints: [],
          cursorPosition: null,
        });
        return;
      }

      // Escape to cancel drawing or deselect
      if (e.key === 'Escape') {
        if (drawingState.isDrawing) {
          setDrawingState({
            isDrawing: false,
            waypoints: [],
            cursorPosition: null,
          });
        } else {
          setEditingState({
            selectedWaypointIndex: null,
            isDragging: false,
            dragOffset: { x: 0, y: 0 },
          });
        }
        return;
      }

      // Delete selected waypoint
      if (
        (e.key === 'Delete' || e.key === 'Backspace') &&
        editingState.selectedWaypointIndex !== null &&
        selectedRoute
      ) {
        e.preventDefault();

        if (selectedRoute.waypoints.length <= 2) {
          // Can't have less than 2 waypoints
          return;
        }

        const updatedWaypoints = selectedRoute.waypoints
          .filter((_, i) => i !== editingState.selectedWaypointIndex)
          .map((wp, i) => ({ ...wp, order: i }));

        onRouteUpdate?.(selectedRoute.id, updatedWaypoints);
        setEditingState((prev) => ({
          ...prev,
          selectedWaypointIndex: null,
        }));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    isEditing,
    drawingState,
    editingState.selectedWaypointIndex,
    selectedRoute,
    onRouteCreate,
    onRouteUpdate,
  ]);

  // --- Toolbar Actions ---

  const handleStartDrawing = useCallback(() => {
    setDrawingState({
      isDrawing: true,
      waypoints: [],
      cursorPosition: null,
    });
    // Deselect any selected route
    if (selectedRouteId) {
      onRouteSelect?.('');
    }
  }, [selectedRouteId, onRouteSelect]);

  const handleDeleteRoute = useCallback(() => {
    if (selectedRouteId) {
      onRouteDelete?.(selectedRouteId);
    }
  }, [selectedRouteId, onRouteDelete]);

  // --- Render Helpers ---

  /**
   * Render a single route
   */
  const renderRoute = useCallback(
    (route: EvacuationRoute) => {
      const isSelected = route.id === selectedRouteId;
      const style = ROUTE_TYPE_STYLES[route.route_type] || ROUTE_TYPE_STYLES.primary;
      const color = route.color || style.color;
      const width = route.line_width || DEFAULT_LINE_WIDTH;

      const pathData = generatePathData(
        route.waypoints,
        containerWidth,
        containerHeight,
        useSmoothCurves
      );

      if (!pathData) return null;

      const sortedWaypoints = [...route.waypoints].sort((a, b) => a.order - b.order);

      // Calculate arrow positions (at midpoints of segments)
      const arrowPositions: Array<{ x: number; y: number; angle: number }> = [];
      for (let i = 0; i < sortedWaypoints.length - 1; i++) {
        const wp1 = sortedWaypoints[i];
        const wp2 = sortedWaypoints[i + 1];
        const p1 = percentToPixel(wp1.x, wp1.y, containerWidth, containerHeight);
        const p2 = percentToPixel(wp2.x, wp2.y, containerWidth, containerHeight);

        arrowPositions.push({
          x: (p1.px + p2.px) / 2,
          y: (p1.py + p2.py) / 2,
          angle: calculateAngle(p1.px, p1.py, p2.px, p2.py),
        });
      }

      return (
        <g key={route.id} className="evacuation-route">
          {/* Clickable line segments for adding waypoints (when selected and editing) */}
          {isSelected && isEditing && sortedWaypoints.length >= 2 && (
            <>
              {sortedWaypoints.slice(0, -1).map((wp, i) => {
                const next = sortedWaypoints[i + 1];
                const p1 = percentToPixel(wp.x, wp.y, containerWidth, containerHeight);
                const p2 = percentToPixel(next.x, next.y, containerWidth, containerHeight);
                return (
                  <line
                    key={`segment-${i}`}
                    x1={p1.px}
                    y1={p1.py}
                    x2={p2.px}
                    y2={p2.py}
                    stroke="transparent"
                    strokeWidth={width + 10}
                    style={{ cursor: 'copy' }}
                    onClick={(e) => handleLineClick(e, i)}
                  />
                );
              })}
            </>
          )}

          {/* Route path */}
          <path
            d={pathData}
            fill="none"
            stroke={color}
            strokeWidth={isSelected ? width + 2 : width}
            strokeDasharray={style.dashArray}
            strokeLinecap="round"
            strokeLinejoin="round"
            className={cn(
              'transition-all duration-150',
              !isEditing && 'cursor-pointer hover:opacity-80'
            )}
            onClick={(e) => handleRouteClick(e, route.id)}
          />

          {/* Selection highlight */}
          {isSelected && (
            <path
              d={pathData}
              fill="none"
              stroke={color}
              strokeWidth={width + 6}
              strokeOpacity={0.3}
              strokeLinecap="round"
              strokeLinejoin="round"
              pointerEvents="none"
            />
          )}

          {/* Direction arrows */}
          {arrowPositions.map((arrow, i) => (
            <g
              key={`arrow-${i}`}
              transform={`translate(${arrow.x}, ${arrow.y}) rotate(${arrow.angle})`}
            >
              <polygon
                points={`0,-${ARROW_SIZE / 2} ${ARROW_SIZE},0 0,${ARROW_SIZE / 2}`}
                fill={color}
              />
            </g>
          ))}

          {/* Waypoint markers */}
          {sortedWaypoints.map((wp, index) => {
            const pos = percentToPixel(wp.x, wp.y, containerWidth, containerHeight);
            const isWaypointSelected =
              isSelected && editingState.selectedWaypointIndex === index;
            const isFirstOrLast = index === 0 || index === sortedWaypoints.length - 1;

            return (
              <g key={`wp-${index}`}>
                {/* Waypoint circle */}
                <circle
                  cx={pos.px}
                  cy={pos.py}
                  r={isSelected && isEditing ? WAYPOINT_HANDLE_RADIUS : WAYPOINT_RADIUS}
                  fill={isFirstOrLast ? color : 'white'}
                  stroke={color}
                  strokeWidth={2}
                  className={cn(
                    'transition-all duration-150',
                    isSelected && isEditing && 'cursor-move'
                  )}
                  style={{
                    filter: isWaypointSelected ? 'drop-shadow(0 0 4px rgba(0,0,0,0.5))' : undefined,
                  }}
                  onMouseDown={(e) => handleWaypointMouseDown(e, index)}
                />

                {/* Selected waypoint indicator */}
                {isWaypointSelected && (
                  <circle
                    cx={pos.px}
                    cy={pos.py}
                    r={WAYPOINT_HANDLE_RADIUS + 4}
                    fill="none"
                    stroke={color}
                    strokeWidth={2}
                    strokeDasharray="4,2"
                    pointerEvents="none"
                  />
                )}

                {/* Waypoint label */}
                {wp.label && (
                  <text
                    x={pos.px}
                    y={pos.py - WAYPOINT_RADIUS - 8}
                    textAnchor="middle"
                    fontSize="12"
                    fill={color}
                    fontWeight="500"
                  >
                    {wp.label}
                  </text>
                )}
              </g>
            );
          })}

          {/* Route name label */}
          {sortedWaypoints.length > 0 && (
            <text
              x={percentToPixel(sortedWaypoints[0].x, sortedWaypoints[0].y, containerWidth, containerHeight).px}
              y={percentToPixel(sortedWaypoints[0].x, sortedWaypoints[0].y, containerWidth, containerHeight).py - 20}
              textAnchor="middle"
              fontSize="14"
              fontWeight="600"
              fill={color}
              stroke="white"
              strokeWidth="3"
              paintOrder="stroke"
            >
              {route.name}
            </text>
          )}

          {/* Accessible route wheelchair markers */}
          {route.route_type === 'accessible' && (
            <>
              {arrowPositions.map((arrow, i) => (
                <text
                  key={`accessible-${i}`}
                  x={arrow.x}
                  y={arrow.y + width + 14}
                  textAnchor="middle"
                  fontSize="12"
                  fill={color}
                >
                  {'\u267F'}
                </text>
              ))}
            </>
          )}

          {/* Emergency vehicle markers */}
          {route.route_type === 'emergency_vehicle' && (
            <>
              {arrowPositions
                .filter((_, i) => i % 2 === 0) // Show every other segment
                .map((arrow, i) => (
                  <text
                    key={`vehicle-${i}`}
                    x={arrow.x}
                    y={arrow.y + width + 14}
                    textAnchor="middle"
                    fontSize="12"
                    fill={color}
                  >
                    {'\u{1F691}'}
                  </text>
                ))}
            </>
          )}
        </g>
      );
    },
    [
      selectedRouteId,
      containerWidth,
      containerHeight,
      useSmoothCurves,
      isEditing,
      editingState.selectedWaypointIndex,
      handleLineClick,
      handleRouteClick,
      handleWaypointMouseDown,
    ]
  );

  /**
   * Render drawing preview
   */
  const renderDrawingPreview = useCallback(() => {
    if (!drawingState.isDrawing || drawingState.waypoints.length === 0) return null;

    const style = ROUTE_TYPE_STYLES[selectedRouteType];
    const color = selectedColor;

    // Draw existing waypoints
    const points = drawingState.waypoints.map((wp) =>
      percentToPixel(wp.x, wp.y, containerWidth, containerHeight)
    );

    // Path for existing waypoints
    const existingPath =
      points.length >= 2
        ? points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.px} ${p.py}`).join(' ')
        : '';

    // Preview line to cursor
    const lastPoint = points[points.length - 1];
    const cursorPos = drawingState.cursorPosition
      ? percentToPixel(
          drawingState.cursorPosition.x,
          drawingState.cursorPosition.y,
          containerWidth,
          containerHeight
        )
      : null;

    return (
      <g className="drawing-preview">
        {/* Existing waypoints path */}
        {existingPath && (
          <path
            d={existingPath}
            fill="none"
            stroke={color}
            strokeWidth={lineWidth}
            strokeDasharray={style.dashArray}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}

        {/* Preview line to cursor */}
        {lastPoint && cursorPos && (
          <line
            x1={lastPoint.px}
            y1={lastPoint.py}
            x2={cursorPos.px}
            y2={cursorPos.py}
            stroke={color}
            strokeWidth={lineWidth}
            strokeDasharray="4,4"
            strokeOpacity={0.6}
          />
        )}

        {/* Waypoint markers */}
        {points.map((p, i) => (
          <circle
            key={`preview-wp-${i}`}
            cx={p.px}
            cy={p.py}
            r={WAYPOINT_RADIUS}
            fill={i === 0 ? color : 'white'}
            stroke={color}
            strokeWidth={2}
          />
        ))}

        {/* Cursor waypoint preview */}
        {cursorPos && (
          <circle
            cx={cursorPos.px}
            cy={cursorPos.py}
            r={WAYPOINT_RADIUS}
            fill="white"
            stroke={color}
            strokeWidth={2}
            strokeDasharray="2,2"
            opacity={0.6}
          />
        )}
      </g>
    );
  }, [drawingState, selectedRouteType, selectedColor, lineWidth, containerWidth, containerHeight]);

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      {/* Floor Plan Image */}
      <img
        src={floorPlanUrl}
        alt="Floor plan"
        className="w-full h-full object-contain"
        draggable={false}
      />

      {/* SVG Overlay */}
      <svg
        ref={svgRef}
        className={cn(
          'absolute inset-0 w-full h-full',
          isEditing && !drawingState.isDrawing && 'cursor-default',
          drawingState.isDrawing && 'cursor-crosshair'
        )}
        viewBox={`0 0 ${containerWidth} ${containerHeight}`}
        preserveAspectRatio="xMidYMid meet"
        onClick={handleCanvasClick}
        onDoubleClick={handleCanvasDoubleClick}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* SVG Definitions for markers */}
        <defs>
          {Object.entries(ROUTE_TYPE_STYLES).map(([type, style]) => (
            <marker
              key={`arrow-${type}`}
              id={`arrow-${type}`}
              markerWidth={ARROW_SIZE}
              markerHeight={ARROW_SIZE}
              refX={ARROW_SIZE}
              refY={ARROW_SIZE / 2}
              orient="auto"
            >
              <polygon
                points={`0 0, ${ARROW_SIZE} ${ARROW_SIZE / 2}, 0 ${ARROW_SIZE}`}
                fill={style.color}
              />
            </marker>
          ))}
        </defs>

        {/* Render all routes */}
        {routes.map(renderRoute)}

        {/* Render drawing preview */}
        {renderDrawingPreview()}
      </svg>

      {/* Editing Toolbar */}
      {isEditing && (
        <div className="absolute top-2 left-2 bg-white rounded-lg shadow-lg p-3 space-y-3 min-w-[200px]">
          {/* Drawing mode indicator */}
          {drawingState.isDrawing && (
            <div className="text-sm text-blue-600 font-medium flex items-center gap-2">
              <span className="w-2 h-2 bg-blue-600 rounded-full animate-pulse" />
              Drawing route... ({drawingState.waypoints.length} points)
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-2">
            <button
              onClick={handleStartDrawing}
              disabled={drawingState.isDrawing}
              className={cn(
                'px-3 py-1.5 text-sm font-medium rounded transition-colors',
                drawingState.isDrawing
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              )}
            >
              New Route
            </button>

            {selectedRouteId && !drawingState.isDrawing && (
              <button
                onClick={handleDeleteRoute}
                className="px-3 py-1.5 text-sm font-medium rounded bg-red-600 text-white hover:bg-red-700 transition-colors"
              >
                Delete Route
              </button>
            )}
          </div>

          {/* Route type selector */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Route Type
            </label>
            <select
              value={selectedRouteType}
              onChange={(e) => setSelectedRouteType(e.target.value as RouteType)}
              className="w-full text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {Object.entries(ROUTE_TYPE_STYLES).map(([type, style]) => (
                <option key={type} value={type}>
                  {style.icon} {style.label}
                </option>
              ))}
            </select>
          </div>

          {/* Color picker */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Route Color
            </label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={selectedColor}
                onChange={(e) => setSelectedColor(e.target.value)}
                className="w-8 h-8 rounded border border-gray-300 cursor-pointer"
              />
              <span className="text-sm text-gray-600">{selectedColor}</span>
            </div>
          </div>

          {/* Line width slider */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Line Width: {lineWidth}px
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={lineWidth}
              onChange={(e) => setLineWidth(Number(e.target.value))}
              className="w-full"
            />
          </div>

          {/* Smooth curves toggle */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="smooth-curves"
              checked={useSmoothCurves}
              onChange={(e) => setUseSmoothCurves(e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="smooth-curves" className="text-sm text-gray-700">
              Smooth curves
            </label>
          </div>

          {/* Instructions */}
          <div className="text-xs text-gray-500 border-t pt-2 mt-2">
            {drawingState.isDrawing ? (
              <>
                <p>Click to add waypoints</p>
                <p>Double-click or press Enter to finish</p>
                <p>Press Escape to cancel</p>
              </>
            ) : selectedRouteId ? (
              <>
                <p>Drag waypoints to reposition</p>
                <p>Click on line to add waypoint</p>
                <p>Select waypoint + Delete to remove</p>
              </>
            ) : (
              <p>Click &quot;New Route&quot; to start drawing</p>
            )}
          </div>
        </div>
      )}

      {/* Route Legend */}
      {!isEditing && routes.length > 0 && (
        <div className="absolute bottom-2 left-2 bg-white/90 rounded-lg shadow p-2">
          <div className="text-xs font-medium text-gray-700 mb-1">Routes</div>
          <div className="space-y-1">
            {routes.map((route) => {
              const style = ROUTE_TYPE_STYLES[route.route_type] || ROUTE_TYPE_STYLES.primary;
              return (
                <button
                  key={route.id}
                  onClick={() => onRouteSelect?.(route.id)}
                  className={cn(
                    'flex items-center gap-2 text-xs w-full px-1 py-0.5 rounded transition-colors',
                    route.id === selectedRouteId
                      ? 'bg-gray-100'
                      : 'hover:bg-gray-50'
                  )}
                >
                  <span
                    className="w-4 h-0.5"
                    style={{
                      backgroundColor: route.color || style.color,
                      borderStyle: style.dashArray ? 'dashed' : 'solid',
                    }}
                  />
                  <span className="text-gray-700">{route.name}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default EvacuationRouteDrawer;
