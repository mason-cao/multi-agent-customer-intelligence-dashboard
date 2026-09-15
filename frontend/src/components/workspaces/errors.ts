import { getApiErrorDetail, getApiErrorStatus } from '../../api/errors';

export function getAdminAccessMessage(error: unknown): string | null {
  const status = getApiErrorStatus(error);
  const detail = getApiErrorDetail(error);

  if (status === 401) {
    return 'Owner access is required to manage all workspaces.';
  }
  if (status === 403) {
    return 'The saved owner passcode was not accepted. Enter the current passcode and retry.';
  }
  if (status === 503) {
    return 'Owner access has not been set up yet.';
  }
  return detail;
}

export function getCreateErrorMessage(error: unknown): string {
  const status = getApiErrorStatus(error);
  const detail = getApiErrorDetail(error);

  if (status === 401) {
    return 'Workspace creation needs owner access. Enter the owner passcode and retry.';
  }
  if (status === 403) {
    return 'The owner passcode was rejected. Update the saved passcode and retry.';
  }
  if (status === 503) {
    return 'Owner access has not been set up yet.';
  }
  if (status === 409 && detail) {
    return detail;
  }
  return detail ?? 'Failed to create workspace. Please try again.';
}

export function getOwnerAccessErrorMessage(error: unknown): string {
  const detail = getApiErrorDetail(error);
  return detail ?? "We couldn't save owner access. Please try again.";
}

export function getListActionErrorMessage(error: unknown): string {
  const status = getApiErrorStatus(error);
  const detail = getApiErrorDetail(error);

  if (status === 429) {
    return detail ?? 'Generation capacity is in use. Try again in a moment.';
  }
  if (status === 401 || status === 403) {
    return 'Owner access was rejected. Update the saved passcode and retry.';
  }
  return detail ?? "That didn't work. Please try again.";
}

export function getSyntheticErrorMessage(error: unknown): string {
  const status = getApiErrorStatus(error);
  const detail = getApiErrorDetail(error);

  if (status === 403) {
    return detail ?? 'Synthetic workspace access is disabled.';
  }
  if (status === 409 || status === 429) {
    return detail ?? 'Synthetic workspace capacity is temporarily unavailable.';
  }
  return detail ?? "We couldn't start the demo workspace. Try again.";
}
