/**
 * Jest setup file for TypeScript tests
 */

// Global test timeout
jest.setTimeout(10000);

// Console logging level for tests
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

beforeAll(() => {
  // Suppress console noise during tests unless debugging
  if (!process.env.DEBUG_TESTS) {
    console.error = jest.fn();
    console.warn = jest.fn();
  }
});

afterAll(() => {
  // Restore console logging
  console.error = originalConsoleError;
  console.warn = originalConsoleWarn;
});

// Global test utilities
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeValidUUID(): R;
      toBeWithinTimeRange(start: Date, end: Date): R;
    }
  }
}

// Custom Jest matchers
expect.extend({
  toBeValidUUID(received) {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    const pass = typeof received === 'string' && uuidRegex.test(received);
    
    if (pass) {
      return {
        message: () => `expected ${received} not to be a valid UUID`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${received} to be a valid UUID`,
        pass: false,
      };
    }
  },
  
  toBeWithinTimeRange(received, start, end) {
    const receivedTime = new Date(received);
    const pass = receivedTime >= start && receivedTime <= end;
    
    if (pass) {
      return {
        message: () => `expected ${received} not to be within time range ${start.toISOString()} - ${end.toISOString()}`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${received} to be within time range ${start.toISOString()} - ${end.toISOString()}`,
        pass: false,
      };
    }
  },
});

// Mock environment variables for tests
process.env.NODE_ENV = 'test';
process.env.AI_MAIL_MCP_TEST = 'true';
