/**
 * Security Utilities
 */

/**
 * Content Security Policy meta tag content
 * This should also be set via HTTP headers for better security
 */
export const CSP_POLICY = `
  default-src 'self';
  script-src 'self' 'unsafe-inline' 'unsafe-eval';
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  font-src 'self' https://fonts.gstatic.com;
  img-src 'self' data: blob: https://*.tile.openstreetmap.org;
  connect-src 'self' ws://localhost:* wss://localhost:* http://localhost:* https://api.eriop.local;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
`.replace(/\s+/g, ' ').trim();

/**
 * Apply CSP via meta tag
 * Note: For production, this should be set via HTTP headers
 */
export function applyCSP(): void {
  const existingMeta = document.querySelector('meta[http-equiv="Content-Security-Policy"]');
  if (!existingMeta) {
    const meta = document.createElement('meta');
    meta.httpEquiv = 'Content-Security-Policy';
    meta.content = CSP_POLICY;
    document.head.appendChild(meta);
  }
}

/**
 * Security headers for API requests
 */
export const SECURITY_HEADERS = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-XSS-Protection': '1; mode=block',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
};

/**
 * Secure storage wrapper
 * Adds encryption for sensitive data in localStorage
 */
class SecureStorage {
  private encoder = new TextEncoder();
  private decoder = new TextDecoder();

  // Simple obfuscation - for real security, use proper encryption
  private obfuscate(data: string): string {
    try {
      return btoa(
        String.fromCharCode(...this.encoder.encode(data))
      );
    } catch {
      return data;
    }
  }

  private deobfuscate(data: string): string {
    try {
      return this.decoder.decode(
        new Uint8Array(
          atob(data).split('').map((c) => c.charCodeAt(0))
        )
      );
    } catch {
      return data;
    }
  }

  setItem(key: string, value: string): void {
    try {
      localStorage.setItem(`eriop_${key}`, this.obfuscate(value));
    } catch (error) {
      console.error('[SecureStorage] Failed to set item:', error);
    }
  }

  getItem(key: string): string | null {
    try {
      const value = localStorage.getItem(`eriop_${key}`);
      return value ? this.deobfuscate(value) : null;
    } catch (error) {
      console.error('[SecureStorage] Failed to get item:', error);
      return null;
    }
  }

  removeItem(key: string): void {
    localStorage.removeItem(`eriop_${key}`);
  }

  clear(): void {
    const keys = Object.keys(localStorage);
    keys.forEach((key) => {
      if (key.startsWith('eriop_')) {
        localStorage.removeItem(key);
      }
    });
  }
}

export const secureStorage = new SecureStorage();

/**
 * CSRF Token management
 */
let csrfToken: string | null = null;

export function setCSRFToken(token: string): void {
  csrfToken = token;
}

export function getCSRFToken(): string | null {
  return csrfToken;
}

export function clearCSRFToken(): void {
  csrfToken = null;
}

/**
 * Session timeout management
 */
const SESSION_TIMEOUT = 30 * 60 * 1000; // 30 minutes
let sessionTimeoutId: ReturnType<typeof setTimeout> | null = null;
let lastActivity = Date.now();

export function resetSessionTimeout(onTimeout: () => void): void {
  lastActivity = Date.now();

  if (sessionTimeoutId) {
    clearTimeout(sessionTimeoutId);
  }

  sessionTimeoutId = setTimeout(() => {
    onTimeout();
  }, SESSION_TIMEOUT);
}

export function getSessionRemainingTime(): number {
  return Math.max(0, SESSION_TIMEOUT - (Date.now() - lastActivity));
}

export function clearSessionTimeout(): void {
  if (sessionTimeoutId) {
    clearTimeout(sessionTimeoutId);
    sessionTimeoutId = null;
  }
}

/**
 * Detect potential security issues
 */
export function detectSecurityIssues(): string[] {
  const issues: string[] = [];

  // Check for insecure connection
  if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost') {
    issues.push('Application not served over HTTPS');
  }

  // Check for browser features
  if (!window.crypto?.subtle) {
    issues.push('Web Crypto API not available');
  }

  // Check for localStorage availability
  try {
    localStorage.setItem('test', 'test');
    localStorage.removeItem('test');
  } catch {
    issues.push('localStorage not available');
  }

  // Check for service worker support
  if (!('serviceWorker' in navigator)) {
    issues.push('Service Workers not supported');
  }

  return issues;
}

/**
 * Generate a cryptographically secure random string
 */
export function generateSecureRandom(length: number = 32): string {
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  return Array.from(array, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

/**
 * Hash a string using SHA-256
 */
export async function hashString(str: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(str);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Sanitize URL to prevent open redirect
 */
export function sanitizeRedirectUrl(url: string, allowedHosts: string[] = []): string {
  try {
    const parsed = new URL(url, window.location.origin);

    // Only allow same-origin or explicitly allowed hosts
    if (
      parsed.origin === window.location.origin ||
      allowedHosts.includes(parsed.host)
    ) {
      return parsed.pathname + parsed.search + parsed.hash;
    }

    return '/';
  } catch {
    // Invalid URL, return home
    return '/';
  }
}

/**
 * Check if running in secure context
 */
export function isSecureContext(): boolean {
  return window.isSecureContext;
}

/**
 * Log security event
 */
export function logSecurityEvent(
  event: string,
  details: Record<string, unknown> = {}
): void {
  const logEntry = {
    timestamp: new Date().toISOString(),
    event,
    details,
    userAgent: navigator.userAgent,
    url: window.location.href,
  };

  // In production, this should send to a security logging service
  console.warn('[Security]', logEntry);

  // Store locally for debugging
  try {
    const logs = JSON.parse(localStorage.getItem('eriop_security_logs') || '[]');
    logs.push(logEntry);
    // Keep only last 100 entries
    while (logs.length > 100) {
      logs.shift();
    }
    localStorage.setItem('eriop_security_logs', JSON.stringify(logs));
  } catch {
    // Ignore storage errors
  }
}
