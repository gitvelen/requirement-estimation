const toTrimmedString = (value) => String(value ?? '').trim();

export const PROFILE_FIELD_LABELS_V21 = {
  system_scope: '系统定位与边界',
  module_structure: '功能模块结构',
  integration_points: '主要集成点',
  key_constraints: '关键约束',
};

export const buildEmptyV21ProfileFormValues = () => ({
  system_scope: '',
  module_structure: '',
  integration_points: '',
  key_constraints: '',
});

const parseJsonArray = (value) => {
  if (Array.isArray(value)) {
    return { ok: true, value };
  }

  const text = toTrimmedString(value);
  if (!text) {
    return { ok: true, value: [] };
  }

  try {
    const parsed = JSON.parse(text);
    if (!Array.isArray(parsed)) {
      return {
        ok: false,
        errorCode: 'invalid_module_structure',
        message: 'module_structure 必须是 JSON 数组',
      };
    }
    return { ok: true, value: parsed };
  } catch (_error) {
    return {
      ok: false,
      errorCode: 'invalid_module_structure',
      message: 'module_structure 不是合法 JSON',
    };
  }
};

export const parseModuleStructureDraft = (draft) => parseJsonArray(draft);

export const stringifyModuleStructureDraft = (value) => {
  const parsed = parseJsonArray(value);
  if (!parsed.ok) {
    return '';
  }
  return JSON.stringify(parsed.value, null, 2);
};

export const parseV21ProfileFormValues = (formValues) => {
  const values = formValues || {};
  const parsedModuleStructure = parseJsonArray(values.module_structure);
  if (!parsedModuleStructure.ok) {
    return parsedModuleStructure;
  }

  return {
    ok: true,
    value: {
      system_scope: toTrimmedString(values.system_scope),
      module_structure: parsedModuleStructure.value,
      integration_points: toTrimmedString(values.integration_points),
      key_constraints: toTrimmedString(values.key_constraints),
    },
  };
};
