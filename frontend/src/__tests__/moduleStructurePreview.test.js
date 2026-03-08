import React, { Profiler } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ModuleStructurePreview from '../components/systemProfile/ModuleStructurePreview';

describe('ModuleStructurePreview', () => {
  it('renders children tree and toggles nested nodes', () => {
    render(
      <ModuleStructurePreview
        value={[
          {
            module_name: '开户',
            description: '开户域',
            children: [
              {
                module_name: '证件校验',
                description: 'OCR校验',
                children: [
                  { module_name: '活体检测', description: '人脸核验', children: [] },
                ],
              },
            ],
          },
        ]}
      />
    );

    expect(screen.getByRole('button', { name: '收起 开户' })).toBeInTheDocument();
    expect(screen.getByText('OCR校验')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '展开 证件校验' })).toBeInTheDocument();


    fireEvent.click(screen.getByRole('button', { name: '展开 证件校验' }));
    expect(screen.getByText('人脸核验')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '收起 证件校验' }));
    expect(screen.getByRole('button', { name: '展开 证件校验' })).toBeInTheDocument();
  });

  it('normalizes legacy functions into child nodes', () => {
    render(
      <ModuleStructurePreview
        value={[
          {
            module_name: '开户',
            functions: [
              { name: '证件校验', desc: 'OCR校验' },
            ],
          },
        ]}
      />
    );

    expect(screen.getByText('证件校验')).toBeInTheDocument();
    expect(screen.getByText('OCR校验')).toBeInTheDocument();
  });

  it('renders 100 modules within 2 seconds with default first-level expansion strategy', async () => {
    const largeValue = Array.from({ length: 10 }, (_, moduleIndex) => ({
      module_name: `模块${moduleIndex}`,
      children: Array.from({ length: 5 }, (_, childIndex) => ({
        module_name: `子模块${moduleIndex}-${childIndex}`,
        children: Array.from({ length: 2 }, (_, leafIndex) => ({
          module_name: `功能${moduleIndex}-${childIndex}-${leafIndex}`,
          children: [],
        })),
      })),
    }));
    let firstCommitDurationMs = null;

    render(
      <Profiler
        id="module-structure-preview"
        onRender={(id, phase, actualDuration, baseDuration, startTime, commitTime) => {
          if (id === 'module-structure-preview' && phase === 'mount') {
            firstCommitDurationMs = commitTime - startTime;
          }
        }}
      >
        <ModuleStructurePreview value={largeValue} />
      </Profiler>
    );

    expect(await screen.findByText('模块0')).toBeInTheDocument();
    expect(firstCommitDurationMs).not.toBeNull();
    expect(firstCommitDurationMs).toBeLessThan(2000);
  });
});
