import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

const port = Number(process.env.GAMIFICATION_SERVICE_PORT || 4006);

app.get('/health', (_req, res) => res.json({ ok: true }));

// Stub: compute progress and badges
app.post('/api/v1/gamification/progress', (req, res) => {
  const { currentStep, totalSteps } = req.body || {};
  const pct = totalSteps ? Math.round((currentStep / totalSteps) * 100) : 0;
  res.json({ percentage: pct, badges: [] });
});

app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`gamification-service listening on http://localhost:${port}`);
});

