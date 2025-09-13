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

const port = Number(process.env.REALTIME_SERVICE_PORT || 4005);
httpServer.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`realtime-service listening on http://localhost:${port}`);
});

