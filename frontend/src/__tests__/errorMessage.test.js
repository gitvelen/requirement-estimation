import { extractErrorMessage } from '../utils/errorMessage';

describe('extractErrorMessage', () => {
  it('reads string message from response payload', () => {
    const error = {
      response: {
        data: {
          message: '权限不足',
        },
      },
    };

    expect(extractErrorMessage(error, '保存失败')).toBe('权限不足');
  });

  it('reads validation detail array from fastapi 422 response', () => {
    const error = {
      response: {
        data: {
          detail: [
            {
              msg: 'Field required',
            },
          ],
        },
      },
    };

    expect(extractErrorMessage(error, '保存失败')).toBe('Field required');
  });

  it('falls back when payload has no readable detail', () => {
    const error = {
      response: {
        data: {
          detail: [{ unknown: 'x' }],
        },
      },
    };

    expect(extractErrorMessage(error, '保存失败')).toBe('保存失败');
  });

  it('maps 413 response to file-too-large message', () => {
    const error = {
      response: {
        status: 413,
        data: '<html><body>413 Request Entity Too Large</body></html>',
      },
    };

    expect(extractErrorMessage(error, '文档导入失败')).toBe('文件过大（超过上传限制 50MB）');
  });
});
