/**
 * MessageInput Component
 * Input field for composing and sending messages
 */

import { useState, useRef, useCallback } from 'react';
import { useMessageStore, MessagePriority } from '../../stores/messageStore';
import { cn } from '../../utils';
import { Button } from '../ui';

interface MessageInputProps {
  channelId: string;
  onTypingStart?: () => void;
  onTypingStop?: () => void;
}

export function MessageInput({
  channelId,
  onTypingStart,
  onTypingStop,
}: MessageInputProps) {
  const [content, setContent] = useState('');
  const [priority, setPriority] = useState<MessagePriority>('normal');
  const [showPriorityMenu, setShowPriorityMenu] = useState(false);
  const { sendMessage, isSending } = useMessageStore();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const typingTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  const handleSubmit = useCallback(async () => {
    if (!content.trim() || isSending) return;

    try {
      await sendMessage(channelId, {
        content: content.trim(),
        priority,
      });
      setContent('');
      setPriority('normal');
      textareaRef.current?.focus();
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  }, [content, priority, channelId, isSending, sendMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setContent(e.target.value);

      // Auto-resize textarea
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
      }

      // Typing indicator
      if (onTypingStart) {
        onTypingStart();
      }

      // Clear previous timeout
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }

      // Set new timeout to stop typing
      typingTimeoutRef.current = setTimeout(() => {
        if (onTypingStop) {
          onTypingStop();
        }
      }, 2000);
    },
    [onTypingStart, onTypingStop]
  );

  const priorityColors: Record<MessagePriority, string> = {
    normal: 'bg-gray-100 text-gray-700',
    high: 'bg-orange-100 text-orange-700',
    urgent: 'bg-red-100 text-red-700',
  };

  const priorityLabels: Record<MessagePriority, string> = {
    normal: 'Normal',
    high: 'High',
    urgent: 'Urgent',
  };

  return (
    <div className="border-t bg-white p-3">
      <div className="flex items-end gap-2">
        {/* Attachment button (placeholder) */}
        <button
          className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          title="Attach file"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
          </svg>
        </button>

        {/* Priority selector */}
        <div className="relative">
          <button
            onClick={() => setShowPriorityMenu(!showPriorityMenu)}
            className={cn(
              'p-2 rounded-lg transition-colors text-sm font-medium',
              priorityColors[priority]
            )}
            title="Set priority"
          >
            {priority === 'urgent' ? '🚨' : priority === 'high' ? '⚠️' : '💬'}
          </button>

          {showPriorityMenu && (
            <div className="absolute bottom-full left-0 mb-1 bg-white border rounded-lg shadow-lg py-1 z-10">
              {(['normal', 'high', 'urgent'] as MessagePriority[]).map((p) => (
                <button
                  key={p}
                  onClick={() => {
                    setPriority(p);
                    setShowPriorityMenu(false);
                  }}
                  className={cn(
                    'w-full px-3 py-1.5 text-left text-sm hover:bg-gray-50 flex items-center gap-2',
                    priority === p && 'bg-gray-50'
                  )}
                >
                  <span>{p === 'urgent' ? '🚨' : p === 'high' ? '⚠️' : '💬'}</span>
                  <span>{priorityLabels[p]}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Text input */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={content}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            rows={1}
            className="w-full px-3 py-2 border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            style={{ maxHeight: '150px' }}
            disabled={isSending}
          />
        </div>

        {/* Location button (placeholder) */}
        <button
          className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          title="Share location"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>

        {/* Send button */}
        <Button
          onClick={handleSubmit}
          disabled={!content.trim() || isSending}
          className="px-4"
        >
          {isSending ? (
            <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          )}
        </Button>
      </div>

      {/* Character count for long messages */}
      {content.length > 500 && (
        <div className="mt-1 text-xs text-gray-400 text-right">
          {content.length} / 10000
        </div>
      )}
    </div>
  );
}

export default MessageInput;
