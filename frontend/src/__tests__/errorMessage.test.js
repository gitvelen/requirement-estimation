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
});
