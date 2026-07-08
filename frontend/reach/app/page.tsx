import Button from "@/components/ui/Button";
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
    <div className="w-full md:w-1/2 flex flex-col items-start text-left gap-4 md:justify-center">
          <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground p-0 m-0 leading-none">
            Find anything,
            </h1>
            <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground p-0 m-0 leading-none">
            close to home.
          </h1>
          <p className="text-base text-muted-foreground leading-relaxed max-w-xs md:max-w-none">
            From a bag of rice to a plumber who can come now — it&apos;s all a
            tap away.
          </p>
          <div className="w-full flex flex-col gap-3 pt-2">
            <Button href="/auth/location" intent="action" variant="primary" className="text-base">
              Get started
            </Button>
            <Link
              href="/auth/signin"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors duration-200 font-semibold text-center md:text-left md:pl-2"
            >
              I already have an account
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}