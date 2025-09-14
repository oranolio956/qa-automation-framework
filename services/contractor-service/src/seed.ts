import dotenv from 'dotenv';
import { Pool } from 'pg';
import { randomUUID } from 'node:crypto';

dotenv.config();

async function run() {
  const pool = new Pool({ connectionString: process.env.POSTGRES_URL });
  try {
    const contractorId = randomUUID();
    await pool.query('INSERT INTO contractor (id, auth0_user_id, status) VALUES ($1, $2, $3)', [contractorId, `dev-${contractorId}`, 'pending']);
    // eslint-disable-next-line no-console
    console.log('Seeded contractorId=', contractorId);
  } finally {
    await pool.end();
  }
}

run();

