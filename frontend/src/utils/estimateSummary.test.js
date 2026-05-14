import { formatEstimateTotal, sumEstimateValues } from './estimateSummary';

describe('estimate summary helpers', () => {
  it('sums numeric estimate values and ignores empty or invalid values', () => {
    const rows = [
      { days: 1 },
      { days: '2.58' },
      { days: null },
      { days: '' },
      { days: 'invalid' },
      { days: 0 },
    ];

    expect(sumEstimateValues(rows, (row) => row.days)).toBe(3.58);
  });

  it('formats totals without noisy trailing decimals', () => {
    expect(formatEstimateTotal(3)).toBe('3');
    expect(formatEstimateTotal(4.080000000000001)).toBe('4.08');
    expect(formatEstimateTotal(0)).toBe('0');
  });
});
