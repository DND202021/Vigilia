/**
 * EmergencyPlanViewer Component
 * Read-only view of the complete emergency plan for a building.
 * Displays procedures, evacuation routes, checkpoints, and floor plan overlays.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, Badge, Button } from '../ui';
import { cn, formatDate } from '../../utils';
import { tokenStorage, emergencyPlanningApi, toAbsoluteApiUrl } from '../../services/api';
import type {
  EmergencyPlanOverview,
  EmergencyProcedure,
  EvacuationRoute,
  EmergencyCheckpoint,
  EmergencyProcedureType,
  RouteType,
  CheckpointType,
} from '../../types';

// ============================================================================
// Types
// ============================================================================

interface FloorPlanInfo {
  id: string;
  name: string;
  floor_number: number;
  image_url: string;
}

interface EmergencyPlanViewerProps {
  buildingId: string;
  buildingName: string;
  floorPlans: FloorPlanInfo[];
  plan: EmergencyPlanOverview;
  onEdit?: () => void;
  onPrint?: () => void;
  className?: string;
}

// ============================================================================
// Configuration
// ============================================================================

const procedureTypeConfig: Record<EmergencyProcedureType, { label: string; icon: string; color: string }> = {
  evacuation: { label: 'Evacuation', icon: '\u{1F6AA}', color: 'bg-green-500' },
  fire: { label: 'Fire', icon: '\u{1F525}', color: 'bg-red-500' },
  medical: { label: 'Medical', icon: '\u{1F3E5}', color: 'bg-blue-500' },
  hazmat: { label: 'Hazmat', icon: '\u2622\uFE0F', color: 'bg-purple-500' },
  lockdown: { label: 'Lockdown', icon: '\u{1F512}', color: 'bg-gray-700' },
  active_shooter: { label: 'Active Shooter', icon: '\u{1F6A8}', color: 'bg-red-700' },
  weather: { label: 'Weather', icon: '\u26C8\uFE0F', color: 'bg-cyan-500' },
  utility_failure: { label: 'Utility Failure', icon: '\u26A1', color: 'bg-yellow-500' },
};

const routeTypeConfig: Record<RouteType, { label: string; color: string; dashArray?: string }> = {
  primary: { label: 'Primary', color: '#22c55e' },
  secondary: { label: 'Secondary', color: '#3b82f6' },
  accessible: { label: 'Accessible', color: '#a855f7', dashArray: '5,5' },
  emergency_vehicle: { label: 'Emergency Vehicle', color: '#ef4444', dashArray: '10,5' },
};

const checkpointTypeConfig: Record<CheckpointType, { label: string; icon: string; color: string }> = {
  assembly_point: { label: 'Assembly Point', icon: '\u{1F465}', color: 'bg-green-500' },
  muster_station: { label: 'Muster Station', icon: '\u{1F3C1}', color: 'bg-blue-500' },
  first_aid: { label: 'First Aid', icon: '\u2695\uFE0F', color: 'bg-red-500' },
  command_post: { label: 'Command Post', icon: '\u{1F3DB}\uFE0F', color: 'bg-gray-700' },
  triage_area: { label: 'Triage Area', icon: '\u{1F6D1}', color: 'bg-orange-500' },
  decontamination: { label: 'Decontamination', icon: '\u{1F9FC}', color: 'bg-purple-500' },
  staging_area: { label: 'Staging Area', icon: '\u{1F697}', color: 'bg-cyan-500' },
  media_point: { label: 'Media Point', icon: '\u{1F4F9}', color: 'bg-yellow-500' },
};

const priorityConfig: Record<number, { label: string; variant: 'danger' | 'warning' | 'info' | 'secondary' }> = {
  1: { label: 'Critical', variant: 'danger' },
  2: { label: 'High', variant: 'warning' },
  3: { label: 'Medium', variant: 'info' },
  4: { label: 'Low', variant: 'secondary' },
  5: { label: 'Informational', variant: 'secondary' },
};

// ============================================================================
// Helper Components
// ============================================================================

/**
 * Collapsible section for organizing content
 */
function CollapsibleSection({
  title,
  icon,
  children,
  defaultOpen = true,
  badge,
  headerClassName,
}: {
  title: string;
  icon?: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  badge?: React.ReactNode;
  headerClassName?: string;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'w-full flex items-center justify-between py-3 px-4 text-left bg-gray-50 hover:bg-gray-100 transition-colors',
          headerClassName
        )}
      >
        <div className="flex items-center gap-2">
          {icon && <span className="text-lg">{icon}</span>}
          <span className="text-sm font-semibold text-gray-800">{title}</span>
          {badge}
        </div>
        <svg
          className={cn(
            'w-5 h-5 text-gray-500 transition-transform',
            isOpen && 'transform rotate-180'
          )}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && <div className="p-4 bg-white">{children}</div>}
    </div>
  );
}

