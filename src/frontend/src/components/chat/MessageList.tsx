/**
 * MessageList Component
 * Displays messages in a channel with infinite scroll
 */

import { useEffect, useRef, useCallback } from 'react';
import { useMessageStore, Message } from '../../stores/messageStore';
import { useAuthStore } from '../../stores/authStore';
import { cn } from '../../utils';
import { Spinner } from '../ui';

interface MessageListProps {
  channelId: string;
}

export function MessageList({ channelId }: MessageListProps) {
  const { messages, isLoading, typingUsers, fetchMessages } = useMessageStore();
  const { user } = useAuthStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const prevMessagesLength = useRef(0);

  const channelMessages = messages[channelId] || [];
  const typing = typingUsers[channelId] || [];

  useEffect(() => {
    fetchMessages(channelId);
  }, [channelId, fetchMessages]);

  // Scroll to bottom on new messages
  useEffect(() => {
    if (channelMessages.length > prevMessagesLength.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
    prevMessagesLength.current = channelMessages.length;
  }, [channelMessages.length]);

  // Load more messages when scrolling to top
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    const { scrollTop } = containerRef.current;

    if (scrollTop === 0 && channelMessages.length > 0 && !isLoading) {
      const oldestMessage = channelMessages[0];
      fetchMessages(channelId, { before: oldestMessage.created_at, limit: 50 });
    }
  }, [channelId, channelMessages, isLoading, fetchMessages]);

  // Group messages by date
  const groupedMessages = groupMessagesByDate(channelMessages);

  if (isLoading && channelMessages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto p-4 space-y-4"
      onScroll={handleScroll}
    >
      {isLoading && channelMessages.length > 0 && (
        <div className="flex justify-center py-2">
          <Spinner size="sm" />
        </div>
      )}

      {Object.entries(groupedMessages).map(([date, msgs]) => (
        <div key={date}>
          {/* Date separator */}
          <div className="flex items-center gap-3 my-4">
            <div className="flex-1 h-px bg-gray-200" />
            <span className="text-xs text-gray-400 font-medium">{date}</span>
            <div className="flex-1 h-px bg-gray-200" />
          </div>

          {/* Messages */}
          <div className="space-y-3">
            {msgs.map((message, idx) => {
              const prevMessage = idx > 0 ? msgs[idx - 1] : null;
              const showAvatar = !prevMessage ||
                prevMessage.sender_id !== message.sender_id ||
                new Date(message.created_at).getTime() - new Date(prevMessage.created_at).getTime() > 60000;

              return (
                <MessageItem
                  key={message.id}
                  message={message}
                  isOwn={message.sender_id === user?.id}
                  showAvatar={showAvatar}
                />
              );
            })}
          </div>
        </div>
      ))}

      {channelMessages.length === 0 && (
        <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
          <svg className="w-12 h-12 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <p>No messages yet</p>
          <p className="text-sm">Start the conversation!</p>
        </div>
      )}

      {/* Typing indicator */}
      {typing.length > 0 && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
          <span>
            {typing.length === 1
              ? `${typing[0]} is typing...`
              : `${typing.slice(0, -1).join(', ')} and ${typing[typing.length - 1]} are typing...`}
          </span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}

interface MessageItemProps {
  message: Message;
  isOwn: boolean;
  showAvatar: boolean;
}

function MessageItem({ message, isOwn, showAvatar }: MessageItemProps) {
  const formatTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // System message
  if (message.message_type === 'system') {
    return (
      <div className="flex justify-center">
        <span className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">
          {message.content}
        </span>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex gap-3',
        isOwn ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      {showAvatar ? (
        <div
          className={cn(
            'w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium flex-shrink-0',
            isOwn ? 'bg-blue-500' : 'bg-gray-400'
          )}
        >
          {message.sender?.full_name?.charAt(0).toUpperCase() || '?'}
        </div>
      ) : (
        <div className="w-8 flex-shrink-0" />
      )}

      {/* Message bubble */}
      <div
        className={cn(
          'max-w-[70%] rounded-lg px-3 py-2',
          isOwn
            ? 'bg-blue-500 text-white'
            : 'bg-white border border-gray-200 text-gray-900'
        )}
      >
        {/* Sender name */}
        {showAvatar && !isOwn && (
          <div className="text-xs font-medium text-gray-500 mb-1">
            {message.sender?.full_name || 'Unknown'}
          </div>
        )}

        {/* Content */}
        <div className="text-sm whitespace-pre-wrap break-words">
          {message.content}
        </div>

        {/* Location */}
        {message.message_type === 'location' && message.location_lat && message.location_lng && (
          <div className="mt-2 p-2 bg-gray-100 rounded text-gray-700 text-xs">
            📍 {message.location_address || `${message.location_lat.toFixed(4)}, ${message.location_lng.toFixed(4)}`}
          </div>
        )}

        {/* Attachment */}
        {message.attachment_url && (
          <div className="mt-2">
            {message.message_type === 'image' ? (
              <img
                src={message.attachment_url}
                alt={message.attachment_name || 'Image'}
                className="max-w-full rounded"
              />
            ) : (
              <a
                href={message.attachment_url}
                target="_blank"
                rel="noopener noreferrer"
                className={cn(
                  'flex items-center gap-2 p-2 rounded text-sm',
                  isOwn ? 'bg-blue-600' : 'bg-gray-100'
                )}
              >
                📎 {message.attachment_name || 'Download'}
                {message.attachment_size && (
                  <span className="text-xs opacity-75">
                    ({formatFileSize(message.attachment_size)})
                  </span>
                )}
              </a>
            )}
          </div>
        )}

        {/* Meta info */}
        <div
          className={cn(
            'flex items-center gap-2 mt-1 text-xs',
            isOwn ? 'text-blue-100' : 'text-gray-400'
          )}
        >
          <span>{formatTime(message.created_at)}</span>
          {message.is_edited && <span>(edited)</span>}
          {message.priority === 'urgent' && (
            <span className="px-1 py-0.5 bg-red-500 text-white rounded text-xs">
              URGENT
            </span>
          )}
          {message.priority === 'high' && (
            <span className="px-1 py-0.5 bg-orange-500 text-white rounded text-xs">
              HIGH
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// Helper functions
function groupMessagesByDate(messages: Message[]): Record<string, Message[]> {
  const grouped: Record<string, Message[]> = {};

  messages.forEach((message) => {
    const date = new Date(message.created_at);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    let dateKey: string;
    if (date.toDateString() === today.toDateString()) {
      dateKey = 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
      dateKey = 'Yesterday';
    } else {
      dateKey = date.toLocaleDateString(undefined, {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
      });
    }

    if (!grouped[dateKey]) {
      grouped[dateKey] = [];
    }
    grouped[dateKey].push(message);
  });

  return grouped;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default MessageList;
