/**
 * DeviceHistoryList - Displays device status change history.
 *
 * Shows a timeline view of status changes for a device with colored badges,
 * timestamps, reasons, and connection quality information.
 */

import { useState, useEffect, useCallback } from 'react';
import type { DeviceStatusHistory } from '../../types';
import { iotDevicesApi } from '../../services/api';

interface DeviceHistoryListProps {
  deviceId: string;
  maxItems?: number;
  onLoadMore?: () => void;
  className?: string;
}

/**
 * Get the color class for a status badge.
 */
function getStatusColor(status: string): string {
  switch (status) {
    case 'online':
      return 'bg-green-100 text-green-800 border-green-200';
    case 'offline':
      return 'bg-gray-100 text-gray-800 border-gray-200';
    case 'alert':
      return 'bg-red-100 text-red-800 border-red-200';
    case 'maintenance':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case 'error':
      return 'bg-orange-100 text-orange-800 border-orange-200';
    default:
      return 'bg-gray-100 text-gray-600 border-gray-200';
  }
}

/**
 * Get the timeline dot color for a status.
 */
function getTimelineDotColor(status: string): string {
  switch (status) {
    case 'online':
      return 'bg-green-500';
    case 'offline':
      return 'bg-gray-400';
    case 'alert':
      return 'bg-red-500';
    case 'maintenance':
      return 'bg-yellow-500';
    case 'error':
      return 'bg-orange-500';
    default:
      return 'bg-gray-400';
  }
}

/**
 * Format a date string to relative time.
 */
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) {
    return 'Just now';
  } else if (diffMin < 60) {
    return `${diffMin} min ago`;
  } else if (diffHour < 24) {
    return `${diffHour} hr ago`;
  } else if (diffDay < 7) {
    return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
  } else {
    return date.toLocaleDateString();
  }
}

/**
 * Format a date string to full date/time.
 */
function formatFullDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Skeleton loader for loading state.
 */
function HistorySkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className="w-3 h-3 rounded-full bg-gray-200" />
            <div className="w-0.5 flex-1 bg-gray-200 mt-1" />
          </div>
          <div className="flex-1 pb-4">
            <div className="h-4 bg-gray-200 rounded w-32 mb-2" />
            <div className="h-3 bg-gray-200 rounded w-24 mb-2" />
            <div className="h-3 bg-gray-200 rounded w-48" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Status badge component.
 */
function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(
        status
      )}`}
    >
      {status}
    </span>
  );
}

export function DeviceHistoryList({
  deviceId,
  maxItems,
  onLoadMore,
  className = '',
}: DeviceHistoryListProps) {
  const [history, setHistory] = useState<DeviceStatusHistory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [totalItems, setTotalItems] = useState(0);

  const pageSize = maxItems || 10;

  const fetchHistory = useCallback(
    async (pageNum: number, append: boolean = false) => {
      try {
        setIsLoading(true);
        setError(null);

        const response = await iotDevicesApi.getHistory(deviceId, {
          page: pageNum,
          page_size: pageSize,
        });

        if (append) {
          setHistory((prev) => [...prev, ...response.items]);
        } else {
          setHistory(response.items);
        }

        setTotalItems(response.total);
        setHasMore(pageNum < response.total_pages);
      } catch (err) {
        setError('Failed to load status history');
        console.error('Error fetching device history:', err);
      } finally {
        setIsLoading(false);
      }
    },
    [deviceId, pageSize]
  );

  useEffect(() => {
    setPage(1);
    fetchHistory(1, false);
  }, [deviceId, fetchHistory]);

  const handleRefresh = () => {
    setPage(1);
    fetchHistory(1, false);
  };

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchHistory(nextPage, true);
    onLoadMore?.();
  };

  return (
    <div className={`bg-white border rounded-lg ${className}`}>
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">Status History</h3>
          {totalItems > 0 && (
            <p className="text-xs text-gray-500 mt-0.5">
              {totalItems} status change{totalItems !== 1 ? 's' : ''}
            </p>
          )}
        </div>
        <button
          onClick={handleRefresh}
          disabled={isLoading}
          className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors disabled:opacity-50"
          title="Refresh history"
        >
          <svg
            className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Loading state */}
        {isLoading && history.length === 0 && <HistorySkeleton />}

        {/* Error state */}
        {error && !isLoading && (
          <div className="text-center py-6">
            <div className="text-red-500 text-sm mb-2">{error}</div>
            <button
              onClick={handleRefresh}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Try again
            </button>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && history.length === 0 && (
          <div className="text-center py-8">
            <div className="text-gray-400 text-sm">No status changes recorded</div>
          </div>
        )}

        {/* Timeline view */}
        {history.length > 0 && (
          <div className="space-y-0">
            {history.map((entry, index) => (
              <div key={entry.id} className="flex gap-3">
                {/* Timeline connector */}
                <div className="flex flex-col items-center">
                  <div
                    className={`w-3 h-3 rounded-full flex-shrink-0 ${getTimelineDotColor(
                      entry.new_status
                    )}`}
                  />
                  {index < history.length - 1 && (
                    <div className="w-0.5 flex-1 bg-gray-200 mt-1" />
                  )}
                </div>

                {/* Entry content */}
                <div className="flex-1 pb-4 min-w-0">
                  {/* Status change */}
                  <div className="flex items-center gap-2 flex-wrap">
                    {entry.old_status && (
                      <>
                        <StatusBadge status={entry.old_status} />
                        <svg
                          className="w-4 h-4 text-gray-400 flex-shrink-0"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M14 5l7 7m0 0l-7 7m7-7H3"
                          />
                        </svg>
                      </>
                    )}
                    <StatusBadge status={entry.new_status} />
                  </div>

                  {/* Timestamp */}
                  <div
                    className="text-xs text-gray-500 mt-1 cursor-help"
                    title={formatFullDate(entry.changed_at)}
                  >
                    {formatRelativeTime(entry.changed_at)}
                  </div>

                  {/* Reason */}
                  {entry.reason && (
                    <div className="text-sm text-gray-600 mt-1">{entry.reason}</div>
                  )}

                  {/* Connection quality */}
                  {entry.connection_quality != null && (
                    <div className="flex items-center gap-1 mt-1">
                      <svg
                        className="w-3 h-3 text-gray-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.14 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0"
                        />
                      </svg>
                      <span className="text-xs text-gray-500">
                        {entry.connection_quality}% signal
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Load more button */}
        {hasMore && history.length > 0 && !isLoading && (
          <div className="text-center pt-2">
            <button
              onClick={handleLoadMore}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              Load more
            </button>
          </div>
        )}

        {/* Loading more indicator */}
        {isLoading && history.length > 0 && (
          <div className="text-center pt-2">
            <span className="text-sm text-gray-500">Loading...</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default DeviceHistoryList;
