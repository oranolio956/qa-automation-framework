import React from 'react';

export interface ProgressProps {
  currentStep: number;
  totalSteps: number;
  completedSections: number[];
  onStepClick?: (step: number) => void;
}

export const ProgressTracker: React.FC<ProgressProps> = ({ currentStep, totalSteps, completedSections, onStepClick }) => {
  const percentage = Math.round((currentStep / totalSteps) * 100);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
      <div aria-label={`Progress ${percentage}%`} style={{ width: 60, height: 60, borderRadius: 30, border: '4px solid #0a7', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span>{percentage}%</span>
      </div>
      <ol style={{ display: 'flex', gap: 8, listStyle: 'none', padding: 0, margin: 0 }}>
        {Array.from({ length: totalSteps }, (_, i) => i + 1).map((step) => {
          const completed = completedSections.includes(step) || step < currentStep;
          return (
            <li key={step}>
              <button
                onClick={() => onStepClick?.(step)}
                aria-current={step === currentStep ? 'step' : undefined}
                style={{ width: 36, height: 36, borderRadius: 18, border: '1px solid #ccc', background: completed ? '#0a7' : step === currentStep ? '#eef' : '#fff', color: completed ? '#fff' : '#000' }}
              >
                {step}
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
};