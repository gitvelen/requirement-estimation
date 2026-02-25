import { resolveActionColumnWidth } from '../utils/taskTableLayout';

describe('task table action column layout', () => {
  it('uses compact width for icon-only actions', () => {
    const width = resolveActionColumnWidth({ isExpert: false, resolvedTab: 'ongoing' });
    expect(width).toBe(148);
  });

  it('uses wider width for expert ongoing tasks', () => {
    const width = resolveActionColumnWidth({ isExpert: true, resolvedTab: 'ongoing' });
    expect(width).toBe(208);
  });

  it('keeps compact width for expert completed tasks', () => {
    const width = resolveActionColumnWidth({ isExpert: true, resolvedTab: 'completed' });
    expect(width).toBe(148);
  });
});
