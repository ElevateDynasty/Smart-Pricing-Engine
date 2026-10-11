import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "ApexPricing AI | Enterprise Retail Dynamic Pricing & Lifecycle Engine",
  description: "AI-powered dynamic pricing, demand forecasting, price elasticity estimation, and inventory lifecycle optimization for consumer electronics retail.",
  keywords: ["dynamic pricing", "retail AI", "inventory optimization", "price elasticity", "LightGBM", "lifecycle optimization"],
  openGraph: {
    title: "ApexPricing AI - Intelligent Retail Dynamic Pricing Engine",
    description: "Maximizing gross margins across offline and multi-store electronics retail while strictly enforcing Legal Metrology MRP limits.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-black text-white">{children}</body>
    </html>
  );
}
