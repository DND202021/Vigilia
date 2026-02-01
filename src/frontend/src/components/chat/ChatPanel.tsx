/**
 * ChatPanel Component
 * Main chat interface combining channel list and message view
 */

import { useState, useEffect, useCallback } from 'react';
import { useChannelStore } from '../../stores/channelStore';
import { useMessageStore } from '../../stores/messageStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import { ChannelList } from './ChannelList';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { cn } from '../../utils';
import { Button } from '../ui';

interface ChatPanelProps {
  className?: string;
  defaultChannelId?: string;
  compact?: boolean;
}

export function ChatPanel({ className, defaultChannelId, compact = false }: ChatPanelProps) {
  const [selectedChannelId, setSelectedChannelId] = useState<string | undefined>(defaultChannelId);
  const [showChannelList, setShowChannelList] = useState(!compact);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const { currentChannel, fetchChannel, setCurrentChannel } = useChannelStore();
  const { markAsRead } = useMessageStore();
  const { isConnected } = useWebSocket();

  // Fetch channel details when selected
  useEffect(() => {
    if (selectedChannelId) {
      fetchChannel(selectedChannelId);
    } else {
      setCurrentChannel(null);
    }
  }, [selectedChannelId, fetchChannel, setCurrentChannel]);

  // Mark as read when viewing channel
  useEffect(() => {
    if (selectedChannelId) {
      markAsRead(selectedChannelId);
    }
  }, [selectedChannelId, markAsRead]);

  // TODO: Add WebSocket channel room management when useWebSocket is extended
  // For now, messages are fetched via API and won't update in real-time

  // Typing indicator handlers (no-op for now without WebSocket)
  const handleTypingStart = useCallback(() => {
    // TODO: Implement when WebSocket channel methods are added
  }, []);

  const handleTypingStop = useCallback(() => {
    // TODO: Implement when WebSocket channel methods are added
  }, []);

  const handleSelectChannel = (channelId: string) => {
    setSelectedChannelId(channelId);
    if (compact) {
      setShowChannelList(false);
    }
  };

  return (
    <div className={cn('flex h-full bg-gray-100', className)}>
      {/* Channel list sidebar */}
      {showChannelList && (
        <div className={cn(
          'flex-shrink-0 border-r bg-white',
          compact ? 'absolute inset-0 z-10' : 'w-72'
        )}>
          <ChannelList
            selectedChannelId={selectedChannelId}
            onSelectChannel={handleSelectChannel}
            onCreateChannel={() => setShowCreateModal(true)}
          />
        </div>
      )}

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="h-14 border-b bg-white flex items-center px-4 gap-3">
          {compact && !showChannelList && (
            <button
              onClick={() => setShowChannelList(true)}
              className="p-1 -ml-1 text-gray-500 hover:text-gray-700"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          )}

          {currentChannel ? (
            <>
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-gray-900 truncate">
                  {currentChannel.name}
                </h3>
                {currentChannel.description && (
                  <p className="text-xs text-gray-500 truncate">
                    {currentChannel.description}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <span>{currentChannel.members?.length || 0} members</span>
                {!isConnected && (
                  <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs">
                    Offline
                  </span>
                )}
              </div>
            </>
          ) : (
            <span className="text-gray-500">Select a channel</span>
          )}
        </div>

        {/* Messages */}
        {selectedChannelId ? (
          <>
            <MessageList channelId={selectedChannelId} />
            <MessageInput
              channelId={selectedChannelId}
              onTypingStart={handleTypingStart}
              onTypingStop={handleTypingStop}
            />
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
            <svg className="w-16 h-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p className="text-lg font-medium">Welcome to Messages</p>
            <p className="text-sm">Select a channel to start chatting</p>
          </div>
        )}
      </div>

      {/* Create channel modal (placeholder) */}
      {showCreateModal && (
        <CreateChannelModal onClose={() => setShowCreateModal(false)} />
      )}
    </div>
  );
}

// Simple create channel modal
function CreateChannelModal({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isPrivate, setIsPrivate] = useState(false);
  const { createChannel, isLoading } = useChannelStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      await createChannel({
        name: name.trim(),
        description: description.trim() || undefined,
        channel_type: 'team',
        is_private: isPrivate,
      });
      onClose();
    } catch (error) {
      console.error('Failed to create channel:', error);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-semibold mb-4">Create Channel</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Channel Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Operations Team"
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description (optional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this channel about?"
              rows={2}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={isPrivate}
              onChange={(e) => setIsPrivate(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm text-gray-700">Make private</span>
          </label>
          <div className="flex gap-2 justify-end pt-2">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={!name.trim() || isLoading}>
              {isLoading ? 'Creating...' : 'Create'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ChatPanel;
