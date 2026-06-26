import Button from "@/components/Button";

export default function Home() {
  return (
    <div className="text-foreground min-h-screen flex flex-col items-center justify-center bg-background px-4">
      <div className="text-center space-y-6 max-w-md w-full">
        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight">
          Pricepoint
        </h1>
        
        <div className="flex justify-center pt-2">
          {/* Internal Link routing */}
          <Button href="/signin" intent="action" variant="primary" className="text-base shadow-sm">
            Get Started
          </Button>
        </div>
      </div>
    </div>
  );
}