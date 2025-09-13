"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { getEnv } from "../../../../lib/config";

export default function DocumentsPage() {
  const params = useParams<{ contractorId: string }>();
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function requestUpload() {
    setError(null);
    setMessage(null);
    if (!file) return setError("Select a file first");
    try {
      const base = getEnv().DOCUMENT_BASE;
      const res = await fetch(`${base}/api/v1/documents/upload-intent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'license', mimeType: file.type, size: file.size })
      });
      if (!res.ok) throw new Error('Failed to create upload intent');
      const data = await res.json();
      const put = await fetch(data.uploadUrl, { method: 'PUT', body: file, headers: { 'Content-Type': file.type } });
      if (!put.ok) throw new Error('Upload failed');
      setMessage('Upload successful. Processing...');
    } catch (e: any) {
      setError(e.message || 'Something went wrong');
    }
  }

  return (
    <main style={{ padding: 24, maxWidth: 640 }}>
      <h1>Upload Documents</h1>
      <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      <button onClick={requestUpload} style={{ padding: 12, marginLeft: 12 }}>Upload</button>
      {message && <p style={{ color: '#0a7' }}>{message}</p>}
      {error && <p style={{ color: '#b00020' }}>{error}</p>}
    </main>
  );
}

