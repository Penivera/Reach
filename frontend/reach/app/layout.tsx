import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import Providers from "@/providers/Providers";
import Toaster from "@/components/ui/Toaster";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Reach",
  description: "Hire someone on Reach today!",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`min-h-full flex flex-col ${jakarta.className}`}>
        <Providers>{children}</Providers>
        <Toaster />
      </body>
    </html>
  );
}