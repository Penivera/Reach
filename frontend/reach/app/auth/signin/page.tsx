import SignInForm from "@/components/layout/SignInForm";

export default function SignInPage() {
  return (
    <div className="relative min-h-screen text-foreground flex items-center justify-center p-6">
      <div
        id="auth-bg"
        aria-hidden="true"
        className="hidden md:block"
      />
      <div className="w-full max-w-lg md:max-w-lg border-0 bg-background p-6 rounded-lg space-y-6 md:shadow-md md:border md:border-foreground">
        <div className="space-y-1 text-left">
          <h2 className="text-3xl font-bold tracking-tight">Welcome back</h2>
          <p className="text-xs font-semibold text-muted-foreground">
            Log into your Reach account
          </p>
        </div>
        <SignInForm />
      </div>
    </div>
  );
}