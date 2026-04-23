jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));

import {
  COSMIC_GUIDANCE_COPY,
  COSMIC_PRESET_LABELS,
  mergeCosmicConfigForSave,
} from '../pages/CosmicConfigPage';

describe('CosmicConfigPage payload merge', () => {
  it('preserves data movement descriptions when save form omits them', () => {
    const currentConfig = {
      data_group_rules: {
        enabled: true,
        min_attributes: 2,
        min_data_groups: 1,
      },
      functional_process_rules: {
        enabled: true,
        granularity: 'medium',
        min_data_movements: 2,
        max_data_movements: 50,
      },
      data_movement_rules: {
        entry: {
          enabled: true,
          description: '数据从用户进入功能处理',
          keywords: ['输入'],
          weight: 1,
        },
        exit: {
          enabled: true,
          description: '数据从功能处理返回给用户',
          keywords: ['输出'],
          weight: 1,
        },
        read: {
          enabled: true,
          description: '从持久存储读取数据',
          keywords: ['查询'],
          weight: 1,
        },
        write: {
          enabled: true,
          description: '数据写入持久存储',
          keywords: ['保存'],
          weight: 1,
        },
      },
      counting_rules: {
        cff_calculation_method: 'sum',
        include_triggering_operations: true,
        count_unique_data_groups: true,
      },
      validation_rules: {
        min_cff_per_feature: 2,
        max_cff_per_feature: 100,
        validate_data_group_consistency: true,
      },
    };

    const formValues = {
      ...currentConfig,
      data_movement_rules: {
        entry: {
          enabled: false,
          keywords: ['录入'],
          weight: 2,
        },
        exit: {
          enabled: true,
          keywords: ['返回'],
          weight: 1,
        },
        read: {
          enabled: true,
          keywords: ['加载'],
          weight: 1,
        },
        write: {
          enabled: true,
          keywords: ['更新'],
          weight: 1,
        },
      },
    };

    expect(mergeCosmicConfigForSave(currentConfig, formValues)).toEqual({
      ...currentConfig,
      data_movement_rules: {
        entry: {
          enabled: false,
          description: '数据从用户进入功能处理',
          keywords: ['录入'],
          weight: 2,
        },
        exit: {
          enabled: true,
          description: '数据从功能处理返回给用户',
          keywords: ['返回'],
          weight: 1,
        },
        read: {
          enabled: true,
          description: '从持久存储读取数据',
          keywords: ['加载'],
          weight: 1,
        },
        write: {
          enabled: true,
          description: '数据写入持久存储',
          keywords: ['更新'],
          weight: 1,
        },
      },
    });
  });
});

describe('CosmicConfigPage guidance copy', () => {
  it('exports preset labels without misleading splitting claims', () => {
    expect(COSMIC_PRESET_LABELS).toEqual({
      fine: '偏保守口径',
      medium: '平衡口径',
      coarse: '宽松口径',
    });

    const joinedLabels = Object.values(COSMIC_PRESET_LABELS).join(' ');
    expect(joinedLabels).not.toMatch(/每个按钮\/操作=1个功能点/);
    expect(joinedLabels).not.toMatch(/完整交易流程=1个功能点/);
    expect(joinedLabels).not.toMatch(/业务模块=1个功能点/);
  });

  it('exports concise guidance focused on metric meaning and boundary', () => {
    const combinedCopy = COSMIC_GUIDANCE_COPY.join('\n');

    expect(combinedCopy).toMatch(/本页用于配置 COSMIC 计量口径/);
    expect(combinedCopy).toMatch(/不会直接控制当前功能点拆分输出/);
    expect(combinedCopy).toMatch(/按组织口径统一配置后，再用于 COSMIC 分析与估算解释/);
    expect(combinedCopy).not.toMatch(/每个按钮\/操作可拆分为单独功能点/);
    expect(combinedCopy).not.toMatch(/一个完整交易流程（输入\+校验\+处理\+返回）作为一个功能点/);
    expect(combinedCopy).not.toMatch(/一个业务模块作为一个功能点/);
  });
});
