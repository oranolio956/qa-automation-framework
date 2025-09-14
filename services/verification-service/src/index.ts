import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

app.get('/health', (_req, res) => res.json({ ok: true }));

// Webhook stubs
app.post('/webhooks/trustlayer', (req, res) => {
  if (!verifySignature(req)) return res.status(401).json({ error: 'invalid signature' });
  forward('insurance', req.body).catch(() => undefined);
  res.status(200).json({ received: true });
});

app.post('/webhooks/veriforce', (req, res) => {
  if (!verifySignature(req)) return res.status(401).json({ error: 'invalid signature' });
  forward('insurance', req.body).catch(() => undefined);
  res.status(200).json({ received: true });
});

app.post('/webhooks/plaid', (req, res) => {
  if (!verifySignature(req)) return res.status(401).json({ error: 'invalid signature' });
  forward('bank', req.body).catch(() => undefined);
  res.status(200).json({ received: true });
});

function verifySignature(req: any): boolean {
  const sig = req.header('x-signature') || '';
  const secret = process.env.WEBHOOK_SECRET || '';
  if (!secret) return true; // dev mode
  const body = JSON.stringify(req.body || {});
  const crypto = require('node:crypto');
  const h = crypto.createHmac('sha256', secret).update(body).digest('hex');
  return crypto.timingSafeEqual(Buffer.from(h), Buffer.from(sig));
}

async function forward(kind: 'insurance'|'bank', payload: any) {
  const contractorId = payload.contractorId || payload.metadata?.contractorId;
  if (!contractorId) return;
  const emitUrl = process.env.REALTIME_EMIT_URL;
  const emitToken = process.env.INTERNAL_EMIT_TOKEN;
  const contractorBase = process.env.CONTRACTOR_BASE;

  if (kind === 'insurance' && contractorBase) {
    await fetch(`${contractorBase}/api/v1/contractors/${contractorId}/insurance/status`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ policyNumber: payload.policyNumber, verificationStatus: payload.status, expirationDate: payload.expirationDate, additionalInsured: payload.additionalInsured })
    });
  }
  if (emitUrl && emitToken) {
    await fetch(emitUrl, { method: 'POST', headers: { 'Content-Type': 'application/json', 'x-internal-token': emitToken }, body: JSON.stringify({ room: `contractor:${contractorId}`, event: 'verification:completed', payload }) });
  }
}

const port = Number(process.env.VERIFICATION_SERVICE_PORT || 4007);
app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`verification-service listening on http://localhost:${port}`);
});

