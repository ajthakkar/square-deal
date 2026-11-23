import type { Metadata } from "next";

export const metadata: Metadata = { title: "About", description: "Who made Square Deal, why, and what it does with your data." };

const FEEDBACK = process.env.NEXT_PUBLIC_FEEDBACK_URL;

export default function Page() {
  return (
    <article className="mx-auto max-w-3xl pt-10">
      <h1 className="text-3xl font-bold text-ink sm:text-4xl">About Square Deal</h1>
      <div className="prose-copy mt-4 text-lg text-copy">
        <p>
          I&apos;m Aayush Thakkar, a business student at Ohio State. Franklin County updated every property value for 2026, and owners
          who think theirs is wrong have until March 31, 2027 to challenge it. The county explains the process well, but it
          doesn&apos;t show you how your value compares with what similar homes sold for, and that&apos;s the evidence the Board of
          Revision asks for. Paid services will pull those sales for you. Square Deal does it for free, for every single-family home in
          the county, and shows its work.
        </p>
        <p>
          It&apos;s an independent student project. It isn&apos;t affiliated with the Franklin County Auditor or any government office,
          and it isn&apos;t legal or tax advice.
        </p>
      </div>

      <h2 className="mt-10 text-xl font-bold text-ink">Your privacy</h2>
      <ul className="mt-2 list-disc space-y-2 pl-5 text-copy">
        <li>Every result is computed ahead of time and served as a static file. The address you type never leaves your browser.</li>
        <li>Property values, home details, and sales are public records. Square Deal never shows owner names.</li>
        <li>If visit counting is on, it uses GoatCounter, which sets no cookies and records only which page was viewed and which kind of result was shown, never an address.</li>
      </ul>

      <h2 className="mt-10 text-xl font-bold text-ink">Did it help?</h2>
      <p className="mt-2 text-copy">
        If you filed a complaint after using Square Deal, or found something wrong, I&apos;d like to hear how it went.
        {FEEDBACK ? (
          <> <a href={FEEDBACK} className="text-accent underline underline-offset-4">Tell me in a two-minute form</a>.</>
        ) : (
          <> Open an issue on <a href="https://github.com/ajthakkar/square-deal/issues" className="text-accent underline underline-offset-4">GitHub</a>.</>
        )}
      </p>

      <h2 className="mt-10 text-xl font-bold text-ink">Sources</h2>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-copy">
        <li>Franklin County Auditor, public appraisal and tax extracts and parcel maps</li>
        <li>IAAO, <em>Standard on Ratio Studies</em></li>
        <li>Christopher Berry, &quot;Reassessing the Property Tax,&quot; University of Chicago</li>
      </ul>
    </article>
  );
}
