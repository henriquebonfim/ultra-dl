import { describe, it, expect } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'fs';
import { gzipSync } from 'zlib';
import { join } from 'path';

describe('Bundle Size', () => {
  const DIST_PATH = './dist/assets';
  const MAX_GZIPPED_SIZE = 512000; // 500KB in bytes

  it('should not exceed 500KB gzipped for all JavaScript bundles', () => {
    // Check if dist directory exists
    let files: string[];
    try {
      files = readdirSync(DIST_PATH);
    } catch (error) {
      throw new Error(
        'Build artifacts not found. Run "npm run build" before running this test.'
      );
    }

    // Filter for JavaScript files only
    const jsFiles = files.filter(file => file.endsWith('.js'));

    if (jsFiles.length === 0) {
      throw new Error('No JavaScript files found in dist/assets directory');
    }

    // Calculate total gzipped size
    let totalGzippedSize = 0;
    const chunkSizes: { name: string; uncompressed: number; gzipped: number }[] = [];

    jsFiles.forEach(file => {
      const filePath = join(DIST_PATH, file);
      const content = readFileSync(filePath);
      const uncompressedSize = statSync(filePath).size;
      const gzipped = gzipSync(content);
      const gzippedSize = gzipped.length;

      totalGzippedSize += gzippedSize;
      chunkSizes.push({
        name: file,
        uncompressed: uncompressedSize,
        gzipped: gzippedSize,
      });
    });

    // Log chunk breakdown for debugging
    console.log('\n📦 Bundle Size Analysis:');
    console.log('─'.repeat(80));
    chunkSizes.forEach(chunk => {
      const uncompressedKB = (chunk.uncompressed / 1024).toFixed(2);
      const gzippedKB = (chunk.gzipped / 1024).toFixed(2);
      const compressionRatio = ((1 - chunk.gzipped / chunk.uncompressed) * 100).toFixed(1);
      console.log(
        `  ${chunk.name.padEnd(40)} ${uncompressedKB.padStart(8)} KB → ${gzippedKB.padStart(8)} KB (${compressionRatio}% compressed)`
      );
    });
    console.log('─'.repeat(80));
    console.log(
      `  Total: ${(totalGzippedSize / 1024).toFixed(2)} KB gzipped (Target: <500 KB)`
    );
    console.log('─'.repeat(80));

    // Assert total size is under target
    expect(totalGzippedSize).toBeLessThan(MAX_GZIPPED_SIZE);

    // Additional assertion: warn if approaching limit (>400KB)
    const warningThreshold = 409600; // 400KB
    if (totalGzippedSize > warningThreshold) {
      console.warn(
        `⚠️  Warning: Bundle size (${(totalGzippedSize / 1024).toFixed(2)} KB) is approaching the 500KB limit`
      );
    }
  });

  it('should have vendor code separated into chunks', () => {
    let files: string[];
    try {
      files = readdirSync(DIST_PATH);
    } catch (error) {
      throw new Error(
        'Build artifacts not found. Run "npm run build" before running this test.'
      );
    }

    const jsFiles = files.filter(file => file.endsWith('.js'));

    // Verify vendor chunks exist
    const hasReactVendor = jsFiles.some(file => file.includes('react-vendor'));
    const hasUiVendor = jsFiles.some(file => file.includes('ui-vendor'));
    const hasQueryVendor = jsFiles.some(file => file.includes('query-vendor'));
    const hasSocketVendor = jsFiles.some(file => file.includes('socket-vendor'));

    expect(hasReactVendor).toBe(true);
    expect(hasUiVendor).toBe(true);
    expect(hasQueryVendor).toBe(true);
    expect(hasSocketVendor).toBe(true);

    console.log('\n✅ Vendor code successfully separated into chunks:');
    console.log('  - react-vendor (React core libraries)');
    console.log('  - ui-vendor (UI component libraries)');
    console.log('  - query-vendor (TanStack React Query)');
    console.log('  - socket-vendor (Socket.IO client)');
  });

  it('should have application code in separate chunk', () => {
    let files: string[];
    try {
      files = readdirSync(DIST_PATH);
    } catch (error) {
      throw new Error(
        'Build artifacts not found. Run "npm run build" before running this test.'
      );
    }

    const jsFiles = files.filter(file => file.endsWith('.js'));

    // Verify main application chunk exists (index-*.js)
    const hasAppChunk = jsFiles.some(
      file => file.startsWith('index-') && !file.includes('vendor')
    );

    expect(hasAppChunk).toBe(true);

    console.log('\n✅ Application code in separate chunk for optimal caching');
  });
});
