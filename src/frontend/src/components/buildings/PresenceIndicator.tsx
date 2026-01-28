/**
 * PresenceIndicator Component
 *
 * Shows active users currently viewing/editing a floor plan.
 */

import { usePresenceStore } from '../../stores/presenceStore';
import type { UserPresence } from '../../types';
import { cn } from '../../utils';

interface PresenceIndicatorProps {
  floorPlanId: string;
  className?: string;
  maxVisible?: number;
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function getAvatarColor(userId: string): string {
  // Generate consistent color from user ID
  const colors = [
    'bg-blue-500',
    'bg-green-500',
    'bg-purple-500',
    'bg-orange-500',
    'bg-pink-500',
    'bg-cyan-500',
    'bg-indigo-500',
    'bg-teal-500',
  ];
  const hash = userId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colors[hash % colors.length];
}

function UserAvatar({ user, showTooltip = true }: { user: UserPresence; showTooltip?: boolean }) {
  return (
    <div className="relative group">
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-medium',
          'border-2 border-white shadow-sm',
          getAvatarColor(user.user_id)
        )}
        title={showTooltip ? `${user.user_name}${user.is_editing ? ' (editing)' : ''}` : undefined}
      >
        {getInitials(user.user_name)}
      </div>
      {user.is_editing && (
        <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 border-2 border-white rounded-full" />
      )}
      {showTooltip && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
          {user.user_name}
          {user.user_role && <span className="text-gray-400"> ({user.user_role})</span>}
          {user.is_editing && <span className="text-green-400 ml-1">Editing</span>}
        </div>
      )}
    </div>
  );
}

export function PresenceIndicator({ className, maxVisible = 3 }: PresenceIndicatorProps) {
  const { activeUsers } = usePresenceStore();

  if (activeUsers.length === 0) {
    return null;
  }

  const visibleUsers = activeUsers.slice(0, maxVisible);
  const hiddenCount = activeUsers.length - maxVisible;
  const editingCount = activeUsers.filter(u => u.is_editing).length;

  return (
    <div className={cn('flex items-center gap-1', className)}>
      {/* User avatars */}
      <div className="flex -space-x-2">
        {visibleUsers.map((user) => (
          <UserAvatar key={user.user_id} user={user} />
        ))}
        {hiddenCount > 0 && (
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center bg-gray-400 text-white text-xs font-medium border-2 border-white shadow-sm"
            title={`${hiddenCount} more user${hiddenCount > 1 ? 's' : ''}`}
          >
            +{hiddenCount}
          </div>
        )}
      </div>

      {/* Status text */}
      <div className="ml-2 text-xs text-gray-500">
        <span>{activeUsers.length} online</span>
        {editingCount > 0 && (
          <span className="text-green-600 ml-1">
            ({editingCount} editing)
          </span>
        )}
      </div>
    </div>
  );
}

export default PresenceIndicator;
