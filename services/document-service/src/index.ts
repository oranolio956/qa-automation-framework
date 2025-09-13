import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import { randomUUID } from 'node:crypto';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

const port = Number(process.env.DOCUMENT_SERVICE_PORT || 4002);

const s3 = new S3Client({
  region: process.env.S3_REGION || 'us-east-1',
  endpoint: process.env.S3_ENDPOINT,
  forcePathStyle: process.env.S3_USE_PATH_STYLE === 'true',
  credentials: process.env.S3_ACCESS_KEY && process.env.S3_SECRET_KEY ? {
    accessKeyId: process.env.S3_ACCESS_KEY,
    secretAccessKey: process.env.S3_SECRET_KEY
  } : undefined
});

app.get('/health', (_req, res) => res.json({ ok: true }));

app.post('/api/v1/documents/upload-intent', async (req, res) => {
  const { type, mimeType, size, checksum } = req.body || {};
  if (!type || !mimeType || !size) {
    return res.status(400).json({ error: 'type, mimeType, size are required' });
  }
  try {
    const documentId = randomUUID();
    const key = `${type}/${documentId}`;
    const bucket = process.env.S3_BUCKET as string;
    const expiresIn = 60 * 5; // 5 minutes

    const command = new PutObjectCommand({ Bucket: bucket, Key: key, ContentType: mimeType });
    const uploadUrl = await getSignedUrl(s3, command, { expiresIn });
    const expiresAt = new Date(Date.now() + expiresIn * 1000).toISOString();
    res.json({ documentId, uploadUrl, expiresAt, checksum: checksum ?? null });
  } catch (err) {
    res.status(500).json({ error: 'Failed to create upload intent' });
  }
});

app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`document-service listening on http://localhost:${port}`);
});

