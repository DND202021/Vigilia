/**
 * Input Validation Utilities
 * Security hardening for user inputs
 */

// Common validation patterns
const PATTERNS = {
  email: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
  phone: /^[\d\s\-+().]{7,20}$/,
  username: /^[a-zA-Z0-9_-]{3,50}$/,
  alphanumeric: /^[a-zA-Z0-9]+$/,
  uuid: /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
  coordinates: /^-?\d+\.?\d*$/,
};

// HTML entities for escaping
const HTML_ENTITIES: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#x27;',
  '/': '&#x2F;',
};

/**
 * Escape HTML to prevent XSS
 */
export function escapeHtml(str: string): string {
  if (typeof str !== 'string') return '';
  return str.replace(/[&<>"'/]/g, (char) => HTML_ENTITIES[char] || char);
}

/**
 * Sanitize string input - removes potential dangerous characters
 */
export function sanitizeString(input: string, maxLength: number = 1000): string {
  if (typeof input !== 'string') return '';

  return input
    .trim()
    .slice(0, maxLength)
    .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, ''); // Remove control characters
}

/**
 * Sanitize text for display
 */
export function sanitizeForDisplay(input: string): string {
  return escapeHtml(sanitizeString(input));
}

/**
 * Validate email format
 */
export function isValidEmail(email: string): boolean {
  return PATTERNS.email.test(email.trim());
}

/**
 * Validate phone number format
 */
export function isValidPhone(phone: string): boolean {
  return PATTERNS.phone.test(phone.trim());
}

/**
 * Validate username format
 */
export function isValidUsername(username: string): boolean {
  return PATTERNS.username.test(username);
}

/**
 * Validate UUID format
 */
export function isValidUuid(uuid: string): boolean {
  return PATTERNS.uuid.test(uuid);
}

/**
 * Validate coordinates
 */
export function isValidLatitude(lat: number | string): boolean {
  const num = typeof lat === 'string' ? parseFloat(lat) : lat;
  return !isNaN(num) && num >= -90 && num <= 90;
}

export function isValidLongitude(lon: number | string): boolean {
  const num = typeof lon === 'string' ? parseFloat(lon) : lon;
  return !isNaN(num) && num >= -180 && num <= 180;
}

/**
 * Validate and sanitize incident data
 */
export function validateIncidentInput(data: {
  title?: string;
  description?: string;
  address?: string;
  caller_name?: string;
  caller_phone?: string;
  latitude?: number;
  longitude?: number;
}): { isValid: boolean; errors: Record<string, string>; sanitized: typeof data } {
  const errors: Record<string, string> = {};
  const sanitized = { ...data };

  // Title - required
  if (!data.title?.trim()) {
    errors.title = 'Title is required';
  } else if (data.title.length > 200) {
    errors.title = 'Title must be less than 200 characters';
  } else {
    sanitized.title = sanitizeString(data.title, 200);
  }

  // Description - optional
  if (data.description) {
    if (data.description.length > 5000) {
      errors.description = 'Description must be less than 5000 characters';
    } else {
      sanitized.description = sanitizeString(data.description, 5000);
    }
  }

  // Address - optional
  if (data.address) {
    if (data.address.length > 500) {
      errors.address = 'Address must be less than 500 characters';
    } else {
      sanitized.address = sanitizeString(data.address, 500);
    }
  }

  // Caller name - optional
  if (data.caller_name) {
    if (data.caller_name.length > 100) {
      errors.caller_name = 'Caller name must be less than 100 characters';
    } else {
      sanitized.caller_name = sanitizeString(data.caller_name, 100);
    }
  }

  // Caller phone - optional
  if (data.caller_phone) {
    if (!isValidPhone(data.caller_phone)) {
      errors.caller_phone = 'Invalid phone number format';
    } else {
      sanitized.caller_phone = sanitizeString(data.caller_phone, 20);
    }
  }

  // Coordinates - optional but must be valid if provided
  if (data.latitude !== undefined) {
    if (!isValidLatitude(data.latitude)) {
      errors.latitude = 'Invalid latitude';
    }
  }

  if (data.longitude !== undefined) {
    if (!isValidLongitude(data.longitude)) {
      errors.longitude = 'Invalid longitude';
    }
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
    sanitized,
  };
}

/**
 * Validate login credentials
 */
export function validateLoginInput(data: {
  username: string;
  password: string;
}): { isValid: boolean; errors: Record<string, string> } {
  const errors: Record<string, string> = {};

  if (!data.username?.trim()) {
    errors.username = 'Username is required';
  } else if (data.username.length > 100) {
    errors.username = 'Username too long';
  }

  if (!data.password) {
    errors.password = 'Password is required';
  } else if (data.password.length < 8) {
    errors.password = 'Password must be at least 8 characters';
  } else if (data.password.length > 128) {
    errors.password = 'Password too long';
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}

/**
 * Validate resource input
 */
export function validateResourceInput(data: {
  name?: string;
  call_sign?: string;
  capabilities?: string[];
}): { isValid: boolean; errors: Record<string, string>; sanitized: typeof data } {
  const errors: Record<string, string> = {};
  const sanitized = { ...data };

  if (!data.name?.trim()) {
    errors.name = 'Name is required';
  } else if (data.name.length > 100) {
    errors.name = 'Name must be less than 100 characters';
  } else {
    sanitized.name = sanitizeString(data.name, 100);
  }

  if (data.call_sign) {
    if (data.call_sign.length > 20) {
      errors.call_sign = 'Call sign must be less than 20 characters';
    } else {
      sanitized.call_sign = sanitizeString(data.call_sign, 20);
    }
  }

  if (data.capabilities) {
    sanitized.capabilities = data.capabilities
      .map((c) => sanitizeString(c, 50))
      .filter(Boolean)
      .slice(0, 20);
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
    sanitized,
  };
}

/**
 * Rate limiting helper
 */
export class RateLimiter {
  private attempts: Map<string, number[]> = new Map();

  constructor(
    private maxAttempts: number = 5,
    private windowMs: number = 60000
  ) {}

  isAllowed(key: string): boolean {
    const now = Date.now();
    const attempts = this.attempts.get(key) || [];

    // Remove old attempts outside the window
    const recentAttempts = attempts.filter((time) => now - time < this.windowMs);

    if (recentAttempts.length >= this.maxAttempts) {
      return false;
    }

    recentAttempts.push(now);
    this.attempts.set(key, recentAttempts);
    return true;
  }

  reset(key: string): void {
    this.attempts.delete(key);
  }

  getRemainingAttempts(key: string): number {
    const now = Date.now();
    const attempts = this.attempts.get(key) || [];
    const recentAttempts = attempts.filter((time) => now - time < this.windowMs);
    return Math.max(0, this.maxAttempts - recentAttempts.length);
  }
}

// Singleton rate limiter for login attempts
export const loginRateLimiter = new RateLimiter(5, 60000);
