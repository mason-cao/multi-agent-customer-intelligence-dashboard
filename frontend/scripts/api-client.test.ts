import { strict as assert } from 'node:assert';
import { afterEach, beforeEach, test } from 'node:test';
import api, { getWorkspaceCredentials } from '../src/api/client';
import { ApiError, getApiErrorDetail, getApiErrorStatus } from '../src/api/errors';
import { clearDashboardQueries } from '../src/api/workspaceQueries';
import { QueryClient } from '@tanstack/react-query';
import {
  ACTIVE_WORKSPACE_STORAGE_KEY as WORKSPACE_ID,
  ACTIVE_WORKSPACE_TOKEN_STORAGE_KEY as WORKSPACE_TOKEN,
  ADMIN_TOKEN_STORAGE_KEY,
  WORKSPACE_MISSING_EVENT,
} from '../src/constants/workspace';

const originalFetch = globalThis.fetch;
const originalWindow = Object.getOwnPropertyDescriptor(globalThis, 'window');
const originalStorage = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
let storage: Map<string, string>;

beforeEach(() => {
  storage = new Map([[WORKSPACE_ID, 'workspace-a'], [WORKSPACE_TOKEN, 'token-a']]);
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
  } });
  Object.defineProperty(globalThis, 'window', { configurable: true, value: new EventTarget() });
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  for (const [key, descriptor] of [['window', originalWindow], ['localStorage', originalStorage]] as const) {
    if (descriptor) Object.defineProperty(globalThis, key, descriptor);
    else Reflect.deleteProperty(globalThis, key);
  }
});

test('requests send credentials, JSON, and the caller cancellation signal', async () => {
  const controller = new AbortController();
  storage.set(ADMIN_TOKEN_STORAGE_KEY, 'owner-token');
  globalThis.fetch = async (url, init) => {
    assert.equal(url, '/api/query');
    assert.equal(init?.signal, controller.signal);
    const headers = new Headers(init?.headers);
    assert.equal(headers.get('X-Workspace-ID'), 'workspace-a');
    assert.equal(headers.get('X-Workspace-Token'), 'token-a');
    assert.equal(headers.get('X-Admin-Token'), 'owner-token');
    assert.equal(init?.body, JSON.stringify({ question: 'summary' }));
    return Response.json({ answer: 'ok' });
  };
  assert.deepEqual(await api.post('/query', { question: 'summary' }, { signal: controller.signal }), { answer: 'ok' });
});

test('a delayed missing-workspace response cannot clear a newly selected workspace', async () => {
  let finish!: (response: Response) => void;
  globalThis.fetch = () => new Promise<Response>((resolve) => { finish = resolve; });
  const pending = api.get('/overview/kpis');
  storage.set(WORKSPACE_ID, 'workspace-b');
  storage.set(WORKSPACE_TOKEN, 'token-b');
  finish(Response.json({ detail: 'Workspace database not found: workspace-a' }, { status: 404 }));
  await assert.rejects(pending, ApiError);
  assert.equal(storage.get(WORKSPACE_ID), 'workspace-b');
  assert.equal(storage.get(WORKSPACE_TOKEN), 'token-b');
});

test('query retries retain captured workspace credentials after a switch', async () => {
  const workspace = getWorkspaceCredentials();
  storage.set(WORKSPACE_ID, 'workspace-b');
  storage.set(WORKSPACE_TOKEN, 'token-b');
  globalThis.fetch = async (_url, init) => {
    const headers = new Headers(init?.headers);
    assert.equal(headers.get('X-Workspace-ID'), 'workspace-a');
    assert.equal(headers.get('X-Workspace-Token'), 'token-a');
    return Response.json({});
  };
  await api.get('/overview/kpis', { workspace });
});

test('a missing active workspace clears its credentials and emits one event', async () => {
  let notifications = 0;
  window.addEventListener(WORKSPACE_MISSING_EVENT, () => notifications++);
  globalThis.fetch = async () => Response.json({ detail: "This workspace doesn't exist." }, { status: 404 });
  await assert.rejects(api.get('/overview/kpis'), ApiError);
  assert.equal(storage.has(WORKSPACE_ID), false);
  assert.equal(storage.has(WORKSPACE_TOKEN), false);
  assert.equal(notifications, 1);
});

test('a missing unrelated workspace does not clear the current one', async () => {
  globalThis.fetch = async () => Response.json({ detail: "This workspace doesn't exist." }, { status: 404 });
  await assert.rejects(api.get('/workspaces/unrelated'), ApiError);
  assert.equal(storage.get(WORKSPACE_ID), 'workspace-a');
});

test('HTTP validation errors expose shared status and detail, including FastAPI arrays', async () => {
  globalThis.fetch = async () => Response.json({ detail: [{ msg: 'Invalid name' }] }, { status: 422 });
  await assert.rejects(api.post('/workspaces', {}), (error: unknown) => {
    assert.equal(getApiErrorStatus(error), 422);
    assert.equal(getApiErrorDetail(error), 'Invalid name');
    return true;
  });
});

test('empty DELETE responses and non-JSON proxy errors are handled', async () => {
  globalThis.fetch = async () => new Response(null, { status: 204 });
  assert.equal(await api.delete('/workspaces/workspace-a'), undefined);
  globalThis.fetch = async () => new Response('Bad gateway', { status: 502 });
  await assert.rejects(api.get('/health'), (error: unknown) => getApiErrorStatus(error) === 502);
});

test('clearing one workspace cancels its in-flight requests and preserves other caches', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  let aborted = false;
  const pending = client.fetchQuery({
    queryKey: ['dashboard', 'workspace-a', 'customers'],
    queryFn: ({ signal }) => new Promise((_resolve, reject) => {
      signal.addEventListener('abort', () => { aborted = true; reject(new Error('aborted')); });
    }),
  });
  client.setQueryData(['dashboard', 'workspace-b', 'customers'], ['keep']);
  client.setQueryData(['query', 'suggestions'], ['keep']);
  clearDashboardQueries(client, 'workspace-a');
  await assert.rejects(pending);
  assert.equal(aborted, true);
  assert.equal(client.getQueryState(['dashboard', 'workspace-a', 'customers']), undefined);
  assert.deepEqual(client.getQueryData(['dashboard', 'workspace-b', 'customers']), ['keep']);
  assert.deepEqual(client.getQueryData(['query', 'suggestions']), ['keep']);
  client.clear();
});
