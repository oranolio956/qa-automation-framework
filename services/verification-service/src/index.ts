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
  res.status(200).json({ received: true });
});

app.post('/webhooks/veriforce', (req, res) => {
  res.status(200).json({ received: true });
});

app.post('/webhooks/plaid', (req, res) => {
  res.status(200).json({ received: true });
});

const port = Number(process.env.VERIFICATION_SERVICE_PORT || 4007);
app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`verification-service listening on http://localhost:${port}`);
});

