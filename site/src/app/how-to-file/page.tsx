import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "How to file a property value complaint in Franklin County",
  description: "The free Board of Revision process for challenging your 2026 Franklin County property value: the form, the deadline, and what evidence to bring.",
};

const BOR = "https://auditor.franklincountyohio.gov/Real-Estate/Board-of-Revision";
const FILING = "https://auditor.franklincountyohio.gov/Real-Estate/Board-of-Revision/Filing-Instructions";

export default function Page() {
  return (
    <article className="mx-auto max-w-3xl pt-10">
      <h1 className="text-3xl font-bold text-ink sm:text-4xl">How to challenge your 2026 value</h1>
      <p className="mt-3 text-lg text-copy">
        If you think the county valued your home above what it would have sold for on January 1, 2026, you can file a complaint with
        the Franklin County Board of Revision. It&apos;s free, you don&apos;t need a lawyer, and you can do it online.
      </p>

      <div className="mt-6 rounded-lg border-l-8 border-warn bg-warn-soft p-5 text-ink">
        <p className="font-semibold">Deadline: March 31, 2027</p>
        <p className="mt-1 text-copy">
          Complaints for tax year 2026 are due by March 31, 2027. In recent years the window has opened in the fall, after values are
          final. Late complaints are dismissed, so check the exact dates on the{" "}
          <a href={FILING} className="text-accent underline underline-offset-4">Auditor&apos;s filing instructions</a>.
        </p>
      </div>

      <ol className="mt-8 space-y-8">
        <Step n={1} title="Decide whether it's worth it">
          <p>
            You need to show what your home was worth on January 1, 2026. Ask: is the county&apos;s value above what similar homes
            nearby sold for? Does your home have problems the county&apos;s record doesn&apos;t show? Square Deal&apos;s check is a
            starting point, not proof.
          </p>
          <p>
            <strong>Be careful if your value looks low.</strong> The board can raise a value as well as lower it, and school
            districts can file their own complaints asking for higher values.
          </p>
        </Step>
        <Step n={2} title="Gather evidence">
          <p>The board decides on market value, so bring what shows it. From strongest to weakest:</p>
          <ul className="ml-5 list-disc space-y-1">
            <li>A recent arm&apos;s-length sale of your own home: the closing statement, purchase contract, or conveyance fee statement.</li>
            <li>A recent appraisal done for a sale or refinance, ideally close to January 1, 2026.</li>
            <li>Sales of similar homes nearby around that date, with how they compare to yours. Square Deal lists five and prints them.</li>
            <li>Photos and contractor estimates for problems: roof, foundation, water damage, outdated systems.</li>
          </ul>
        </Step>
        <Step n={3} title="File DTE Form 1">
          <p>
            The form is the <em>Complaint Against the Valuation of Real Property</em> (DTE 1). Franklin County accepts it online, by
            mail, or in person at 373 S. High St., 20th Floor, Columbus. Your value (from the Auditor&apos;s site) goes on the form
            along with the value you think is right and why.
          </p>
          <p>
            Start at the <a href={BOR} className="text-accent underline underline-offset-4">Board of Revision page</a>.
          </p>
        </Step>
        <Step n={4} title="Mediation or a hearing">
          <p>
            The county runs a free mediation program for property value disputes. If mediation doesn&apos;t settle it, you keep your
            right to a hearing before the three-member Board of Revision, where you present your evidence. You can appeal the
            board&apos;s decision to the Ohio Board of Tax Appeals.
          </p>
        </Step>
        <Step n={5} title="What changes if you win">
          <p>
            The board sets a new value for tax year 2026. In Ohio, a value set by the board generally stays in place until the
            county&apos;s next update. Your tax bill follows your value, though tax rates change too.
          </p>
        </Step>
      </ol>

      <p className="mt-10 text-sm text-muted">
        This page summarizes the county&apos;s published instructions as of November 2026. It isn&apos;t legal advice; the
        Auditor&apos;s office and the Board of Revision have the final word on the process.
      </p>
    </article>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <li className="flex gap-4">
      <span aria-hidden className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent font-bold text-accent-ink">{n}</span>
      <div className="prose-copy text-copy">
        <h2 className="text-xl font-semibold text-ink">{title}</h2>
        <div className="prose-copy mt-2">{children}</div>
      </div>
    </li>
  );
}
