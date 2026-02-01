/**
 * ChannelList Component
 * Displays list of communication channels with unread indicators
 */

import { useEffect, useState } from 'react';
import { useChannelStore, ChannelListItem, ChannelType } from '../../stores/channelStore';
import { useMessageStore } from '../../stores/messageStore';
import { cn } from '../../utils';
import { Spinner } from '../ui';

interface ChannelListProps {
  selectedChannelId?: string;
  onSelectChannel: (channelId: string) => void;
  onCreateChannel?: () => void;
}

const channelTypeIcons: Record<ChannelType, string> = {
  direct: '💬',
  incident: '🚨',
  team: '👥',
  broadcast: '📢',
};

const channelTypeLabels: Record<ChannelType, string> = {
  direct: 'Direct Messages',
  incident: 'Incidents',
  team: 'Teams',
  broadcast: 'Broadcasts',
};

export function ChannelList({
  selectedChannelId,
  onSelectChannel,
  onCreateChannel,
}: ChannelListProps) {
  const { channels, isLoading, error, fetchChannels } = useChannelStore();
  const { unreadCount, fetchUnreadCount } = useMessageStore();
  const [filter, setFilter] = useState<ChannelType | 'all'>('all');

  useEffect(() => {
    fetchChannels();
    fetchUnreadCount();
  }, [fetchChannels, fetchUnreadCount]);

  const filteredChannels = filter === 'all'
    ? channels
    : channels.filter((c) => c.channel_type === filter);

  const groupedChannels = filteredChannels.reduce<Record<ChannelType, ChannelListItem[]>>(
    (acc, channel) => {
      const type = channel.channel_type;
      if (!acc[type]) acc[type] = [];
      acc[type].push(channel);
      return acc;
    },
    {} as Record<ChannelType, ChannelListItem[]>
  );

  if (isLoading && channels.length === 0) {
    return (
      <div className="flex items-center justify-center h-32">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="p-3 border-b bg-white">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-semibold text-gray-900">Messages</h2>
          {unreadCount.total > 0 && (
            <span className="px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700 rounded-full">
              {unreadCount.total}
            </span>
          )}
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1">
          <button
            onClick={() => setFilter('all')}
            className={cn(
              'px-2 py-1 text-xs rounded',
              filter === 'all'
                ? 'bg-blue-100 text-blue-700'
                : 'text-gray-600 hover:bg-gray-100'
            )}
          >
            All
          </button>
          {(['direct', 'incident', 'team'] as ChannelType[]).map((type) => (
            <button
              key={type}
              onClick={() => setFilter(type)}
              className={cn(
                'px-2 py-1 text-xs rounded',
                filter === type
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100'
              )}
            >
              {channelTypeIcons[type]}
            </button>
          ))}
        </div>
      </div>

      {/* Channel list */}
      <div className="flex-1 overflow-y-auto">
        {error && (
          <div className="p-3 text-sm text-red-600 bg-red-50">
            {error}
          </div>
        )}

        {Object.entries(groupedChannels).map(([type, typeChannels]) => (
          <div key={type} className="mb-2">
            <div className="px-3 py-2 text-xs font-medium text-gray-500 uppercase">
              {channelTypeLabels[type as ChannelType]}
            </div>
            {typeChannels.map((channel) => (
              <ChannelItem
                key={channel.id}
                channel={channel}
                isSelected={channel.id === selectedChannelId}
                onClick={() => onSelectChannel(channel.id)}
              />
            ))}
          </div>
        ))}

        {filteredChannels.length === 0 && !isLoading && (
          <div className="p-4 text-center text-gray-500 text-sm">
            No channels found
          </div>
        )}
      </div>

      {/* Create channel button */}
      {onCreateChannel && (
        <div className="p-3 border-t bg-white">
          <button
            onClick={onCreateChannel}
            className="w-full px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
          >
            + New Channel
          </button>
        </div>
      )}
    </div>
  );
}

interface ChannelItemProps {
  channel: ChannelListItem;
  isSelected: boolean;
  onClick: () => void;
}

function ChannelItem({ channel, isSelected, onClick }: ChannelItemProps) {
  const formatTime = (dateStr?: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (days === 1) {
      return 'Yesterday';
    } else if (days < 7) {
      return date.toLocaleDateString([], { weekday: 'short' });
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full px-3 py-2 flex items-center gap-3 text-left transition-colors',
        isSelected
          ? 'bg-blue-50 border-l-2 border-blue-500'
          : 'hover:bg-gray-100 border-l-2 border-transparent'
      )}
    >
      {/* Icon */}
      <div className="flex-shrink-0 text-lg">
        {channelTypeIcons[channel.channel_type]}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span
            className={cn(
              'font-medium truncate',
              channel.unread_count > 0 ? 'text-gray-900' : 'text-gray-700'
            )}
          >
            {channel.name}
          </span>
          {channel.last_message_at && (
            <span className="text-xs text-gray-400 flex-shrink-0">
              {formatTime(channel.last_message_at)}
            </span>
          )}
        </div>
        <div className="flex items-center justify-between mt-0.5">
          <span className="text-xs text-gray-400">
            {channel.is_private ? '🔒 Private' : ''}
          </span>
          {channel.unread_count > 0 && (
            <span className="px-1.5 py-0.5 text-xs font-medium bg-blue-500 text-white rounded-full min-w-[20px] text-center">
              {channel.unread_count > 99 ? '99+' : channel.unread_count}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

export default ChannelList;
