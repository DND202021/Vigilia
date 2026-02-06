/**
 * Toast Store Tests
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useToastStore, toast } from '../stores/toastStore';

describe('useToastStore', () => {
  beforeEach(() => {
    // Reset store state
    useToastStore.setState({
      toasts: [],
    });
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('addToast', () => {
    it('should add a toast to the queue', () => {
      const { addToast, toasts } = useToastStore.getState();

      addToast('success', 'Operation successful');

      const state = useToastStore.getState();
      expect(state.toasts).toHaveLength(1);
      expect(state.toasts[0]).toMatchObject({
        type: 'success',
        message: 'Operation successful',
        duration: 5000,
      });
      expect(state.toasts[0].id).toMatch(/^toast-\d+$/);
    });

    it('should add multiple toasts with unique IDs', () => {
      const { addToast } = useToastStore.getState();

      addToast('info', 'First message');
      addToast('warning', 'Second message');

      const state = useToastStore.getState();
      expect(state.toasts).toHaveLength(2);
      expect(state.toasts[0].id).not.toBe(state.toasts[1].id);
    });

    it('should auto-remove toast after duration', () => {
      const { addToast } = useToastStore.getState();

      addToast('error', 'Temporary error', 1000);

      expect(useToastStore.getState().toasts).toHaveLength(1);

      // Fast-forward time by 1000ms
      vi.advanceTimersByTime(1000);

      expect(useToastStore.getState().toasts).toHaveLength(0);
    });

    it('should not auto-remove toast with 0 duration', () => {
      const { addToast } = useToastStore.getState();

      addToast('info', 'Persistent message', 0);

      expect(useToastStore.getState().toasts).toHaveLength(1);

      vi.advanceTimersByTime(10000);

      // Should still be present
      expect(useToastStore.getState().toasts).toHaveLength(1);
    });
  });

  describe('removeToast', () => {
    it('should remove a specific toast by ID', () => {
      const { addToast, removeToast } = useToastStore.getState();

      addToast('success', 'Message 1', 0);
      addToast('error', 'Message 2', 0);

      const state = useToastStore.getState();
      const firstToastId = state.toasts[0].id;

      removeToast(firstToastId);

      const newState = useToastStore.getState();
      expect(newState.toasts).toHaveLength(1);
      expect(newState.toasts[0].message).toBe('Message 2');
    });

    it('should do nothing if ID does not exist', () => {
      const { addToast, removeToast } = useToastStore.getState();

      addToast('info', 'Test message', 0);
      removeToast('non-existent-id');

      expect(useToastStore.getState().toasts).toHaveLength(1);
    });
  });

  describe('clearToasts', () => {
    it('should clear all toasts', () => {
      const { addToast, clearToasts } = useToastStore.getState();

      addToast('success', 'Message 1', 0);
      addToast('error', 'Message 2', 0);
      addToast('warning', 'Message 3', 0);

      expect(useToastStore.getState().toasts).toHaveLength(3);

      clearToasts();

      expect(useToastStore.getState().toasts).toHaveLength(0);
    });

    it('should handle clearing when already empty', () => {
      const { clearToasts } = useToastStore.getState();

      clearToasts();

      expect(useToastStore.getState().toasts).toHaveLength(0);
    });
  });

  describe('toast convenience functions', () => {
    it('should add error toast via toast.error', () => {
      toast.error('Error message');

      const state = useToastStore.getState();
      expect(state.toasts).toHaveLength(1);
      expect(state.toasts[0].type).toBe('error');
      expect(state.toasts[0].message).toBe('Error message');
    });

    it('should add success toast via toast.success', () => {
      toast.success('Success message');

      const state = useToastStore.getState();
      expect(state.toasts).toHaveLength(1);
      expect(state.toasts[0].type).toBe('success');
      expect(state.toasts[0].message).toBe('Success message');
    });

    it('should add warning toast via toast.warning', () => {
      toast.warning('Warning message');

      const state = useToastStore.getState();
      expect(state.toasts).toHaveLength(1);
      expect(state.toasts[0].type).toBe('warning');
      expect(state.toasts[0].message).toBe('Warning message');
    });

    it('should add info toast via toast.info', () => {
      toast.info('Info message');

      const state = useToastStore.getState();
      expect(state.toasts).toHaveLength(1);
      expect(state.toasts[0].type).toBe('info');
      expect(state.toasts[0].message).toBe('Info message');
    });

    it('should accept custom duration in convenience functions', () => {
      toast.success('Custom duration', 3000);

      const state = useToastStore.getState();
      expect(state.toasts[0].duration).toBe(3000);
    });
  });
});
