import request from 'supertest';
import { createApp } from '../src/app';
import { Pool } from 'pg';

class MockPool extends Pool {
  async query() { return { rows: [{ '?column?': 1 }] } as any; }
}

test('health ok', async () => {
  const app = createApp(new MockPool() as any);
  const res = await request(app).get('/health');
  expect(res.status).toBe(200);
  expect(res.body.ok).toBe(true);
});