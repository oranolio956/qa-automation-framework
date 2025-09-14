"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { getEnv } from "../../../../lib/config";
import { loadDraft, saveDraft } from "../../../../lib/draftStore";
import { ProgressTracker } from "../../../../components/ProgressTracker";

export default function BusinessInfoPage() {
  const params = useParams<{ contractorId: string }>();
  const router = useRouter();
  const schema = z.object({
    legalName: z.string().min(2, 'Enter a valid legal name')
  });
  const { register, handleSubmit, formState: { errors }, watch } = useForm<{ legalName: string }>({ resolver: zodResolver(schema), defaultValues: { legalName: "" } });
  const legalName = watch('legalName');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params?.contractorId) return;
    loadDraft<string>(`business:${params.contractorId}`).then((d) => {
      if (d) setLegalName(d);
    });
  }, [params?.contractorId]);

  useEffect(() => {
    if (!params?.contractorId) return;
    const i = setInterval(() => {
      void saveDraft(`business:${params.contractorId}`, legalName);
    }, 30000);
    return () => clearInterval(i);
  }, [params?.contractorId, legalName]);

  async function saveAndNext() {
    setError(null);
    setLoading(true);
    try {
      const base = getEnv().CONTRACTOR_BASE;
      const res = await fetch(`${base}/api/v1/contractors/${params.contractorId}/progress`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ currentStep: 2, completedSteps: [1], validationErrors: null })
      });
      if (!res.ok) throw new Error("Failed to save progress");
      router.push(`/onboarding/${params.contractorId}/documents`);
    } catch (e: any) {
      setError(e.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ padding: 24, maxWidth: 640 }}>
      <ProgressTracker currentStep={2} totalSteps={5} completedSections={[1]} />
      <h1>Business Information</h1>
      <form onSubmit={handleSubmit(saveAndNext)}>
        <label htmlFor="legalName">Legal Business Name</label>
        <input
          id="legalName"
          {...register('legalName')}
          placeholder="Acme Lights LLC"
          style={{ display: "block", width: "100%", padding: 12, marginTop: 8, marginBottom: 4 }}
        />
        {errors.legalName && (
          <span role="alert" style={{ color: '#b00020', display: 'block', marginBottom: 12 }}>{errors.legalName.message}</span>
        )}
        <button type="submit" disabled={loading} style={{ padding: 12 }}>
        {loading ? "Saving..." : "Continue"}
        </button>
      </form>
      {error && (
        <p role="alert" style={{ color: "#b00020", marginTop: 12 }}>
          {error}
        </p>
      )}
    </main>
  );
}