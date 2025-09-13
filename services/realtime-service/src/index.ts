import dotenv from 'dotenv';
import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import { createAdapter } from 'socket.io-redis-adapter';
import { Cluster } from 'ioredis';

dotenv.config();

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, { cors: { origin: '*' } });

// Optional Redis adapter (requires Redis cluster)
if (process.env.REDIS_URL) {
  const url = new URL(process.env.REDIS_URL);
  const cluster = new Cluster([{ host: url.hostname, port: Number(url.port || 6379) }], {});
  // @ts-ignore
  io.adapter(createAdapter(cluster as any, cluster as any));
}

io.on('connection', (socket) => {
  const contractorId = socket.handshake.auth?.contractorId as string | undefined;
  if (contractorId) socket.join(`contractor:${contractorId}`);
  socket.emit('connected', { ok: true });
});

app.get('/health', (_req, res) => res.json({ ok: true }));

// Simple token auth via header for internal emits
app.post('/emit', (req, res) => {
  const token = req.header('x-internal-token');
  if (!process.env.INTERNAL_EMIT_TOKEN || token !== process.env.INTERNAL_EMIT_TOKEN) {
    return res.status(401).json({ error: 'unauthorized' });
  }
  const { room, event, payload } = req.body || {};
  if (!room || !event) return res.status(400).json({ error: 'room and event required' });
  io.to(room).emit(event, payload);
  res.json({ ok: true });
});

const port = Number(process.env.REALTIME_SERVICE_PORT || 4005);
httpServer.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`realtime-service listening on http://localhost:${port}`);
});

