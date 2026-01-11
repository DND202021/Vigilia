/**
 * Utility Functions Tests
 */

import { describe, it, expect } from 'vitest';
import {
  formatDate,
  formatRelativeTime,
  getPriorityLabel,
  getStatusLabel,
  getSeverityLabel,
  calculateDistance,
  formatDistance,
  cn,
} from '../utils';

describe('formatDate', () => {
  it('should format ISO date string correctly', () => {
    const result = formatDate('2025-01-15T14:30:00Z');
    expect(result).toContain('Jan');
    expect(result).toContain('15');
    expect(result).toContain('2025');
  });

  it('should handle invalid date gracefully', () => {
    const result = formatDate('invalid-date');
    expect(result).toBe('invalid-date');
  });
});

describe('formatRelativeTime', () => {
  it('should format recent times', () => {
    const recentDate = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    const result = formatRelativeTime(recentDate);
    expect(result).toContain('minute');
  });

  it('should handle invalid date gracefully', () => {
    const result = formatRelativeTime('invalid-date');
    expect(result).toBe('invalid-date');
  });
});

describe('getPriorityLabel', () => {
  it('should return correct labels for priorities', () => {
    expect(getPriorityLabel(1)).toBe('Critical');
    expect(getPriorityLabel(2)).toBe('High');
    expect(getPriorityLabel(3)).toBe('Medium');
    expect(getPriorityLabel(4)).toBe('Low');
    expect(getPriorityLabel(5)).toBe('Info');
  });
});

describe('getStatusLabel', () => {
  it('should return correct labels for statuses', () => {
    expect(getStatusLabel('new')).toBe('New');
    expect(getStatusLabel('assigned')).toBe('Assigned');
    expect(getStatusLabel('on_scene')).toBe('On Scene');
    expect(getStatusLabel('closed')).toBe('Closed');
  });
});

describe('getSeverityLabel', () => {
  it('should return correct labels for severities', () => {
    expect(getSeverityLabel('critical')).toBe('Critical');
    expect(getSeverityLabel('high')).toBe('High');
    expect(getSeverityLabel('medium')).toBe('Medium');
    expect(getSeverityLabel('low')).toBe('Low');
    expect(getSeverityLabel('info')).toBe('Info');
  });
});

describe('calculateDistance', () => {
  it('should calculate distance between two points', () => {
    // Montreal to Toronto is approximately 504 km
    const distance = calculateDistance(45.5017, -73.5673, 43.6532, -79.3832);
    expect(distance).toBeGreaterThan(500000);
    expect(distance).toBeLessThan(520000);
  });

  it('should return 0 for same point', () => {
    const distance = calculateDistance(45.5017, -73.5673, 45.5017, -73.5673);
    expect(distance).toBe(0);
  });
});

describe('formatDistance', () => {
  it('should format meters for short distances', () => {
    expect(formatDistance(500)).toBe('500 m');
  });

  it('should format kilometers for long distances', () => {
    expect(formatDistance(5000)).toBe('5.0 km');
  });
});

describe('cn', () => {
  it('should merge class names', () => {
    const result = cn('foo', 'bar');
    expect(result).toBe('foo bar');
  });

  it('should handle conditional classes', () => {
    const result = cn('foo', false && 'bar', 'baz');
    expect(result).toBe('foo baz');
  });

  it('should handle tailwind merge conflicts', () => {
    const result = cn('p-4', 'p-8');
    expect(result).toBe('p-8');
  });
});
