"use client";

interface StepIndicatorProps {
  totalSteps?: number;
  currentStep: number;
}

export default function StepIndicator({ totalSteps = 3, currentStep }: StepIndicatorProps) {
  return (
    <div className="flex items-center justify-center w-full gap-1.5 my-6">
      {Array.from({ length: totalSteps }).map((_, index) => {
        const step = index + 1;
        const isActive = step === currentStep;
        
        return (
          <div
            key={step}
            className={`h-1.5 rounded-full transition-all duration-300 ${
              isActive ? "w-4 bg-primary" : "w-1.5 bg-neutral-300"
            }`}
          />
        );
      })}
    </div>
  );
}