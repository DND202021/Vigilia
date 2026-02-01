/**
 * Channel Store
 * Zustand store for managing communication channels
 */

import { create } from 'zustand';
import api from '../services/api';

export type ChannelType = 'direct' | 'incident' | 'team' | 'broadcast';

export interface ChannelMember {
  id: string;
  user_id: string;
  user_name: string;
  user_email: string;
  is_admin: boolean;
  is_muted: boolean;
  unread_count: number;
  joined_at: string;
}

export interface Channel {
  id: string;
  name: string;
  description?: string;
  channel_type: ChannelType;
  agency_id?: string;
  incident_id?: string;
  is_archived: boolean;
  is_private: boolean;
  last_message_at?: string;
  message_count: number;
  created_at: string;
  members: ChannelMember[];
}

export interface ChannelListItem {
  id: string;
  name: string;
  channel_type: ChannelType;
  is_private: boolean;
  last_message_at?: string;
  unread_count: number;
}

interface ChannelState {
  channels: ChannelListItem[];
  currentChannel: Channel | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchChannels: (type?: ChannelType) => Promise<void>;
  fetchChannel: (channelId: string) => Promise<void>;
  createChannel: (data: {
    name: string;
    description?: string;
    channel_type?: ChannelType;
    is_private?: boolean;
    member_ids?: string[];
  }) => Promise<Channel>;
  createDirectChannel: (userId: string) => Promise<Channel>;
  updateChannel: (channelId: string, data: {
    name?: string;
    description?: string;
    is_archived?: boolean;
  }) => Promise<void>;
  deleteChannel: (channelId: string) => Promise<void>;
  addMember: (channelId: string, userId: string, isAdmin?: boolean) => Promise<void>;
  removeMember: (channelId: string, userId: string) => Promise<void>;
  leaveChannel: (channelId: string) => Promise<void>;
  muteChannel: (channelId: string, muted: boolean) => Promise<void>;
  setCurrentChannel: (channel: Channel | null) => void;
  updateUnreadCount: (channelId: string, count: number) => void;
  handleNewMessage: (channelId: string) => void;
  clearError: () => void;
}

export const useChannelStore = create<ChannelState>((set, get) => ({
  channels: [],
  currentChannel: null,
  isLoading: false,
  error: null,

  fetchChannels: async (type?: ChannelType) => {
    set({ isLoading: true, error: null });
    try {
      const params = type ? `?channel_type=${type}` : '';
      const response = await api.get<ChannelListItem[]>(`/channels${params}`);
      set({ channels: response.data, isLoading: false });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to fetch channels',
        isLoading: false,
      });
    }
  },

  fetchChannel: async (channelId: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get<Channel>(`/channels/${channelId}`);
      set({ currentChannel: response.data, isLoading: false });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to fetch channel',
        isLoading: false,
      });
    }
  },

  createChannel: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post<Channel>('/channels', data);
      const newChannel: ChannelListItem = {
        id: response.data.id,
        name: response.data.name,
        channel_type: response.data.channel_type,
        is_private: response.data.is_private,
        last_message_at: response.data.last_message_at,
        unread_count: 0,
      };
      set((state) => ({
        channels: [newChannel, ...state.channels],
        isLoading: false,
      }));
      return response.data;
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to create channel',
        isLoading: false,
      });
      throw error;
    }
  },

  createDirectChannel: async (userId: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post<Channel>('/channels/direct', { user_id: userId });
      // Check if channel already exists in list
      const exists = get().channels.find(c => c.id === response.data.id);
      if (!exists) {
        const newChannel: ChannelListItem = {
          id: response.data.id,
          name: response.data.name,
          channel_type: response.data.channel_type,
          is_private: response.data.is_private,
          last_message_at: response.data.last_message_at,
          unread_count: 0,
        };
        set((state) => ({
          channels: [newChannel, ...state.channels],
        }));
      }
      set({ isLoading: false });
      return response.data;
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to create direct channel',
        isLoading: false,
      });
      throw error;
    }
  },

  updateChannel: async (channelId: string, data) => {
    try {
      const response = await api.patch<Channel>(`/channels/${channelId}`, data);
      set((state) => ({
        channels: state.channels.map((c) =>
          c.id === channelId ? { ...c, name: response.data.name } : c
        ),
        currentChannel:
          state.currentChannel?.id === channelId ? response.data : state.currentChannel,
      }));
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to update channel' });
      throw error;
    }
  },

  deleteChannel: async (channelId: string) => {
    try {
      await api.delete(`/channels/${channelId}`);
      set((state) => ({
        channels: state.channels.filter((c) => c.id !== channelId),
        currentChannel: state.currentChannel?.id === channelId ? null : state.currentChannel,
      }));
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to delete channel' });
      throw error;
    }
  },

  addMember: async (channelId: string, userId: string, isAdmin = false) => {
    try {
      await api.post(`/channels/${channelId}/members`, { user_id: userId, is_admin: isAdmin });
      // Refresh channel to get updated members
      await get().fetchChannel(channelId);
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to add member' });
      throw error;
    }
  },

  removeMember: async (channelId: string, userId: string) => {
    try {
      await api.delete(`/channels/${channelId}/members/${userId}`);
      // Refresh channel to get updated members
      await get().fetchChannel(channelId);
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to remove member' });
      throw error;
    }
  },

  leaveChannel: async (channelId: string) => {
    try {
      await api.post(`/channels/${channelId}/leave`);
      set((state) => ({
        channels: state.channels.filter((c) => c.id !== channelId),
        currentChannel: state.currentChannel?.id === channelId ? null : state.currentChannel,
      }));
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to leave channel' });
      throw error;
    }
  },

  muteChannel: async (channelId: string, muted: boolean) => {
    try {
      await api.post(`/channels/${channelId}/mute?muted=${muted}`);
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to mute channel' });
      throw error;
    }
  },

  setCurrentChannel: (channel: Channel | null) => {
    set({ currentChannel: channel });
  },

  updateUnreadCount: (channelId: string, count: number) => {
    set((state) => ({
      channels: state.channels.map((c) =>
        c.id === channelId ? { ...c, unread_count: count } : c
      ),
    }));
  },

  handleNewMessage: (channelId: string) => {
    const { currentChannel } = get();
    // Only increment if not in the channel
    if (currentChannel?.id !== channelId) {
      set((state) => ({
        channels: state.channels.map((c) =>
          c.id === channelId
            ? { ...c, unread_count: c.unread_count + 1, last_message_at: new Date().toISOString() }
            : c
        ),
      }));
    }
  },

  clearError: () => set({ error: null }),
}));
