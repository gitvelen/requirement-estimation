import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import EvaluationPage from '../pages/EvaluationPage';
import ReportPage from '../pages/ReportPage';

jest.setTimeout(30000);

jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));
const axios = require('axios');

jest.mock('../hooks/usePermission', () => () => ({
  isAdmin: true,
}));

const mockEvaluationResponse = {
  data: {
    code: 200,
    data: {
      task: {
        id: 'task_1',
        name: '任务A',
        status: 'evaluating',
        currentRound: 1,
        systems: ['HOP'],
      },
      features: {
        HOP: [
          {
            id: 'feat_1',
            sequence: '1.1',
            module: '开户',
            name: '证件校验',
            description: '校验身份证',
            inputs: ['身份证号'],
            outputs: ['结果'],
            dependencies: ['OCR'],
            aiEstimatedDays: 2.58,
            optimistic: 1.5,
            mostLikely: 2.5,
            most_likely: 2.5,
            pessimistic: 4.0,
            expected: 2.58,
            reasoning: '规则复杂度中等',
            estimationDegraded: false,
            profileContextUsed: true,
            profile_context_used: true,
            contextSource: 'canonical+wiki_candidate',
            context_source: 'canonical+wiki_candidate',
            myEvaluation: null,
          },
          {
            id: 'feat_2',
            sequence: '1.2',
            module: '销户',
            name: '销户申请',
            description: '提交销户申请',
            inputs: [],
            outputs: [],
            dependencies: [],
            aiEstimatedDays: 1.5,
            optimistic: null,
            mostLikely: null,
            most_likely: null,
            pessimistic: null,
            expected: 1.5,
            reasoning: '',
            estimationDegraded: true,
            profileContextUsed: false,
            profile_context_used: false,
            contextSource: 'none',
            context_source: 'none',
            myEvaluation: null,
          },
        ],
      },
      myEvaluation: {
        hasSubmitted: false,
        submittedRound: 0,
        draftData: {},
      },
      highDeviationFeatures: [],
    },
  },
};

const mockTaskDetailResponse = {
  data: {
    code: 200,
    data: {
      id: 'task_1',
      name: '任务A',
      status: 'completed',
      aiStatus: 'completed',
      currentRound: 1,
      maxRounds: 3,
      creatorName: 'PM',
      createdAt: '2026-03-01T10:00:00',
      documentName: 'req.docx',
      systems: ['HOP'],
      featureCount: 2,
      remark: '',
      expertAssignments: [],
      evaluationProgress: { submitted: 0, total: 0 },
      reportVersions: [
        { id: 'rep_1', round: 1, version: 1, file_name: 'report.pdf', generated_at: '2026-03-01T11:00:00' },
      ],
      deviations: {},
    },
  },
};

const mockReportEvaluationResponse = {
  data: {
    task_id: 'task_1',
    status: 'completed',
    features: [
      {
        feature_id: 'feat_1',
        description: '证件校验',
        estimation_days: 2.58,
        optimistic: 1.5,
        most_likely: 2.5,
        pessimistic: 4.0,
        expected: 2.58,
        reasoning: '规则复杂度中等',
        estimation_degraded: false,
        profile_context_used: true,
        context_source: 'canonical+wiki_candidate',
        system_name: 'HOP',
      },
      {
        feature_id: 'feat_2',
        description: '销户申请',
        estimation_days: 1.5,
        optimistic: null,
        most_likely: null,
        pessimistic: null,
        expected: 1.5,
        reasoning: '',
        estimation_degraded: true,
        profile_context_used: false,
        context_source: 'none',
        system_name: 'HOP',
      },
    ],
  },
};

