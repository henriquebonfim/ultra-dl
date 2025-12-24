import { describe, expect, it, spyOn } from 'bun:test';

describe('useDownload utilities', () => {
  it('window.open should be callable', () => {
    const windowOpenSpy = spyOn(window, 'open').mockImplementation(() => null);

    window.open('http://download.com', '_blank');

    expect(windowOpenSpy).toHaveBeenCalledWith('http://download.com', '_blank');
    windowOpenSpy.mockRestore();
  });
});
