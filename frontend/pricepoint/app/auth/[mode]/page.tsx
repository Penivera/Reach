import { notFound } from "next/navigation";
import SignInForm from "@/components/SignInForm";
import SignUpForm from "@/components/SignUpForm";

interface AuthPageProps {
  params: Promise<{ mode: string }>;
}

export default async function AuthPage({ params }: AuthPageProps) {
  const { mode } = await params;

  if (mode !== "signin" && mode !== "signup") {
    notFound();
  }

  const isSignIn = mode === "signin";

  return (
<div className="relative min-h-screen text-foreground flex items-center justify-center p-6">

      <div id="auth-bg" aria-hidden="true" />
      <div className="w-full max-w-md md:max-w-lg border border-foreground bg-background p-6 rounded-lg space-y-6 shadow-md">
        
        <div className="space-y-1 text-center">
          <h2 className="text-2xl font-bold tracking-tight">
            {isSignIn ? "Welcome back" : "Create an account"}
          </h2>
          <p className="text-xs font-semibold text-muted-foreground">
            {isSignIn 
              ? "Log into your Pricepoint account" 
              : "Get started with Pricepoint today"}
          </p>
        </div>

        {/* Dynamic Form Render */}
        {isSignIn ? <SignInForm /> : <SignUpForm />}

      </div>
    </div>
  );
}