import {
  ACTIVE_WORKSPACE_STORAGE_KEY,
  ACTIVE_WORKSPACE_TOKEN_STORAGE_KEY,
  ADMIN_TOKEN_STORAGE_KEY,
} from '../constants/workspace';

type SessionStorageTarget = Pick<Storage, 'removeItem'>;

export function clearStoredSession(storage: SessionStorageTarget = window.localStorage) {
  storage.removeItem(ADMIN_TOKEN_STORAGE_KEY);
  storage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  storage.removeItem(ACTIVE_WORKSPACE_TOKEN_STORAGE_KEY);
}

export function shouldShowWorkspaceHubLogout({
  workspacesIsLoading,
  workspacesIsError,
}: {
  workspacesIsLoading: boolean;
  workspacesIsError: boolean;
}) {
  return !workspacesIsLoading && !workspacesIsError;
}
