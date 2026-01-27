/**
 * Alerts Floor Table - Sound anomaly alerts table with replay/download columns.
 *
 * Shows alerts for a given floor/building with:
 * - Created time, source device, type, occurrence, severity
 * - Audio replay button (inline AudioPlayer)
 * - Download button
 * - Assignee
 */

import { AudioPlayer } from '../audio/AudioPlayer';
import { audioClipsApi } from '../../services/api';
import type { SoundAlert } from '../../types';

interface AlertsFloorTableProps {
  alerts: SoundAlert[];
  isLoading?: boolean;
  onAssign?: (alertId: string) => void;
  className?: string;
}

function getSeverityBadge(severity: string) {
  const colors: Record<string, string> = {
    critical: 'bg-red-100 text-red-800 border-red-200',
    high: 'bg-orange-100 text-orange-800 border-orange-200',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    low: 'bg-blue-100 text-blue-800 border-blue-200',
    info: 'bg-gray-100 text-gray-800 border-gray-200',
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${colors[severity] || colors.info}`}>
      {severity}
    </span>
  );
}

function formatAlertType(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function AlertsFloorTable({
  alerts,
  isLoading = false,
  onAssign,
  className = '',
}: AlertsFloorTableProps) {
  const handleDownload = (clipId: string) => {
    const url = audioClipsApi.getDownloadUrl(clipId);
    window.open(url, '_blank');
  };

  if (isLoading) {
    return (
      <div className={`bg-white rounded-lg border p-8 text-center text-gray-500 ${className}`}>
        Loading alerts...
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className={`bg-white rounded-lg border p-8 text-center text-gray-400 ${className}`}>
        No alerts found for this view
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg border overflow-hidden ${className}`}>
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Occurrences</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Confidence</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Replay</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Download</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assignee</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {alerts.map((alert) => (
            <tr key={alert.id} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                {new Date(alert.created_at).toLocaleString()}
              </td>
              <td className="px-4 py-3 text-sm text-gray-700">
                {alert.source || 'Unknown'}
              </td>
              <td className="px-4 py-3 text-sm font-medium text-gray-800">
                {formatAlertType(alert.alert_type)}
              </td>
              <td className="px-4 py-3 text-sm text-gray-600">
                <span className="font-medium">{alert.occurrence_count || 1}</span>
                {alert.last_occurrence && (
                  <div className="text-xs text-gray-400">
                    Last: {new Date(alert.last_occurrence).toLocaleTimeString()}
                  </div>
                )}
              </td>
              <td className="px-4 py-3">
                {getSeverityBadge(alert.severity)}
              </td>
              <td className="px-4 py-3 text-sm text-gray-600">
                {alert.confidence != null ? `${Math.round(alert.confidence * 100)}%` : '—'}
              </td>
              <td className="px-4 py-3">
                {alert.audio_clip_id ? (
                  <AudioPlayer clipId={alert.audio_clip_id} compact />
                ) : (
                  <span className="text-xs text-gray-400">No clip</span>
                )}
              </td>
              <td className="px-4 py-3">
                {alert.audio_clip_id ? (
                  <button
                    onClick={() => handleDownload(alert.audio_clip_id!)}
                    className="text-blue-600 hover:text-blue-800 text-sm"
                    title="Download audio clip"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="7 10 12 15 17 10" />
                      <line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                  </button>
                ) : (
                  <span className="text-xs text-gray-400">—</span>
                )}
              </td>
              <td className="px-4 py-3 text-sm">
                {alert.assigned_to_id ? (
                  <span className="text-gray-700">Assigned</span>
                ) : (
                  <button
                    onClick={() => onAssign?.(alert.id)}
                    className="text-blue-600 hover:text-blue-800 text-xs"
                  >
                    Assign
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
