"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { 
  ArrowLeft, 
  ForkKnife, 
  Wrench, 
  Truck, 
  Scissors, 
  BookOpen, 
  SprayBottle 
} from "@phosphor-icons/react";
import Button from "@/components/ui/Button";
import StepIndicator from "@/components/ui/StepIndicator";

const INTERESTS = [
  { id: "food", label: "Daily Food", icon: ForkKnife },
  { id: "repairs", label: "Home Repairs", icon: Wrench },
  { id: "deliveries", label: "Deliveries", icon: Truck },
  { id: "beauty", label: "Beauty/Hair", icon: Scissors },
  { id: "tutoring", label: "Tutoring", icon: BookOpen },
  { id: "cleaning", label: "Cleaning", icon: SprayBottle },
];

export default function InterestsPage() {
  const router = useRouter();
  const [selected, setSelected] = useState<string[]>([]);

  const toggleInterest = (id: string) => {
    setSelected((prev) => 
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleContinue = () => {
    // Save interests to API here if needed, then route to the next step
    router.push("/auth/signup"); // Adjust this route based on your auth flow
  };

  return (
    <div className="flex min-h-screen flex-col bg-background px-6 py-8">
      {/* Header */}
      <header className="flex w-full items-center justify-between pb-6">
        <button 
          onClick={() => router.back()} 
          className="p-2 -ml-2 text-foreground active:scale-95 transition-transform"
          aria-label="Go back"
        >
          <ArrowLeft size={24} weight="bold" />
        </button>
        <Link 
          href="/home" 
          className="text-sm font-semibold text-muted-foreground hover:text-foreground transition-colors"
        >
          Skip
        </Link>
      </header>

      {/* Content */}
      <div className="flex w-full flex-col gap-2 pt-2">
        <h1 className="text-3xl font-extrabold tracking-tight text-foreground leading-tight">
          What are you looking<br />for today?
        </h1>
        <p className="text-sm font-medium text-muted-foreground leading-relaxed mt-1">
          Select your main interests to help us customize your local feed. You can change this anytime.
        </p>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-2 gap-4 mt-8">
        {INTERESTS.map(({ id, label, icon: Icon }) => {
          const isSelected = selected.includes(id);
          
          return (
            <button
              key={id}
              onClick={() => toggleInterest(id)}
              className={`flex flex-col items-start justify-center gap-3 rounded-2xl border p-4 transition-colors duration-200 ${
                isSelected 
                  ? "border-primary bg-[#FFF1ED] text-primary" 
                  : "border-neutral-200 bg-transparent text-foreground hover:border-neutral-300"
              }`}
            >
              <Icon size={28} weight={isSelected ? "fill" : "regular"} className={isSelected ? "text-primary" : "text-neutral-600"} />
              <span className={`text-sm tracking-tight ${isSelected ? "font-bold text-foreground" : "font-semibold"}`}>
                {label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Bottom Actions */}
      <div className="w-full flex flex-col gap-6 pt-8 mt-auto pb-4">
        <StepIndicator currentStep={3} totalSteps={3} />
        
        <Button 
          intent="action" 
          variant="primary" 
          className="text-base font-semibold"
          onClick={handleContinue}
        >
          Continue Sign up
        </Button>
      </div>
    </div>
  );
}