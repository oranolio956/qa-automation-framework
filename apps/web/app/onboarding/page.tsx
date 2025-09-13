"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { getEnv } from "../../lib/config";

export default function OnboardingStartPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStart() {
    setError(null);
    if (!email) {
      setError("Email is required");
      return;
    }
    setLoading(true);
    try {
      const base = getEnv().CONTRACTOR_BASE;
      const res = await fetch(`${base}/api/v1/contractors`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auth0UserId: `dev-${email}`, email })
      });
      if (!res.ok) throw new Error("Failed to create contractor");
      const data = (await res.json()) as { contractorId: string };
      localStorage.setItem("contractorId", data.contractorId);
      router.push(`/onboarding/${data.contractorId}/business`);
    } catch (e: any) {
      setError(e.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ padding: 24, maxWidth: 520 }}>
      <h1>Welcome & Quick Start</h1>
      <p>Start your registration. It only takes a few minutes.</p>
      <label htmlFor="email">Email</label>
      <input
        id="email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@business.com"
        style={{ display: "block", width: "100%", padding: 12, marginTop: 8, marginBottom: 12 }}
      />
      <button onClick={handleStart} disabled={loading} style={{ padding: 12 }}>
        {loading ? "Starting..." : "Start Registration"}
      </button>
      {error && (
        <p role="alert" style={{ color: "#b00020", marginTop: 12 }}>
          {error}
        </p>
      )}
    </main>
  );
}