/**
 * Procedure card showing detailed procedure information
 */
function ProcedureCard({ procedure }: { procedure: EmergencyProcedure }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const config = procedureTypeConfig[procedure.procedure_type];
  const priority = priorityConfig[procedure.priority] || priorityConfig[3];

  return (
    <Card className={cn('overflow-hidden', !procedure.is_active && 'opacity-60')}>
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full text-left"
      >
        <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0">
          <div className="flex items-center gap-3">
            <span
              className={cn(
                'w-10 h-10 rounded-lg flex items-center justify-center text-white text-lg',
                config?.color || 'bg-gray-500'
              )}
            >
              {config?.icon || '\u{1F4CB}'}
            </span>
            <div>
              <h4 className="font-semibold text-gray-900">{procedure.name}</h4>
              <p className="text-xs text-gray-500">{config?.label || procedure.procedure_type}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={priority.variant} size="sm">
              P{procedure.priority} - {priority.label}
            </Badge>
            {!procedure.is_active && (
              <Badge variant="secondary" size="sm">Inactive</Badge>
            )}
            <svg
              className={cn(
                'w-5 h-5 text-gray-400 transition-transform',
                isExpanded && 'transform rotate-180'
              )}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </CardHeader>
      </button>

      {isExpanded && (
        <CardContent className="pt-0 pb-4 px-4 space-y-4">
          {/* Description */}
          {procedure.description && (
            <p className="text-sm text-gray-600">{procedure.description}</p>
          )}

          {/* Estimated Duration */}
          {procedure.estimated_duration_minutes && (
            <div className="flex items-center gap-2 text-sm">
              <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-gray-500">Estimated Duration:</span>
              <span className="font-medium">{procedure.estimated_duration_minutes} minutes</span>
            </div>
          )}

          {/* Steps */}
          {procedure.steps && procedure.steps.length > 0 && (
            <div>
              <h5 className="text-sm font-semibold text-gray-700 mb-2">Procedure Steps</h5>
              <ol className="space-y-2">
                {procedure.steps
                  .sort((a, b) => a.order - b.order)
                  .map((step, idx) => (
                    <li key={idx} className="flex gap-3 text-sm">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-semibold text-xs">
                        {step.order}
                      </span>
                      <div className="flex-1">
                        <p className="font-medium text-gray-800">{step.title}</p>
                        <p className="text-gray-600">{step.description}</p>
                        {(step.responsible_role || step.duration_minutes) && (
                          <div className="flex gap-4 mt-1 text-xs text-gray-500">
                            {step.responsible_role && (
                              <span>Role: {step.responsible_role}</span>
                            )}
                            {step.duration_minutes && (
                              <span>Duration: {step.duration_minutes} min</span>
                            )}
                          </div>
                        )}
                      </div>
                    </li>
                  ))}
              </ol>
            </div>
          )}

          {/* Contacts */}
          {procedure.contacts && procedure.contacts.length > 0 && (
            <div>
              <h5 className="text-sm font-semibold text-gray-700 mb-2">Emergency Contacts</h5>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {procedure.contacts.map((contact, idx) => (
                  <div key={idx} className="flex items-center gap-2 bg-gray-50 rounded-lg p-2">
                    <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 text-sm font-medium">
                      {contact.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{contact.name}</p>
                      <p className="text-xs text-gray-500 truncate">{contact.role}</p>
                    </div>
                    {contact.phone && (
                      <a
                        href={`tel:${contact.phone}`}
                        className="text-blue-600 hover:text-blue-800"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                        </svg>
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Equipment */}
          {procedure.equipment_needed && procedure.equipment_needed.length > 0 && (
            <div>
              <h5 className="text-sm font-semibold text-gray-700 mb-2">Required Equipment</h5>
              <div className="flex flex-wrap gap-2">
                {procedure.equipment_needed.map((item, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 rounded text-sm text-gray-700"
                  >
                    <svg className="w-3 h-3 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    {item}
                  </span>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}

/**
 * Floor plan view with route and checkpoint overlays
 */
function FloorPlanView({
  floorPlan,
  routes,
  checkpoints,
  highlightedRouteId,
  onRouteClick,
}: {
  floorPlan: FloorPlanInfo;
  routes: EvacuationRoute[];
  checkpoints: EmergencyCheckpoint[];
  highlightedRouteId?: string | null;
  onRouteClick?: (route: EvacuationRoute) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [authImageUrl, setAuthImageUrl] = useState<string | null>(null);

  // Filter routes and checkpoints for this floor
  const floorRoutes = routes.filter(r => r.floor_plan_id === floorPlan.id && r.is_active);
  const floorCheckpoints = checkpoints.filter(c => c.floor_plan_id === floorPlan.id && c.is_active);

  // Auth image loading - convert relative URL to absolute
  const imageUrl = toAbsoluteApiUrl(floorPlan.image_url);

  useEffect(() => {
    if (!imageUrl) return;

    let revoked = false;
    const token = tokenStorage.getAccessToken();

    setImageLoaded(false);
    setImageError(false);

    fetch(imageUrl, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.blob();
      })
      .then((blob) => {
        if (!revoked) {
          setAuthImageUrl(URL.createObjectURL(blob));
          setImageError(false);
        }
      })
      .catch(() => {
        if (!revoked) {
          setImageError(true);
        }
      });

    return () => {
      revoked = true;
      if (authImageUrl) {
        URL.revokeObjectURL(authImageUrl);
      }
    };
  }, [imageUrl]); // eslint-disable-line react-hooks/exhaustive-deps

  // Zoom controls
  const zoomIn = useCallback(() => setScale((s) => Math.min(s * 1.2, 5)), []);
  const zoomOut = useCallback(() => setScale((s) => Math.max(s / 1.2, 0.5)), []);
  const resetView = useCallback(() => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setScale((s) => Math.min(Math.max(s * delta, 0.5), 5));
  }, []);

  // Pan handlers
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button !== 0) return;
      setIsDragging(true);
      setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
    },
    [position]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging) return;
      setPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    },
    [isDragging, dragStart]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Toggle fullscreen
  const toggleFullscreen = useCallback(() => {
    if (!containerRef.current) return;

    if (!isFullscreen) {
      if (containerRef.current.requestFullscreen) {
        containerRef.current.requestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
    setIsFullscreen(!isFullscreen);
  }, [isFullscreen]);

  return (
    <div ref={containerRef} className="flex flex-col h-full">
      {/* Controls */}
      <div className="flex items-center justify-between p-2 bg-gray-100 border-b">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">
            {floorPlan.name || `Floor ${floorPlan.floor_number}`}
          </span>
          <Badge variant="info" size="sm">
            {floorRoutes.length} routes
          </Badge>
          <Badge variant="success" size="sm">
            {floorCheckpoints.length} checkpoints
          </Badge>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={zoomOut}
            className="p-1.5 rounded hover:bg-gray-200 transition-colors"
            title="Zoom Out"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
            </svg>
          </button>
          <span className="text-xs text-gray-600 w-12 text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={zoomIn}
            className="p-1.5 rounded hover:bg-gray-200 transition-colors"
            title="Zoom In"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
          <button
            onClick={resetView}
            className="p-1.5 rounded hover:bg-gray-200 transition-colors ml-1"
            title="Reset View"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
              />
            </svg>
          </button>
          <button
            onClick={toggleFullscreen}
            className="p-1.5 rounded hover:bg-gray-200 transition-colors ml-2"
            title="Toggle Fullscreen"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {isFullscreen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Viewer Container */}
      <div
        className="flex-1 overflow-hidden bg-gray-50 relative cursor-grab active:cursor-grabbing"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{ minHeight: '400px' }}
      >
        <div
          className="absolute inset-0 flex items-center justify-center"
          style={{
            transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
            transformOrigin: 'center center',
            transition: isDragging ? 'none' : 'transform 0.1s ease-out',
          }}
        >
          {authImageUrl ? (
            <div className="relative">
              <img
                ref={imageRef}
                src={authImageUrl}
                alt={`Floor plan - ${floorPlan.name || `Floor ${floorPlan.floor_number}`}`}
                className={cn(
                  'max-w-full max-h-full object-contain',
                  imageLoaded ? 'opacity-100' : 'opacity-0'
                )}
                onLoad={() => setImageLoaded(true)}
                onError={() => setImageError(true)}
                draggable={false}
              />

              {/* SVG Overlay for Routes */}
              {imageLoaded && (
                <svg
                  className="absolute inset-0 w-full h-full pointer-events-none"
                  style={{ overflow: 'visible' }}
                >
                  {floorRoutes.map((route) => {
                    const config = routeTypeConfig[route.route_type];
                    const isHighlighted = highlightedRouteId === route.id;
                    const waypoints = route.waypoints.sort((a, b) => a.order - b.order);

                    if (waypoints.length < 2) return null;

                    const pathData = waypoints
                      .map((wp, idx) => `${idx === 0 ? 'M' : 'L'} ${wp.x}% ${wp.y}%`)
                      .join(' ');

                    return (
                      <g key={route.id}>
                        <path
                          d={pathData}
                          fill="none"
                          stroke={config?.color || '#6b7280'}
                          strokeWidth={isHighlighted ? 6 : 4}
                          strokeDasharray={config?.dashArray}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          className={cn(
                            'pointer-events-auto cursor-pointer transition-all',
                            isHighlighted && 'filter drop-shadow-lg'
                          )}
                          onClick={() => onRouteClick?.(route)}
                        />
                        {/* Route label at midpoint */}
                        {waypoints.length >= 2 && (
                          <text
                            x={`${waypoints[Math.floor(waypoints.length / 2)].x}%`}
                            y={`${waypoints[Math.floor(waypoints.length / 2)].y}%`}
                            fill={config?.color || '#6b7280'}
                            fontSize="10"
                            fontWeight="bold"
                            textAnchor="middle"
                            dy="-8"
                            className="pointer-events-none"
                          >
                            {route.name}
                          </text>
                        )}
                      </g>
                    );
                  })}
                </svg>
              )}

              {/* Checkpoint markers */}
              {imageLoaded &&
                floorCheckpoints.map((checkpoint) => {
                  const config = checkpointTypeConfig[checkpoint.checkpoint_type];
                  return (
                    <div
                      key={checkpoint.id}
                      className={cn(
                        'absolute w-8 h-8 -ml-4 -mt-4 rounded-full flex items-center justify-center',
                        'text-white text-sm shadow-lg border-2 border-white',
                        'hover:scale-125 transition-transform cursor-pointer',
                        config?.color || 'bg-gray-500'
                      )}
                      style={{
                        left: `${checkpoint.position_x}%`,
                        top: `${checkpoint.position_y}%`,
                      }}
                      title={`${checkpoint.name} (${config?.label || checkpoint.checkpoint_type})`}
                    >
                      {config?.icon || '\u{1F4CD}'}
                    </div>
                  );
                })}
            </div>
          ) : (
            <div className="text-center text-gray-500 p-8">
              <svg
                className="w-16 h-16 mx-auto mb-4 text-gray-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
                />
              </svg>
              <p>No floor plan image available</p>
            </div>
          )}

          {/* Loading indicator */}
          {authImageUrl && !imageLoaded && !imageError && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          )}

          {/* Error state */}
          {imageError && (
            <div className="text-center text-red-500 p-8">
              <svg
                className="w-16 h-16 mx-auto mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <p>Failed to load floor plan image</p>
            </div>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="p-2 bg-gray-50 border-t">
        <div className="flex flex-wrap gap-3 text-xs">
          {/* Route types */}
          <span className="text-gray-500 font-medium">Routes:</span>
          {Object.entries(routeTypeConfig).map(([type, config]) => (
            <div key={type} className="flex items-center gap-1">
              <div
                className="w-6 h-1 rounded"
                style={{
                  backgroundColor: config.color,
                  backgroundImage: config.dashArray ? `repeating-linear-gradient(90deg, ${config.color}, ${config.color} 3px, transparent 3px, transparent 6px)` : undefined,
                }}
              />
              <span className="text-gray-600">{config.label}</span>
            </div>
          ))}
          <span className="text-gray-300">|</span>
          {/* Checkpoint types */}
          <span className="text-gray-500 font-medium">Checkpoints:</span>
          {Object.entries(checkpointTypeConfig)
            .filter(([type]) => floorCheckpoints.some(c => c.checkpoint_type === type))
            .map(([type, config]) => (
              <div key={type} className="flex items-center gap-1">
                <span
                  className={cn(
                    'w-4 h-4 rounded-full flex items-center justify-center text-white text-[10px]',
                    config.color
                  )}
                >
                  {config.icon}
                </span>
                <span className="text-gray-600">{config.label}</span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Quick stats cards
 */
function QuickStats({
  procedures,
  routes,
  checkpoints,
}: {
  procedures: EmergencyProcedure[];
  routes: EvacuationRoute[];
  checkpoints: EmergencyCheckpoint[];
}) {
  const activeProcedures = procedures.filter(p => p.is_active);
  const activeRoutes = routes.filter(r => r.is_active);
  const activeCheckpoints = checkpoints.filter(c => c.is_active);

  // Count contacts
  const totalContacts = activeProcedures.reduce(
    (sum, p) => sum + (p.contacts?.length || 0),
    0
  );

  // Count by checkpoint type
  const checkpointsByType = activeCheckpoints.reduce((acc, c) => {
    acc[c.checkpoint_type] = (acc[c.checkpoint_type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Count by procedure type
  const proceduresByType = activeProcedures.reduce((acc, p) => {
    acc[p.procedure_type] = (acc[p.procedure_type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{activeRoutes.length}</p>
            <p className="text-xs text-gray-500">Evacuation Routes</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{activeCheckpoints.length}</p>
            <p className="text-xs text-gray-500">Checkpoints</p>
          </div>
        </div>
        {Object.keys(checkpointsByType).length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {Object.entries(checkpointsByType).slice(0, 3).map(([type, count]) => (
              <span key={type} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                {checkpointTypeConfig[type as CheckpointType]?.label || type}: {count}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{totalContacts}</p>
            <p className="text-xs text-gray-500">Emergency Contacts</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{activeProcedures.length}</p>
            <p className="text-xs text-gray-500">Procedures</p>
          </div>
        </div>
        {Object.keys(proceduresByType).length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {Object.entries(proceduresByType).slice(0, 3).map(([type, count]) => (
              <span key={type} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                {procedureTypeConfig[type as EmergencyProcedureType]?.label || type}: {count}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function EmergencyPlanViewer({
  buildingId,
  buildingName,
  floorPlans,
  plan,
  onEdit,
  onPrint,
  className,
}: EmergencyPlanViewerProps) {
  const [selectedFloorPlanId, setSelectedFloorPlanId] = useState<string | null>(
    floorPlans.length > 0 ? floorPlans[0].id : null
  );
  const [highlightedRouteId, setHighlightedRouteId] = useState<string | null>(null);
  const [isPrintMode, setIsPrintMode] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const selectedFloorPlan = floorPlans.find(fp => fp.id === selectedFloorPlanId);

  // Sort floor plans by floor number
  const sortedFloorPlans = [...floorPlans].sort((a, b) => a.floor_number - b.floor_number);

  // Handle print
  const handlePrint = useCallback(() => {
    setIsPrintMode(true);
    setTimeout(() => {
      window.print();
      setIsPrintMode(false);
    }, 100);
    onPrint?.();
  }, [onPrint]);

  // Handle PDF export
  const handleExportPDF = useCallback(async () => {
    setIsExporting(true);
    try {
      const blob = await emergencyPlanningApi.exportEmergencyPlan(buildingId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `emergency-plan-${buildingName.replace(/\s+/g, '-').toLowerCase()}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export PDF:', error);
    } finally {
      setIsExporting(false);
    }
  }, [buildingId, buildingName]);

  // Handle route highlight from table click
  const handleRouteTableClick = useCallback((route: EvacuationRoute) => {
    setHighlightedRouteId(route.id);
    if (route.floor_plan_id) {
      setSelectedFloorPlanId(route.floor_plan_id);
    }
    // Clear highlight after 3 seconds
    setTimeout(() => setHighlightedRouteId(null), 3000);
  }, []);

  // Get last updated date
  const lastUpdated = plan.procedures.length > 0
    ? Math.max(...plan.procedures.map(p => new Date(p.updated_at).getTime()))
    : null;

  // Print-friendly layout
  if (isPrintMode) {
    return (
      <div className="print-container p-8 bg-white">
        {/* Header */}
        <div className="text-center mb-8 border-b pb-4">
          <h1 className="text-2xl font-bold">{buildingName}</h1>
          <h2 className="text-xl text-gray-600">Emergency Response Plan</h2>
          {lastUpdated && (
            <p className="text-sm text-gray-500 mt-2">
              Last Updated: {formatDate(new Date(lastUpdated).toISOString())}
            </p>
          )}
        </div>

        {/* Quick Stats */}
        <div className="mb-8">
          <h3 className="text-lg font-semibold mb-4">Plan Summary</h3>
          <div className="grid grid-cols-4 gap-4 text-center">
            <div className="border p-3 rounded">
              <p className="text-2xl font-bold">{plan.routes.filter(r => r.is_active).length}</p>
              <p className="text-sm text-gray-600">Evacuation Routes</p>
            </div>
            <div className="border p-3 rounded">
              <p className="text-2xl font-bold">{plan.checkpoints.filter(c => c.is_active).length}</p>
              <p className="text-sm text-gray-600">Checkpoints</p>
            </div>
            <div className="border p-3 rounded">
              <p className="text-2xl font-bold">
                {plan.procedures.reduce((sum, p) => sum + (p.contacts?.length || 0), 0)}
              </p>
              <p className="text-sm text-gray-600">Emergency Contacts</p>
            </div>
            <div className="border p-3 rounded">
              <p className="text-2xl font-bold">{plan.procedures.filter(p => p.is_active).length}</p>
              <p className="text-sm text-gray-600">Procedures</p>
            </div>
          </div>
        </div>

        {/* Procedures */}
        <div className="mb-8 page-break-inside-avoid">
          <h3 className="text-lg font-semibold mb-4">Emergency Procedures</h3>
          {plan.procedures.filter(p => p.is_active).map((procedure) => (
            <div key={procedure.id} className="mb-6 border p-4 rounded">
              <h4 className="font-semibold text-lg">
                {procedure.name}
                <span className="text-sm text-gray-500 ml-2">
                  (Priority {procedure.priority})
                </span>
              </h4>
              {procedure.description && (
                <p className="text-sm text-gray-600 mt-1">{procedure.description}</p>
              )}
              {procedure.steps && procedure.steps.length > 0 && (
                <div className="mt-3">
                  <p className="font-medium text-sm mb-2">Steps:</p>
                  <ol className="list-decimal list-inside text-sm space-y-1">
                    {procedure.steps.sort((a, b) => a.order - b.order).map((step) => (
                      <li key={step.order}>
                        <strong>{step.title}</strong> - {step.description}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
              {procedure.contacts && procedure.contacts.length > 0 && (
                <div className="mt-3">
                  <p className="font-medium text-sm mb-2">Contacts:</p>
                  <table className="w-full text-sm border">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="border p-1 text-left">Name</th>
                        <th className="border p-1 text-left">Role</th>
                        <th className="border p-1 text-left">Phone</th>
                        <th className="border p-1 text-left">Email</th>
                      </tr>
                    </thead>
                    <tbody>
                      {procedure.contacts.map((contact, idx) => (
                        <tr key={idx}>
                          <td className="border p-1">{contact.name}</td>
                          <td className="border p-1">{contact.role}</td>
                          <td className="border p-1">{contact.phone || '-'}</td>
                          <td className="border p-1">{contact.email || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Routes Table */}
        <div className="mb-8 page-break-inside-avoid">
          <h3 className="text-lg font-semibold mb-4">Evacuation Routes</h3>
          <table className="w-full text-sm border">
            <thead>
              <tr className="bg-gray-50">
                <th className="border p-2 text-left">Name</th>
                <th className="border p-2 text-left">Type</th>
                <th className="border p-2 text-left">Floor</th>
                <th className="border p-2 text-right">Capacity</th>
                <th className="border p-2 text-right">Est. Time</th>
              </tr>
            </thead>
            <tbody>
              {plan.routes.filter(r => r.is_active).map((route) => {
                const floor = floorPlans.find(fp => fp.id === route.floor_plan_id);
                return (
                  <tr key={route.id}>
                    <td className="border p-2">{route.name}</td>
                    <td className="border p-2">{routeTypeConfig[route.route_type]?.label || route.route_type}</td>
                    <td className="border p-2">{floor?.name || 'All Floors'}</td>
                    <td className="border p-2 text-right">{route.capacity || '-'}</td>
                    <td className="border p-2 text-right">
                      {route.estimated_time_seconds ? `${Math.ceil(route.estimated_time_seconds / 60)} min` : '-'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Checkpoints Table */}
        <div className="mb-8 page-break-inside-avoid">
          <h3 className="text-lg font-semibold mb-4">Emergency Checkpoints</h3>
          <table className="w-full text-sm border">
            <thead>
              <tr className="bg-gray-50">
                <th className="border p-2 text-left">Name</th>
                <th className="border p-2 text-left">Type</th>
                <th className="border p-2 text-left">Floor</th>
                <th className="border p-2 text-right">Capacity</th>
                <th className="border p-2 text-left">Responsible Person</th>
              </tr>
            </thead>
            <tbody>
              {plan.checkpoints.filter(c => c.is_active).map((checkpoint) => {
                const floor = floorPlans.find(fp => fp.id === checkpoint.floor_plan_id);
                return (
                  <tr key={checkpoint.id}>
                    <td className="border p-2">{checkpoint.name}</td>
                    <td className="border p-2">{checkpointTypeConfig[checkpoint.checkpoint_type]?.label || checkpoint.checkpoint_type}</td>
                    <td className="border p-2">{floor?.name || '-'}</td>
                    <td className="border p-2 text-right">{checkpoint.capacity || '-'}</td>
                    <td className="border p-2">{checkpoint.responsible_person || '-'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <Card>
        <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
          <div>
            <CardTitle className="text-xl">{buildingName}</CardTitle>
            <p className="text-sm text-gray-500 mt-1">Emergency Response Plan</p>
            {lastUpdated && (
              <p className="text-xs text-gray-400 mt-1">
                Last updated: {formatDate(new Date(lastUpdated).toISOString())}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {onEdit && (
              <Button variant="outline" size="sm" onClick={onEdit}>
                <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Edit
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={handlePrint}>
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
              </svg>
              Print
            </Button>
            <Button variant="primary" size="sm" onClick={handleExportPDF} isLoading={isExporting}>
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Export PDF
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          <QuickStats
            procedures={plan.procedures}
            routes={plan.routes}
            checkpoints={plan.checkpoints}
          />
        </CardContent>
      </Card>

      {/* Procedures Section */}
      <CollapsibleSection
        title="Emergency Procedures"
        icon="\u{1F4CB}"
        defaultOpen={true}
        badge={
          <Badge variant="info" size="sm">
            {plan.procedures.filter(p => p.is_active).length}
          </Badge>
        }
      >
        {plan.procedures.length > 0 ? (
          <div className="space-y-3">
            {plan.procedures
              .sort((a, b) => a.priority - b.priority)
              .map((procedure) => (
                <ProcedureCard key={procedure.id} procedure={procedure} />
              ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <svg className="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p>No procedures defined</p>
          </div>
        )}
      </CollapsibleSection>

      {/* Floor Plan View */}
      {floorPlans.length > 0 && (
        <CollapsibleSection
          title="Floor Plan View"
          icon="\u{1F5FA}\uFE0F"
          defaultOpen={true}
        >
          {/* Floor selector tabs */}
          <div className="flex flex-wrap gap-2 mb-4">
            {sortedFloorPlans.map((fp) => (
              <button
                key={fp.id}
                onClick={() => setSelectedFloorPlanId(fp.id)}
                className={cn(
                  'px-3 py-1.5 text-sm rounded-lg transition-colors',
                  selectedFloorPlanId === fp.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                )}
              >
                {fp.name || `Floor ${fp.floor_number}`}
              </button>
            ))}
          </div>

          {/* Floor plan viewer */}
          {selectedFloorPlan && (
            <div className="border rounded-lg overflow-hidden" style={{ height: '500px' }}>
              <FloorPlanView
                floorPlan={selectedFloorPlan}
                routes={plan.routes}
                checkpoints={plan.checkpoints}
                highlightedRouteId={highlightedRouteId}
                onRouteClick={(route) => setHighlightedRouteId(route.id === highlightedRouteId ? null : route.id)}
              />
            </div>
          )}
        </CollapsibleSection>
      )}

      {/* Routes Summary */}
      <CollapsibleSection
        title="Evacuation Routes Summary"
        icon="\u{1F6A8}"
        defaultOpen={false}
        badge={
          <Badge variant="success" size="sm">
            {plan.routes.filter(r => r.is_active).length}
          </Badge>
        }
      >
        {plan.routes.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-3 text-xs font-semibold text-gray-500 uppercase">Name</th>
                  <th className="text-left py-3 px-3 text-xs font-semibold text-gray-500 uppercase">Type</th>
                  <th className="text-left py-3 px-3 text-xs font-semibold text-gray-500 uppercase">Floor</th>
                  <th className="text-right py-3 px-3 text-xs font-semibold text-gray-500 uppercase">Capacity</th>
                  <th className="text-right py-3 px-3 text-xs font-semibold text-gray-500 uppercase">Est. Time</th>
                  <th className="text-center py-3 px-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
                  <th className="py-3 px-3"></th>
                </tr>
              </thead>
              <tbody>
                {plan.routes.map((route) => {
                  const config = routeTypeConfig[route.route_type];
                  const floor = floorPlans.find(fp => fp.id === route.floor_plan_id);
                  return (
                    <tr
                      key={route.id}
                      className={cn(
                        'border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors',
                        highlightedRouteId === route.id && 'bg-blue-50'
                      )}
                      onClick={() => handleRouteTableClick(route)}
                    >
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: config?.color || '#6b7280' }}
                          />
                          <span className="font-medium text-gray-900">{route.name}</span>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-gray-600">{config?.label || route.route_type}</td>
                      <td className="py-3 px-3 text-gray-600">{floor?.name || 'All Floors'}</td>
                      <td className="py-3 px-3 text-right text-gray-600">{route.capacity || '-'}</td>
                      <td className="py-3 px-3 text-right text-gray-600">
                        {route.estimated_time_seconds
                          ? `${Math.ceil(route.estimated_time_seconds / 60)} min`
                          : '-'}
                      </td>
                      <td className="py-3 px-3 text-center">
                        <Badge variant={route.is_active ? 'success' : 'secondary'} size="sm">
                          {route.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </td>
                      <td className="py-3 px-3">
                        <button
                          className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRouteTableClick(route);
                          }}
                        >
                          Show on Map
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <svg className="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
            <p>No evacuation routes defined</p>
          </div>
        )}
      </CollapsibleSection>

      {/* Checkpoints Summary */}
      <CollapsibleSection
        title="Emergency Checkpoints Summary"
        icon="\u{1F4CD}"
        defaultOpen={false}
        badge={
          <Badge variant="info" size="sm">
            {plan.checkpoints.filter(c => c.is_active).length}
          </Badge>
        }
      >
        {plan.checkpoints.length > 0 ? (
          <div className="space-y-4">
            {/* Group by type */}
            {Object.entries(
              plan.checkpoints.reduce((acc, cp) => {
                const type = cp.checkpoint_type;
                if (!acc[type]) acc[type] = [];
                acc[type].push(cp);
                return acc;
              }, {} as Record<string, EmergencyCheckpoint[]>)
            ).map(([type, checkpoints]) => {
              const config = checkpointTypeConfig[type as CheckpointType];
              return (
                <div key={type}>
                  <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
                    <span
                      className={cn(
                        'w-6 h-6 rounded-full flex items-center justify-center text-white text-xs',
                        config?.color || 'bg-gray-500'
                      )}
                    >
                      {config?.icon || '\u{1F4CD}'}
                    </span>
                    {config?.label || type}
                    <Badge variant="secondary" size="sm">{checkpoints.length}</Badge>
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {checkpoints.map((checkpoint) => {
                      const floor = floorPlans.find(fp => fp.id === checkpoint.floor_plan_id);
                      return (
                        <div
                          key={checkpoint.id}
                          className={cn(
                            'bg-gray-50 rounded-lg p-3 border border-gray-100',
                            !checkpoint.is_active && 'opacity-60'
                          )}
                        >
                          <div className="flex items-start justify-between">
                            <div>
                              <h5 className="font-medium text-gray-900">{checkpoint.name}</h5>
                              <p className="text-xs text-gray-500">{floor?.name || 'Location not set'}</p>
                            </div>
                            {!checkpoint.is_active && (
                              <Badge variant="secondary" size="sm">Inactive</Badge>
                            )}
                          </div>
                          <div className="mt-2 space-y-1 text-xs text-gray-600">
                            {checkpoint.capacity && (
                              <p>Capacity: {checkpoint.capacity} people</p>
                            )}
                            {checkpoint.responsible_person && (
                              <p>Responsible: {checkpoint.responsible_person}</p>
                            )}
                            {checkpoint.contact_info?.phone && (
                              <p>Phone: {checkpoint.contact_info.phone}</p>
                            )}
                            {checkpoint.contact_info?.radio_channel && (
                              <p>Radio: {checkpoint.contact_info.radio_channel}</p>
                            )}
                          </div>
                          {checkpoint.instructions && (
                            <p className="mt-2 text-xs text-gray-500 italic">
                              {checkpoint.instructions}
                            </p>
                          )}
                          {checkpoint.equipment && checkpoint.equipment.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {checkpoint.equipment.map((eq, idx) => (
                                <span
                                  key={idx}
                                  className="text-xs bg-white border border-gray-200 px-1.5 py-0.5 rounded"
                                >
                                  {eq.name} x{eq.quantity}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <svg className="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <p>No checkpoints defined</p>
          </div>
        )}
      </CollapsibleSection>

      {/* Print Styles */}
      <style>{`
        @media print {
          .print-container {
            font-size: 12px;
          }
          .page-break-inside-avoid {
            page-break-inside: avoid;
          }
          @page {
            margin: 1cm;
          }
        }
      `}</style>
    </div>
  );
}

export default EmergencyPlanViewer;
