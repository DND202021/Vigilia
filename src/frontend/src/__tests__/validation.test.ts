/**
 * Validation Utilities Tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  escapeHtml,
  sanitizeString,
  isValidEmail,
  isValidPhone,
  isValidUsername,
  isValidUuid,
  isValidLatitude,
  isValidLongitude,
  validateIncidentInput,
  validateLoginInput,
  validateResourceInput,
  RateLimiter,
} from '../utils/validation';

describe('escapeHtml', () => {
  it('should escape HTML entities', () => {
    expect(escapeHtml('<script>alert("xss")</script>')).toBe(
      '&lt;script&gt;alert(&quot;xss&quot;)&lt;&#x2F;script&gt;'
    );
  });

  it('should handle normal text', () => {
    expect(escapeHtml('Hello World')).toBe('Hello World');
  });

  it('should handle non-string input', () => {
    expect(escapeHtml(null as unknown as string)).toBe('');
    expect(escapeHtml(123 as unknown as string)).toBe('');
  });
});

describe('sanitizeString', () => {
  it('should trim whitespace', () => {
    expect(sanitizeString('  hello  ')).toBe('hello');
  });

  it('should remove control characters', () => {
    expect(sanitizeString('hello\x00world')).toBe('helloworld');
  });

  it('should respect max length', () => {
    expect(sanitizeString('hello world', 5)).toBe('hello');
  });
});

describe('isValidEmail', () => {
  it('should validate correct emails', () => {
    expect(isValidEmail('test@example.com')).toBe(true);
    expect(isValidEmail('user.name@domain.co.uk')).toBe(true);
  });

  it('should reject invalid emails', () => {
    expect(isValidEmail('invalid')).toBe(false);
    expect(isValidEmail('invalid@')).toBe(false);
    expect(isValidEmail('@invalid.com')).toBe(false);
  });
});

describe('isValidPhone', () => {
  it('should validate correct phone numbers', () => {
    expect(isValidPhone('555-1234')).toBe(true);
    expect(isValidPhone('+1 (555) 123-4567')).toBe(true);
  });

  it('should reject invalid phone numbers', () => {
    expect(isValidPhone('123')).toBe(false);
    expect(isValidPhone('abc-defg')).toBe(false);
  });
});

describe('isValidUsername', () => {
  it('should validate correct usernames', () => {
    expect(isValidUsername('john_doe')).toBe(true);
    expect(isValidUsername('user123')).toBe(true);
  });

  it('should reject invalid usernames', () => {
    expect(isValidUsername('ab')).toBe(false); // too short
    expect(isValidUsername('user@name')).toBe(false); // invalid char
  });
});

describe('isValidUuid', () => {
  it('should validate correct UUIDs', () => {
    expect(isValidUuid('123e4567-e89b-12d3-a456-426614174000')).toBe(true);
  });

  it('should reject invalid UUIDs', () => {
    expect(isValidUuid('invalid-uuid')).toBe(false);
    expect(isValidUuid('123456789')).toBe(false);
  });
});

describe('isValidLatitude', () => {
  it('should validate correct latitudes', () => {
    expect(isValidLatitude(45.5)).toBe(true);
    expect(isValidLatitude(-90)).toBe(true);
    expect(isValidLatitude(90)).toBe(true);
    expect(isValidLatitude('45.5')).toBe(true);
  });

  it('should reject invalid latitudes', () => {
    expect(isValidLatitude(91)).toBe(false);
    expect(isValidLatitude(-91)).toBe(false);
    expect(isValidLatitude('invalid')).toBe(false);
  });
});

describe('isValidLongitude', () => {
  it('should validate correct longitudes', () => {
    expect(isValidLongitude(-73.5)).toBe(true);
    expect(isValidLongitude(-180)).toBe(true);
    expect(isValidLongitude(180)).toBe(true);
  });

  it('should reject invalid longitudes', () => {
    expect(isValidLongitude(181)).toBe(false);
    expect(isValidLongitude(-181)).toBe(false);
  });
});

describe('validateIncidentInput', () => {
  it('should validate correct input', () => {
    const result = validateIncidentInput({
      title: 'Test Incident',
      description: 'Test description',
      address: '123 Main St',
      caller_name: 'John Doe',
      caller_phone: '555-1234',
      latitude: 45.5,
      longitude: -73.5,
    });

    expect(result.isValid).toBe(true);
    expect(Object.keys(result.errors)).toHaveLength(0);
  });

  it('should require title', () => {
    const result = validateIncidentInput({
      title: '',
    });

    expect(result.isValid).toBe(false);
    expect(result.errors.title).toBeDefined();
  });

  it('should validate phone format', () => {
    const result = validateIncidentInput({
      title: 'Test',
      caller_phone: 'invalid',
    });

    expect(result.isValid).toBe(false);
    expect(result.errors.caller_phone).toBeDefined();
  });

  it('should validate coordinates', () => {
    const result = validateIncidentInput({
      title: 'Test',
      latitude: 999,
      longitude: 999,
    });

    expect(result.isValid).toBe(false);
    expect(result.errors.latitude).toBeDefined();
    expect(result.errors.longitude).toBeDefined();
  });

  it('should sanitize input', () => {
    const result = validateIncidentInput({
      title: '  Test Title  ',
    });

    expect(result.sanitized.title).toBe('Test Title');
  });
});

describe('validateLoginInput', () => {
  it('should validate correct input', () => {
    const result = validateLoginInput({
      username: 'testuser',
      password: 'password123',
    });

    expect(result.isValid).toBe(true);
  });

  it('should require username', () => {
    const result = validateLoginInput({
      username: '',
      password: 'password123',
    });

    expect(result.isValid).toBe(false);
    expect(result.errors.username).toBeDefined();
  });

  it('should require minimum password length', () => {
    const result = validateLoginInput({
      username: 'testuser',
      password: 'short',
    });

    expect(result.isValid).toBe(false);
    expect(result.errors.password).toBeDefined();
  });
});

describe('validateResourceInput', () => {
  it('should validate correct input', () => {
    const result = validateResourceInput({
      name: 'Engine 1',
      call_sign: 'E1',
      capabilities: ['fire', 'rescue'],
    });

    expect(result.isValid).toBe(true);
  });

  it('should require name', () => {
    const result = validateResourceInput({
      name: '',
    });

    expect(result.isValid).toBe(false);
    expect(result.errors.name).toBeDefined();
  });

  it('should sanitize capabilities', () => {
    const result = validateResourceInput({
      name: 'Test',
      capabilities: ['  fire  ', 'rescue'],
    });

    expect(result.sanitized.capabilities).toEqual(['fire', 'rescue']);
  });
});

describe('RateLimiter', () => {
  let rateLimiter: RateLimiter;

  beforeEach(() => {
    rateLimiter = new RateLimiter(3, 1000); // 3 attempts per second
  });

  it('should allow requests within limit', () => {
    expect(rateLimiter.isAllowed('test')).toBe(true);
    expect(rateLimiter.isAllowed('test')).toBe(true);
    expect(rateLimiter.isAllowed('test')).toBe(true);
  });

  it('should block requests exceeding limit', () => {
    rateLimiter.isAllowed('test');
    rateLimiter.isAllowed('test');
    rateLimiter.isAllowed('test');
    expect(rateLimiter.isAllowed('test')).toBe(false);
  });

  it('should track separate keys independently', () => {
    rateLimiter.isAllowed('key1');
    rateLimiter.isAllowed('key1');
    rateLimiter.isAllowed('key1');
    expect(rateLimiter.isAllowed('key2')).toBe(true);
  });

  it('should reset correctly', () => {
    rateLimiter.isAllowed('test');
    rateLimiter.isAllowed('test');
    rateLimiter.isAllowed('test');
    rateLimiter.reset('test');
    expect(rateLimiter.isAllowed('test')).toBe(true);
  });

  it('should return remaining attempts', () => {
    rateLimiter.isAllowed('test');
    expect(rateLimiter.getRemainingAttempts('test')).toBe(2);
  });
});
