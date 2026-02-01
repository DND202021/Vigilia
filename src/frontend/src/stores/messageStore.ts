/**
 * Message Store
 * Zustand store for managing messages in communication channels
 */

import { create } from 'zustand';
import api from '../services/api';

export type MessageType = 'text' | 'file' | 'image' | 'location' | 'system';
export type MessagePriority = 'normal' | 'high' | 'urgent';

export interface MessageSender {
  id: string;
  full_name: string;
  email: string;
}

export interface Message {
  id: string;
  channel_id: string;
  sender_id?: string;
  sender?: MessageSender;
  message_type: MessageType;
  content: string;
  priority: MessagePriority;
  attachment_url?: string;
  attachment_name?: string;
  attachment_size?: number;
  attachment_mime_type?: string;
  location_lat?: number;
  location_lng?: number;
  location_address?: string;
  reply_to_id?: string;
  is_edited: boolean;
  edited_at?: string;
  read_by?: string[];
  created_at: string;
}

export interface UnreadCount {
  total: number;
  by_channel: Record<string, number>;
}

interface MessageState {
  messages: Record<string, Message[]>; // Keyed by channel_id
  unreadCount: UnreadCount;
  isLoading: boolean;
  isSending: boolean;
  error: string | null;
  typingUsers: Record<string, string[]>; // channel_id -> user names

  // Actions
  fetchMessages: (channelId: string, options?: {
    limit?: number;
    before?: string;
    after?: string;
  }) => Promise<void>;
  sendMessage: (channelId: string, data: {
    content: string;
    message_type?: MessageType;
    priority?: MessagePriority;
    reply_to_id?: string;
    location_lat?: number;
    location_lng?: number;
    location_address?: string;
  }) => Promise<Message>;
  editMessage: (messageId: string, content: string) => Promise<void>;
  deleteMessage: (messageId: string) => Promise<void>;
  markAsRead: (channelId: string, messageId?: string) => Promise<void>;
  fetchUnreadCount: () => Promise<void>;
  searchMessages: (query: string, channelId?: string) => Promise<Message[]>;
  addReaction: (messageId: string, emoji: string) => Promise<void>;
  removeReaction: (messageId: string, emoji: string) => Promise<void>;

  // Real-time handlers
  handleNewMessage: (channelId: string, message: Message) => void;
  handleMessageEdited: (channelId: string, messageId: string, content: string, editedAt: string) => void;
  handleMessageDeleted: (channelId: string, messageId: string) => void;
  setTypingUser: (channelId: string, userName: string, isTyping: boolean) => void;

  clearMessages: (channelId?: string) => void;
  clearError: () => void;
}

