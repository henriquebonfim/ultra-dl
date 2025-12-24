import { describe, expect, it } from 'bun:test';

describe('Index Page', () => {
  it('should export Index component', async () => {
    const module = await import('./Index');
    expect(module.default).toBeDefined();
    expect(typeof module.default).toBe('function');
  });
});
