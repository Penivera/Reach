import PaymentProfileForm from "@/components/layout/PaymentProfileForm";

export default function PaymentProfilePage() {
  return (
    <div className="relative min-h-screen text-foreground flex items-center justify-center p-6">
      <div
        id="auth-bg"
        aria-hidden="true"
        className="hidden md:block"
      />
      <div className="w-full max-w-lg md:max-w-lg border-0 bg-background p-6 rounded-lg space-y-6 md:shadow-md md:border md:border-foreground">
        <div className="space-y-1 text-left">
          <h2 className="text-3xl font-bold tracking-tight">Complete your profile</h2>
          <p className="text-sm text-muted-foreground">
            We need a few more details to set up your secure FossaPay wallet before you can transact.
          </p>
        </div>
        <PaymentProfileForm />
      </div>
    </div>
  );
}