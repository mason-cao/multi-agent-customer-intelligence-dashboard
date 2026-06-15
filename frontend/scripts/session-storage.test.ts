import { strict as assert } from 'node:assert';

import {
  ACTIVE_WORKSPACE_STORAGE_KEY,
  ACTIVE_WORKSPACE_TOKEN_STORAGE_KEY,
  ADMIN_TOKEN_STORAGE_KEY,
} from '../src/constants/workspace';
import { clearStoredSession } from '../src/utils/session';

class MemoryStorage {
  private readonly values = new Map<string, string>();

  getItem(key: string): string | null {
    return this.values.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value);
  }

  removeItem(key: string): void {
    this.values.delete(key);
  }
}

const storage = new MemoryStorage();
storage.setItem(ADMIN_TOKEN_STORAGE_KEY, 'owner-passcode');
storage.setItem(ACTIVE_WORKSPACE_STORAGE_KEY, 'workspace-123');
storage.setItem(ACTIVE_WORKSPACE_TOKEN_STORAGE_KEY, 'workspace-token');
storage.setItem('unrelated-setting', 'keep-me');

clearStoredSession(storage);

assert.equal(storage.getItem(ADMIN_TOKEN_STORAGE_KEY), null);
assert.equal(storage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY), null);
assert.equal(storage.getItem(ACTIVE_WORKSPACE_TOKEN_STORAGE_KEY), null);
assert.equal(storage.getItem('unrelated-setting'), 'keep-me');
