"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { getEnv } from "../../../../lib/config";
import { ProgressTracker } from "../../../../components/ProgressTracker";

const schema = z.object({
  state: z.string().min(2).max(2),
  licenseNumber: z.string().min(3)
});

export default function LicensePage() {
  const params = useParams<{ contractorId: string }>();
  const router = useRouter();
  const { register, handleSubmit, formState: { errors }, watch } = useForm<{ state: string; licenseNumber: string }>({ resolver: zodResolver(schema) });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(values: { state: string; licenseNumber: string }) {
    setError(null);
    setLoading(true);
    try {
      const base = getEnv().CONTRACTOR_BASE;
      // Save progress only (stub; real impl would persist license entity)
      const res = await fetch(`${base}/api/v1/contractors/${params.contractorId}/progress`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ currentStep: 3, completedSteps: [1, 2], validationErrors: null })
      });
      if (!res.ok) throw new Error('Failed to save');
      router.push(`/onboarding/${params.contractorId}/insurance`);
    } catch (e: any) {
      setError(e.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ padding: 24, maxWidth: 640 }}>
      <ProgressTracker currentStep={3} totalSteps={5} completedSections={[1,2]} />
      <h1>License Information</h1>
      <form onSubmit={handleSubmit(onSubmit)}>
        <label htmlFor="state">State</label>
        <input id="state" placeholder="TX" maxLength={2} {...register('state')} style={{ display: 'block', padding: 12, marginTop: 8, marginBottom: 4 }} />
        {errors.state && <span role="alert" style={{ color: '#b00020' }}>{errors.state.message}</span>}

        <label htmlFor="licenseNumber">License Number</label>
        <input id="licenseNumber" {...register('licenseNumber')} style={{ display: 'block', padding: 12, marginTop: 8, marginBottom: 4 }} />
        {errors.licenseNumber && <span role="alert" style={{ color: '#b00020' }}>{errors.licenseNumber.message}</span>}

        <button type="submit" disabled={loading} style={{ padding: 12, marginTop: 12 }}>{loading ? 'Saving...' : 'Continue'}</button>
      </form>
      {error && <p role="alert" style={{ color: '#b00020', marginTop: 12 }}>{error}</p>}
    </main>
  );
}

