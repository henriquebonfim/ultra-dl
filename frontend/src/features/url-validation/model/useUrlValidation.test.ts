import { describe, expect, it } from 'bun:test';
import { validateUrlNotEmpty, validateYoutubeUrl } from './useUrlValidation';

describe('URL Validation', () => {
  describe('Validators', () => {
    it('validateUrlNotEmpty should check for empty string', () => {
      expect(validateUrlNotEmpty('')).toBe(false);
      expect(validateUrlNotEmpty('   ')).toBe(false);
      expect(validateUrlNotEmpty('valid')).toBe(true);
    });

    it('validateYoutubeUrl should regex match youtube domains', () => {
      expect(validateYoutubeUrl('https://www.youtube.com/watch?v=123')).toBe(true);
      expect(validateYoutubeUrl('https://youtu.be/123')).toBe(true);
      expect(validateYoutubeUrl('https://youtube.com/watch?v=123')).toBe(true);
      expect(validateYoutubeUrl('invalid')).toBe(false);
      expect(validateYoutubeUrl('https://example.com')).toBe(false);
    });

    it('validateYoutubeUrl should handle edge cases', () => {
      expect(validateYoutubeUrl('')).toBe(false);
      expect(validateYoutubeUrl('youtube.com')).toBe(false);
      expect(validateYoutubeUrl('http://youtube.com/watch?v=123')).toBe(true);
    });
  });
});
