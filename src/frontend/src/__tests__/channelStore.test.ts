/**
 * Channel Store Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useChannelStore, type Channel, type ChannelListItem } from '../stores/channelStore';
import api from '../services/api';

// Mock API
vi.mock('../services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockChannelListItem: ChannelListItem = {
  id: 'chan-1',
  name: 'General',
  channel_type: 'team',
  is_private: false,
  unread_count: 0,
};

const mockChannel: Channel = {
  id: 'chan-1',
  name: 'General',
  description: 'General discussion',
  channel_type: 'team',
  agency_id: 'agency-1',
  is_archived: false,
  is_private: false,
  message_count: 10,
  created_at: new Date().toISOString(),
  members: [],
};

describe('useChannelStore', () => {
  beforeEach(() => {
    useChannelStore.setState({
      channels: [],
      currentChannel: null,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  describe('fetchChannels', () => {
    it('should fetch channels successfully', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [mockChannelListItem] });

      await useChannelStore.getState().fetchChannels();

      const state = useChannelStore.getState();
      expect(state.channels).toEqual([mockChannelListItem]);
      expect(state.isLoading).toBe(false);
      expect(api.get).toHaveBeenCalledWith('/channels');
    });

    it('should filter by channel type', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] });

      await useChannelStore.getState().fetchChannels('direct');

      expect(api.get).toHaveBeenCalledWith('/channels?channel_type=direct');
    });

    it('should handle fetch error', async () => {
      vi.mocked(api.get).mockRejectedValue({
        response: { data: { detail: 'Failed to fetch' } },
      });

      await useChannelStore.getState().fetchChannels();

      const state = useChannelStore.getState();
      expect(state.error).toBe('Failed to fetch');
    });
  });

  describe('fetchChannel', () => {
    it('should fetch single channel', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockChannel });

      await useChannelStore.getState().fetchChannel('chan-1');

      const state = useChannelStore.getState();
      expect(state.currentChannel).toEqual(mockChannel);
      expect(api.get).toHaveBeenCalledWith('/channels/chan-1');
    });

    it('should handle fetch error', async () => {
      vi.mocked(api.get).mockRejectedValue({
        response: { data: { detail: 'Not found' } },
      });

      await useChannelStore.getState().fetchChannel('chan-999');

      const state = useChannelStore.getState();
      expect(state.error).toBe('Not found');
    });
  });

  describe('createChannel', () => {
    it('should create channel and add to list', async () => {
      vi.mocked(api.post).mockResolvedValue({ data: mockChannel });

      const result = await useChannelStore.getState().createChannel({
        name: 'General',
        channel_type: 'team',
      });

      expect(result).toEqual(mockChannel);

      const state = useChannelStore.getState();
      expect(state.channels).toHaveLength(1);
      expect(state.channels[0].name).toBe('General');
    });

    it('should handle create error', async () => {
      vi.mocked(api.post).mockRejectedValue({
        response: { data: { detail: 'Invalid data' } },
      });

      await expect(
        useChannelStore.getState().createChannel({ name: 'Test' })
      ).rejects.toThrow();

      const state = useChannelStore.getState();
      expect(state.error).toBe('Invalid data');
    });
  });

  describe('createDirectChannel', () => {
    it('should create direct channel', async () => {
      const directChannel = { ...mockChannel, channel_type: 'direct' as const };
      vi.mocked(api.post).mockResolvedValue({ data: directChannel });

      const result = await useChannelStore.getState().createDirectChannel('user-2');

      expect(result).toEqual(directChannel);
      expect(api.post).toHaveBeenCalledWith('/channels/direct', { user_id: 'user-2' });
    });

    it('should not duplicate existing direct channel', async () => {
      const directChannel = { ...mockChannel, id: 'chan-existing', channel_type: 'direct' as const };

      useChannelStore.setState({
        channels: [{ ...mockChannelListItem, id: 'chan-existing' }],
      });

      vi.mocked(api.post).mockResolvedValue({ data: directChannel });

      await useChannelStore.getState().createDirectChannel('user-2');

      const state = useChannelStore.getState();
      expect(state.channels).toHaveLength(1); // Not duplicated
    });
  });

  describe('updateChannel', () => {
    it('should update channel in list', async () => {
      const updatedChannel = { ...mockChannel, name: 'Updated Name' };

      useChannelStore.setState({
        channels: [mockChannelListItem],
        currentChannel: mockChannel,
      });

      vi.mocked(api.patch).mockResolvedValue({ data: updatedChannel });

      await useChannelStore.getState().updateChannel('chan-1', { name: 'Updated Name' });

      const state = useChannelStore.getState();
      expect(state.channels[0].name).toBe('Updated Name');
      expect(state.currentChannel?.name).toBe('Updated Name');
    });
  });

  describe('deleteChannel', () => {
    it('should remove channel from list', async () => {
      useChannelStore.setState({
        channels: [mockChannelListItem],
        currentChannel: mockChannel,
      });

      vi.mocked(api.delete).mockResolvedValue({ data: {} });

      await useChannelStore.getState().deleteChannel('chan-1');

      const state = useChannelStore.getState();
      expect(state.channels).toHaveLength(0);
      expect(state.currentChannel).toBeNull();
    });
  });

  describe('member management', () => {
    it('should add member to channel', async () => {
      useChannelStore.setState({ currentChannel: mockChannel });

      vi.mocked(api.post).mockResolvedValue({ data: {} });
      vi.mocked(api.get).mockResolvedValue({ data: mockChannel });

      await useChannelStore.getState().addMember('chan-1', 'user-2', false);

      expect(api.post).toHaveBeenCalledWith('/channels/chan-1/members', {
        user_id: 'user-2',
        is_admin: false,
      });
      expect(api.get).toHaveBeenCalledWith('/channels/chan-1');
    });

    it('should remove member from channel', async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: {} });
      vi.mocked(api.get).mockResolvedValue({ data: mockChannel });

      await useChannelStore.getState().removeMember('chan-1', 'user-2');

      expect(api.delete).toHaveBeenCalledWith('/channels/chan-1/members/user-2');
    });

    it('should leave channel', async () => {
      useChannelStore.setState({
        channels: [mockChannelListItem],
        currentChannel: mockChannel,
      });

      vi.mocked(api.post).mockResolvedValue({ data: {} });

      await useChannelStore.getState().leaveChannel('chan-1');

      const state = useChannelStore.getState();
      expect(state.channels).toHaveLength(0);
      expect(state.currentChannel).toBeNull();
    });
  });

  describe('updateUnreadCount', () => {
    it('should update unread count for channel', () => {
      useChannelStore.setState({
        channels: [mockChannelListItem],
      });

      useChannelStore.getState().updateUnreadCount('chan-1', 5);

      const state = useChannelStore.getState();
      expect(state.channels[0].unread_count).toBe(5);
    });
  });

  describe('handleNewMessage', () => {
    it('should increment unread count when not in channel', () => {
      const otherChannel = { ...mockChannelListItem, id: 'chan-2' };
      useChannelStore.setState({
        channels: [otherChannel],
        currentChannel: mockChannel, // In chan-1
      });

      useChannelStore.getState().handleNewMessage('chan-2');

      const state = useChannelStore.getState();
      expect(state.channels[0].unread_count).toBe(1);
    });

    it('should not increment unread when in current channel', () => {
      useChannelStore.setState({
        channels: [mockChannelListItem],
        currentChannel: mockChannel,
      });

      useChannelStore.getState().handleNewMessage('chan-1');

      const state = useChannelStore.getState();
      expect(state.channels[0].unread_count).toBe(0);
    });
  });

  describe('setCurrentChannel', () => {
    it('should set current channel', () => {
      useChannelStore.getState().setCurrentChannel(mockChannel);

      const state = useChannelStore.getState();
      expect(state.currentChannel).toEqual(mockChannel);
    });
  });

  describe('clearError', () => {
    it('should clear error state', () => {
      useChannelStore.setState({ error: 'Some error' });
      useChannelStore.getState().clearError();

      const state = useChannelStore.getState();
      expect(state.error).toBeNull();
    });
  });
});
