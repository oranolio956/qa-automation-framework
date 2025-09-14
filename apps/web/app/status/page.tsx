"use client";

import { useEffect, useState } from "react";
import { getSocket } from "../../lib/socket";

export default function StatusPage() {
  const [events, setEvents] = useState<string[]>([]);

  useEffect(() => {
    const socket = getSocket(localStorage.getItem('contractorId') || undefined);
    const handler = (e: unknown) => setEvents((prev) => [JSON.stringify(e), ...prev].slice(0, 20));
    socket.on('verification:started', handler);
    socket.on('verification:completed', handler);
    socket.on('progress:updated', handler);
    socket.on('badge:unlocked', handler);
    return () => {
      socket.off('verification:started', handler);
      socket.off('verification:completed', handler);
      socket.off('progress:updated', handler);
      socket.off('badge:unlocked', handler);
    };
  }, []);

  return (
    <main style={{ padding: 24 }}>
      <h1>Status Events</h1>
      <ul>
        {events.map((e, i) => (
          <li key={i} style={{ fontFamily: 'monospace' }}>{e}</li>
        ))}
      </ul>
    </main>
  );
}

