export class ApiError extends Error {
  readonly status: number;
  readonly data: unknown;

  constructor(status: number, data: unknown) {
    super(getErrorDetail(data) ?? `Request failed (${status})`);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

function getErrorDetail(data: unknown): string | null {
  if (!data || typeof data !== 'object' || !('detail' in data)) return null;
  const { detail } = data;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.find((item) => item && typeof item.msg === 'string')?.msg ?? null;
  }
  return null;
}

export function getApiErrorStatus(error: unknown): number | undefined {
  return error instanceof ApiError ? error.status : undefined;
}

export function getApiErrorDetail(error: unknown): string | null {
  return error instanceof ApiError ? getErrorDetail(error.data) : null;
}