export const useMessageStore = create<MessageState>((set, get) => ({
  messages: {},
  unreadCount: { total: 0, by_channel: {} },
  isLoading: false,
  isSending: false,
  error: null,
  typingUsers: {},

  fetchMessages: async (channelId: string, options = {}) => {
    set({ isLoading: true, error: null });
    try {
      const params = new URLSearchParams();
      if (options.limit) params.set('limit', options.limit.toString());
      if (options.before) params.set('before', options.before);
      if (options.after) params.set('after', options.after);

      const queryString = params.toString();
      const url = `/messages/channel/${channelId}${queryString ? `?${queryString}` : ''}`;
      const response = await api.get<Message[]>(url);

      set((state) => ({
        messages: {
          ...state.messages,
          [channelId]: options.before
            ? [...response.data, ...(state.messages[channelId] || [])]
            : response.data,
        },
        isLoading: false,
      }));
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to fetch messages',
        isLoading: false,
      });
    }
  },

  sendMessage: async (channelId: string, data) => {
    set({ isSending: true, error: null });
    try {
      const response = await api.post<Message>(`/messages/channel/${channelId}`, data);
      set((state) => ({
        messages: {
          ...state.messages,
          [channelId]: [...(state.messages[channelId] || []), response.data],
        },
        isSending: false,
      }));
      return response.data;
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to send message',
        isSending: false,
      });
      throw error;
    }
  },

  editMessage: async (messageId: string, content: string) => {
    try {
      const response = await api.patch<Message>(`/messages/${messageId}`, { content });
      const message = response.data;
      set((state) => ({
        messages: {
          ...state.messages,
          [message.channel_id]: state.messages[message.channel_id]?.map((m) =>
            m.id === messageId ? { ...m, content, is_edited: true, edited_at: message.edited_at } : m
          ) || [],
        },
      }));
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to edit message' });
      throw error;
    }
  },

  deleteMessage: async (messageId: string) => {
    try {
      // Find the message first to get channel_id
      let channelId: string | null = null;
      const { messages } = get();
      for (const [cId, msgs] of Object.entries(messages)) {
        if (msgs.find((m) => m.id === messageId)) {
          channelId = cId;
          break;
        }
      }

      await api.delete(`/messages/${messageId}`);

      if (channelId) {
        set((state) => ({
          messages: {
            ...state.messages,
            [channelId!]: state.messages[channelId!]?.filter((m) => m.id !== messageId) || [],
          },
        }));
      }
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to delete message' });
      throw error;
    }
  },

  markAsRead: async (channelId: string, messageId?: string) => {
    try {
      const params = messageId ? `?message_id=${messageId}` : '';
      await api.post(`/messages/channel/${channelId}/read${params}`);
      // Update unread count
      set((state) => ({
        unreadCount: {
          ...state.unreadCount,
          total: Math.max(0, state.unreadCount.total - (state.unreadCount.by_channel[channelId] || 0)),
          by_channel: {
            ...state.unreadCount.by_channel,
            [channelId]: 0,
          },
        },
      }));
    } catch (error: any) {
      console.error('Failed to mark as read:', error);
    }
  },

  fetchUnreadCount: async () => {
    try {
      const response = await api.get<UnreadCount>('/messages/unread/count');
      set({ unreadCount: response.data });
    } catch (error: any) {
      console.error('Failed to fetch unread count:', error);
    }
  },

  searchMessages: async (query: string, channelId?: string) => {
    try {
      const params = new URLSearchParams({ query });
      if (channelId) params.set('channel_id', channelId);
      const response = await api.get<Message[]>(`/messages/search?${params}`);
      return response.data;
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to search messages' });
      return [];
    }
  },

  addReaction: async (messageId: string, emoji: string) => {
    try {
      await api.post(`/messages/${messageId}/reactions`, { emoji });
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to add reaction' });
      throw error;
    }
  },

  removeReaction: async (messageId: string, emoji: string) => {
    try {
      await api.delete(`/messages/${messageId}/reactions/${encodeURIComponent(emoji)}`);
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to remove reaction' });
      throw error;
    }
  },

  // Real-time handlers
  handleNewMessage: (channelId: string, message: Message) => {
    set((state) => ({
      messages: {
        ...state.messages,
        [channelId]: [...(state.messages[channelId] || []), message],
      },
    }));
  },

  handleMessageEdited: (channelId: string, messageId: string, content: string, editedAt: string) => {
    set((state) => ({
      messages: {
        ...state.messages,
        [channelId]: state.messages[channelId]?.map((m) =>
          m.id === messageId ? { ...m, content, is_edited: true, edited_at: editedAt } : m
        ) || [],
      },
    }));
  },

  handleMessageDeleted: (channelId: string, messageId: string) => {
    set((state) => ({
      messages: {
        ...state.messages,
        [channelId]: state.messages[channelId]?.filter((m) => m.id !== messageId) || [],
      },
    }));
  },

  setTypingUser: (channelId: string, userName: string, isTyping: boolean) => {
    set((state) => {
      const current = state.typingUsers[channelId] || [];
      const updated = isTyping
        ? current.includes(userName) ? current : [...current, userName]
        : current.filter((n) => n !== userName);

      return {
        typingUsers: {
          ...state.typingUsers,
          [channelId]: updated,
        },
      };
    });
  },

  clearMessages: (channelId?: string) => {
    if (channelId) {
      set((state) => ({
        messages: {
          ...state.messages,
          [channelId]: [],
        },
      }));
    } else {
      set({ messages: {} });
    }
  },

  clearError: () => set({ error: null }),
}));
