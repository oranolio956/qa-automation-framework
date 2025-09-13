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
  res.status(200).json({ received: true });
});

app.post('/webhooks/veriforce', (req, res) => {
  if (!verifySignature(req)) return res.status(401).json({ error: 'invalid signature' });
  res.status(200).json({ received: true });
});

app.post('/webhooks/plaid', (req, res) => {
  if (!verifySignature(req)) return res.status(401).json({ error: 'invalid signature' });
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

const port = Number(process.env.VERIFICATION_SERVICE_PORT || 4007);
app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`verification-service listening on http://localhost:${port}`);
});

