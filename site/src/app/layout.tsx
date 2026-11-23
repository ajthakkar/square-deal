import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";
import { Public_Sans } from "next/font/google";
import "./globals.css";
import meta from "../../public/data/meta.json";

const sans = Public_Sans({ variable: "--font-sans-face", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Square Deal: check your Franklin County home value", template: "%s · Square Deal" },
  description:
    "A free check of your 2026 Franklin County property value against what similar homes nearby sold for, with the comparable sales and how to file with the Board of Revision.",
};

const nav = [
  { href: "/", label: "Check a home" },
  { href: "/how-to-file/", label: "How to file" },
  { href: "/fairness/", label: "Countywide fairness" },
  { href: "/method/", label: "How it works" },
];

const GOAT = process.env.NEXT_PUBLIC_GOATCOUNTER;

function dataDate() {
  if (!meta.data_date) return "";
  const [y, m, d] = meta.data_date.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${sans.variable} min-h-screen antialiased`}>
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-card focus:px-3 focus:py-2">
          Skip to content
        </a>
        <header className="border-b border-line bg-card">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
            <Link href="/" className="flex items-center gap-2 text-lg font-bold tracking-tight text-ink">
              <span aria-hidden className="inline-block h-4 w-4 rounded-[3px] border-[3px] border-accent" />
              Square Deal
            </Link>
            <nav aria-label="Main" className="flex flex-wrap gap-x-5 gap-y-1 text-[15px]">
              {nav.map((n) => (
                <Link key={n.href} href={n.href} className="text-copy underline-offset-4 hover:text-accent hover:underline">
                  {n.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main id="main" className="mx-auto max-w-5xl px-4 pb-16 sm:px-6">
          {children}
        </main>
        <footer className="border-t border-line bg-card">
          <div className="mx-auto max-w-5xl space-y-2 px-4 py-8 text-sm text-muted sm:px-6">
            <p>
              <strong className="text-copy">Not affiliated with the Franklin County Auditor.</strong> Not legal or tax advice, and not an
              appraisal. Built from the county&apos;s public data{dataDate() ? `, as published ${dataDate()}` : ""}. Owner names are never shown.
            </p>
            <p>
              Made by Aayush Thakkar, a student at Ohio State.{" "}
              <Link href="/about/" className="underline underline-offset-4 hover:text-accent">About this project</Link> ·{" "}
              <a href="https://github.com/ajthakkar/square-deal" className="underline underline-offset-4 hover:text-accent">Code and data on GitHub</a>
            </p>
          </div>
        </footer>
        {GOAT && <Script data-goatcounter={`https://${GOAT}.goatcounter.com/count`} src="https://gc.zgo.at/count.js" strategy="afterInteractive" />}
      </body>
    </html>
  );
}
