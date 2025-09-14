"use client";

import { useParams, useRouter } from "next/navigation";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { getEnv } from "../../../../lib/config";
import { ProgressTracker } from "../../../../components/ProgressTracker";
import { useState } from "react";

const schema = z.object({
  provider: z.enum(["trustlayer", "veriforce", "manual"]),
  policyNumber: z.string().min(5),
  expirationDate: z.string()
});

export default function InsurancePage() {
  const params = useParams<{ contractorId: string }>();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors } } = useForm<{ provider: 'trustlayer'|'veriforce'|'manual'; policyNumber: string; expirationDate: string }>({ resolver: zodResolver(schema) });

  async function onSubmit(values: { provider: string; policyNumber: string; expirationDate: string }) {
    setError(null);
    setLoading(true);
    try {
      const base = getEnv().CONTRACTOR_BASE;
      const res = await fetch(`${base}/api/v1/contractors/${params.contractorId}/progress`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ currentStep: 4, completedSteps: [1,2,3], validationErrors: null })
      });
      if (!res.ok) throw new Error('Failed to save');
      router.push(`/onboarding/${params.contractorId}/documents`);
    } catch (e: any) {
      setError(e.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ padding: 24, maxWidth: 640 }}>
      <ProgressTracker currentStep={4} totalSteps={5} completedSections={[1,2,3]} />
      <h1>Insurance Information</h1>
      <form onSubmit={handleSubmit(onSubmit)}>
        <label htmlFor="provider">Provider</label>
        <select id="provider" {...register('provider')} style={{ display: 'block', padding: 12, marginTop: 8, marginBottom: 4 }}>
          <option value="trustlayer">TrustLayer</option>
          <option value="veriforce">Veriforce</option>
          <option value="manual">Manual</option>
        </select>
        {errors.provider && <span role="alert" style={{ color: '#b00020' }}>{String(errors.provider.message)}</span>}

        <label htmlFor="policyNumber">Policy Number</label>
        <input id="policyNumber" {...register('policyNumber')} style={{ display: 'block', padding: 12, marginTop: 8, marginBottom: 4 }} />
        {errors.policyNumber && <span role="alert" style={{ color: '#b00020' }}>{errors.policyNumber.message}</span>}

        <label htmlFor="expirationDate">Expiration Date</label>
        <input id="expirationDate" type="date" {...register('expirationDate')} style={{ display: 'block', padding: 12, marginTop: 8, marginBottom: 4 }} />
        {errors.expirationDate && <span role="alert" style={{ color: '#b00020' }}>{errors.expirationDate.message}</span>}

        <button type="submit" disabled={loading} style={{ padding: 12, marginTop: 12 }}>{loading ? 'Saving...' : 'Continue'}</button>
      </form>
      {error && <p role="alert" style={{ color: '#b00020', marginTop: 12 }}>{error}</p>}
    </main>
  );
}

