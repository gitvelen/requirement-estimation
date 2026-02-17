import {
  PROFILE_FIELD_LABELS_V21,
  parseModuleStructureDraft,
  stringifyModuleStructureDraft,
} from './systemProfileV21';

describe('systemProfileV21 helpers', () => {
  test('uses exactly four profile fields in v2.1 board', () => {
    expect(Object.keys(PROFILE_FIELD_LABELS_V21)).toEqual([
      'system_scope',
      'module_structure',
      'integration_points',
      'key_constraints',
    ]);
  });

  test('parses module_structure JSON array', () => {
    const draft = '[{"module_name":"账户","functions":[{"name":"开户","desc":"开户流程"}]}]';
    const result = parseModuleStructureDraft(draft);

    expect(result.ok).toBe(true);
    expect(result.value).toEqual([
      {
        module_name: '账户',
        functions: [{ name: '开户', desc: '开户流程' }],
      },
    ]);
  });

  test('rejects non-array module_structure JSON', () => {
    const result = parseModuleStructureDraft('{"module_name":"账户"}');

    expect(result.ok).toBe(false);
    expect(result.errorCode).toBe('invalid_module_structure');
  });

  test('formats module_structure with stable pretty JSON', () => {
    const text = stringifyModuleStructureDraft([
      { module_name: '账户', functions: [{ name: '开户', desc: '' }] },
    ]);

    expect(text).toContain('"module_name": "账户"');
    expect(text).toContain('"functions": [');
  });
});
