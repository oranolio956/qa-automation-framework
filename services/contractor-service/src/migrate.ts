import dotenv from 'dotenv';
import { Pool } from 'pg';

dotenv.config();

const sql = `
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS contractor (
  id UUID PRIMARY KEY,
  auth0_user_id TEXT UNIQUE NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS onboarding_progress (
  contractor_id UUID PRIMARY KEY REFERENCES contractor(id) ON DELETE CASCADE,
  current_step INTEGER NOT NULL DEFAULT 1,
  completed_steps INTEGER[] NOT NULL DEFAULT '{}',
  validation_errors JSONB,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS license (
  id UUID PRIMARY KEY,
  contractor_id UUID NOT NULL REFERENCES contractor(id) ON DELETE CASCADE,
  state TEXT NOT NULL,
  license_number TEXT NOT NULL,
  license_type TEXT,
  expiration_date DATE,
  status TEXT NOT NULL DEFAULT 'unverified',
  verified_at TIMESTAMPTZ,
  UNIQUE(contractor_id, state, license_number)
);

CREATE TYPE IF NOT EXISTS insurance_coverage AS ENUM ('gl', 'wc', 'auto', 'umbrella');
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'insurance_coverage') THEN
    CREATE TYPE insurance_coverage AS ENUM ('gl', 'wc', 'auto', 'umbrella');
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS insurance_policy (
  id UUID PRIMARY KEY,
  contractor_id UUID NOT NULL REFERENCES contractor(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  policy_number TEXT NOT NULL,
  coverage_types insurance_coverage[] DEFAULT ARRAY['gl']::insurance_coverage[],
  expiration_date DATE,
  verification_status TEXT NOT NULL DEFAULT 'pending',
  additional_insured BOOLEAN DEFAULT false,
  last_checked_at TIMESTAMPTZ
);
`;

async function run() {
  const pool = new Pool({ connectionString: process.env.POSTGRES_URL });
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await client.query(sql);
    await client.query('COMMIT');
    // eslint-disable-next-line no-console
    console.log('Migrations executed successfully');
  } catch (err) {
    await client.query('ROLLBACK');
    // eslint-disable-next-line no-console
    console.error('Migration failed', err);
    process.exitCode = 1;
  } finally {
    client.release();
    await pool.end();
  }
}

run();

