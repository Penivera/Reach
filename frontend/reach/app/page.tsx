import Button from "@/components/Button";
import Image from "next/image";
import Link from "next/link";

const HERO_IMAGE =
  "https://images.unsplash.com/photo-1572402123736-c79526db405a?q=80&w=870&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D";

export default function Home() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-6 py-12">
<div className="w-full max-w-5xl flex flex-col md:flex-row gap-10 md:gap-16">

  {/* Image */}
  <div className="w-full md:w-1/2 flex justify-center">
    <div className="w-full max-w-sm aspect-square md:max-w-none md:aspect-auto md:h-full rounded-2xl overflow-hidden">
      <Image
        src={HERO_IMAGE}
        alt="Find anything close to home"
        width={437}
        height={437}
        className="w-full h-full object-cover"
        priority
      />
    </div>
  </div>

        {/* Content */}
    <div className="w-full md:w-1/2 flex flex-col items-center md:items-start text-center md:text-left gap-4 md:justify-center">
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-foreground leading-snug">
            Find anything,
            <br />
            close to home.
          </h1>
          <p className="text-base text-muted-foreground leading-relaxed max-w-xs md:max-w-none">
            From a bag of rice to a plumber who can come now — it&apos;s all a
            tap away.
          </p>
          <div className="flex flex-col items-center md:items-start gap-3 pt-2">
            <Button href="/auth/signup" intent="action" variant="primary" className="text-base">
              Get started
            </Button>
            <Link
              href="/auth/signin"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors duration-200 font-semibold"
            >
              I already have an account
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}