import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { Pool } from 'pg';
import { randomUUID } from 'node:crypto';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

const port = Number(process.env.CONTRACTOR_SERVICE_PORT || 4001);
const pool = new Pool({ connectionString: process.env.POSTGRES_URL });

app.get('/health', async (_req, res) => {
  try {
    await pool.query('SELECT 1');
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ ok: false });
  }
});

app.post('/api/v1/contractors', async (req, res) => {
  const { auth0UserId, email } = req.body || {};
  if (!auth0UserId || !email) {
    return res.status(400).json({ error: 'auth0UserId and email are required' });
  }
  try {
    const contractorId = randomUUID();
    await pool.query(
      `INSERT INTO contractor (id, auth0_user_id, status) VALUES ($1, $2, 'pending')`,
      [contractorId, auth0UserId]
    );
    res.status(201).json({ contractorId });
  } catch (err) {
    res.status(500).json({ error: 'Failed to create contractor' });
  }
});

app.patch('/api/v1/contractors/:id/progress', async (req, res) => {
  const { id } = req.params;
  const { currentStep, completedSteps, validationErrors } = req.body || {};
  try {
    await pool.query(
      `INSERT INTO onboarding_progress (contractor_id, current_step, completed_steps, validation_errors, updated_at)
       VALUES ($1, $2, $3, $4, now())
       ON CONFLICT (contractor_id)
       DO UPDATE SET current_step = EXCLUDED.current_step, completed_steps = EXCLUDED.completed_steps, validation_errors = EXCLUDED.validation_errors, updated_at = now()`,
      [id, currentStep ?? 1, completedSteps ?? [], validationErrors ?? null]
    );
    if (process.env.REALTIME_EMIT_URL && process.env.INTERNAL_EMIT_TOKEN) {
      // Fire and forget; no blocking
      fetch(process.env.REALTIME_EMIT_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-internal-token': process.env.INTERNAL_EMIT_TOKEN },
        body: JSON.stringify({ room: `contractor:${id}`, event: 'progress:updated', payload: { contractorId: id, progress: currentStep } })
      }).catch(() => undefined);
    }
    res.json({ ok: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to update progress' });
  }
});

app.get('/api/v1/contractors/:id/status', async (req, res) => {
  const { id } = req.params;
  try {
    const [{ rows: cRows }, { rows: pRows }] = await Promise.all([
      pool.query('SELECT status FROM contractor WHERE id = $1', [id]),
      pool.query('SELECT current_step, completed_steps FROM onboarding_progress WHERE contractor_id = $1', [id])
    ]);
    if (cRows.length === 0) return res.status(404).json({ error: 'Not found' });
    const status = cRows[0].status;
    const progress = pRows[0] || { current_step: 1, completed_steps: [] };
    res.json({ status, currentStep: progress.current_step, completedSteps: progress.completed_steps });
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch status' });
  }
});

// License persistence (minimal)
app.post('/api/v1/contractors/:id/license', async (req, res) => {
  const { id } = req.params;
  const { state, licenseNumber, licenseType, expirationDate } = req.body || {};
  if (!state || !licenseNumber) return res.status(400).json({ error: 'state and licenseNumber required' });
  try {
    await pool.query(
      `INSERT INTO license (id, contractor_id, state, license_number, license_type, expiration_date, status)
       VALUES ($1, $2, $3, $4, $5, $6, 'unverified')
       ON CONFLICT (contractor_id, state, license_number)
       DO UPDATE SET license_type = EXCLUDED.license_type, expiration_date = EXCLUDED.expiration_date`,
      [randomUUID(), id, state, licenseNumber, licenseType ?? null, expirationDate ?? null]
    );
    res.status(201).json({ ok: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to save license' });
  }
});

// Insurance persistence (minimal)
app.post('/api/v1/contractors/:id/insurance', async (req, res) => {
  const { id } = req.params;
  const { provider, policyNumber, coverageTypes, expirationDate, additionalInsured } = req.body || {};
  if (!provider || !policyNumber) return res.status(400).json({ error: 'provider and policyNumber required' });
  try {
    await pool.query(
      `INSERT INTO insurance_policy (id, contractor_id, provider, policy_number, coverage_types, expiration_date, verification_status, additional_insured)
       VALUES ($1, $2, $3, $4, $5, $6, 'pending', $7)
       ON CONFLICT (id) DO NOTHING`,
      [randomUUID(), id, provider, policyNumber, coverageTypes ?? ['gl'], expirationDate ?? null, additionalInsured ?? false]
    );
    res.status(201).json({ ok: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to save insurance' });
  }
});

// Update statuses from verification-service
app.post('/api/v1/contractors/:id/license/status', async (req, res) => {
  const { id } = req.params;
  const { state, licenseNumber, status, verifiedAt } = req.body || {};
  if (!state || !licenseNumber || !status) return res.status(400).json({ error: 'state, licenseNumber, status required' });
  try {
    await pool.query(
      `UPDATE license SET status = $1, verified_at = $2 WHERE contractor_id = $3 AND state = $4 AND license_number = $5`,
      [status, verifiedAt ?? null, id, state, licenseNumber]
    );
    res.json({ ok: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to update license status' });
  }
});

app.post('/api/v1/contractors/:id/insurance/status', async (req, res) => {
  const { id } = req.params;
  const { policyNumber, verificationStatus, expirationDate, additionalInsured } = req.body || {};
  if (!policyNumber || !verificationStatus) return res.status(400).json({ error: 'policyNumber, verificationStatus required' });
  try {
    await pool.query(
      `UPDATE insurance_policy SET verification_status = $1, expiration_date = COALESCE($2, expiration_date), additional_insured = COALESCE($3, additional_insured), last_checked_at = now() WHERE contractor_id = $4 AND policy_number = $5`,
      [verificationStatus, expirationDate ?? null, additionalInsured ?? null, id, policyNumber]
    );
    res.json({ ok: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to update insurance status' });
  }
});

app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`contractor-service listening on http://localhost:${port}`);
});

