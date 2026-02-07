/**
 * DeviceStatusIndicator Component
 *
 * Displays device online/offline status badge with colored dot,
 * last-seen relative time, and config sync pending warning.
 */
import { formatDistanceToNow } from 'date-fns';
import type { DeviceStatus } from '../../types';

interface DeviceStatusIndicatorProps {
  status: DeviceStatus;
  lastSeen: string | null;
  isSynced: boolean;
  className?: string;
  size?: 'sm' | 'md';
}

export function DeviceStatusIndicator({
  status,
  lastSeen,
  isSynced,
  className = '',
  size = 'md',
}: DeviceStatusIndicatorProps) {
  // Status dot colors
  const dotColorClass = {
    online: 'bg-green-500',
    offline: 'bg-gray-400',
    alert: 'bg-red-500 animate-pulse',
    maintenance: 'bg-yellow-500',
    error: 'bg-red-600',
  }[status];

  // Dot and text sizes
  const dotSizeClass = size === 'sm' ? 'w-2 h-2' : 'w-3 h-3';
  const textSizeClass = size === 'sm' ? 'text-xs' : 'text-sm';

  // Status text (capitalize first letter)
  const statusText = status.charAt(0).toUpperCase() + status.slice(1);

  // Last seen text
  let lastSeenText = '';
  if (lastSeen) {
    try {
      lastSeenText = `Last seen ${formatDistanceToNow(new Date(lastSeen), { addSuffix: true })}`;
    } catch {
      lastSeenText = 'Last seen unknown';
    }
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className={`rounded-full ${dotSizeClass} ${dotColorClass} flex-shrink-0`} />
      <div className="flex flex-col">
        <span className={`font-medium ${textSizeClass}`}>{statusText}</span>
        {lastSeen && (
          <span className={`text-gray-500 ${size === 'sm' ? 'text-xs' : 'text-xs'}`}>
            {lastSeenText}
          </span>
        )}
        {!isSynced && status === 'online' && (
          <span className={`text-orange-500 ${size === 'sm' ? 'text-xs' : 'text-xs'}`}>
            Config sync pending
          </span>
        )}
      </div>
    </div>
  );
}

export default DeviceStatusIndicator;