describe('Evaluation/Report three-point estimate v2.4', () => {
  const createMatchMediaResult = (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });

  beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query) => createMatchMediaResult(query),
    });
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows expected as main value and expandable three-point detail in EvaluationPage', async () => {
    axios.get.mockImplementation((url) => {
      if (String(url).includes('/api/v1/evaluation/task_1')) {
        return Promise.resolve(mockEvaluationResponse);
      }
      if (String(url).includes('/api/v1/system-profiles/completeness')) {
        return Promise.resolve({ data: { completeness_score: 88, breakdown: { code_scan: 30, documents: 40, esb: 18 } } });
      }
      return Promise.resolve({ data: {} });
    });

    render(
      <MemoryRouter initialEntries={['/evaluate/task_1?token=token_1']}>
        <Routes>
          <Route path="/evaluate/:taskId" element={<EvaluationPage />} />
        </Routes>
      </MemoryRouter>
    );

    const featureText = await screen.findByText('证件校验');
    expect(featureText).toBeInTheDocument();
    expect(screen.getAllByText('2.58').length).toBeGreaterThan(0);

    const featureRow = featureText.closest('tr');
    const expandIcon = featureRow?.querySelector('.ant-table-row-expand-icon');
    expect(expandIcon).not.toBeNull();
    fireEvent.click(expandIcon);
    expect(await screen.findByText(/乐观值/)).toBeInTheDocument();
    expect(screen.getByText(/最可能值/)).toBeInTheDocument();
    expect(screen.getByText(/悲观值/)).toBeInTheDocument();
    expect(screen.getByText(/规则复杂度中等/)).toBeInTheDocument();
    expect(screen.getByText(/画像上下文：已使用/)).toBeInTheDocument();
    expect(screen.getByText(/已发布画像 \+ wiki高置信候选补位/)).toBeInTheDocument();
  });

  it('shows degraded message in EvaluationPage expanded row when three-point values are missing', async () => {
    axios.get.mockImplementation((url) => {
      if (String(url).includes('/api/v1/evaluation/task_1')) {
        return Promise.resolve(mockEvaluationResponse);
      }
      if (String(url).includes('/api/v1/system-profiles/completeness')) {
        return Promise.resolve({ data: { completeness_score: 88, breakdown: { code_scan: 30, documents: 40, esb: 18 } } });
      }
      return Promise.resolve({ data: {} });
    });

    render(
      <MemoryRouter initialEntries={['/evaluate/task_1?token=token_1']}>
        <Routes>
          <Route path="/evaluate/:taskId" element={<EvaluationPage />} />
        </Routes>
      </MemoryRouter>
    );

    const degradedText = await screen.findByText('销户申请');
    expect(degradedText).toBeInTheDocument();
    const degradedRow = degradedText.closest('tr');
    const expandIcon = degradedRow?.querySelector('.ant-table-row-expand-icon');
    expect(expandIcon).not.toBeNull();
    fireEvent.click(expandIcon);
    expect(await screen.findByText('LLM 估算未成功，显示为拆分阶段原始估值')).toBeInTheDocument();
  });

  it('renders ReportPage feature details with expandable three-point section', async () => {
    axios.get.mockImplementation((url) => {
      if (url === '/api/v1/tasks/task_1') {
        return Promise.resolve(mockTaskDetailResponse);
      }
      if (url === '/api/v1/tasks/task_1/high-deviation') {
        return Promise.resolve({ data: { data: { round: null, isOfficial: false, items: [] } } });
      }
      if (url === '/api/v1/tasks/task_1/evaluation') {
        return Promise.resolve(mockReportEvaluationResponse);
      }
      return Promise.resolve({ data: {} });
    });

    render(
      <MemoryRouter initialEntries={['/reports/task_1']}>
        <Routes>
          <Route path="/reports/:taskId" element={<ReportPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('功能点明细')).toBeInTheDocument();
    const reportFeatureText = await screen.findByText('证件校验');
    expect(reportFeatureText).toBeInTheDocument();
    expect(screen.getAllByText('2.58').length).toBeGreaterThan(0);

    const reportFeatureRow = reportFeatureText.closest('tr');
    const expandIcon = reportFeatureRow?.querySelector('.ant-table-row-expand-icon');
    expect(expandIcon).not.toBeNull();
    fireEvent.click(expandIcon);
    await waitFor(() => {
      expect(screen.getByText(/最可能值/)).toBeInTheDocument();
    });
    expect(screen.getByText(/画像上下文：已使用/)).toBeInTheDocument();
    expect(screen.getByText(/已发布画像 \+ wiki高置信候选补位/)).toBeInTheDocument();
  });
});
