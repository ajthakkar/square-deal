# Why Square Deal: how I picked this project

November 2026. I wanted my next project to be used by real people, to help them in a way I could measure, and to be relevant to the roles I'm applying for (data, finance, software, consulting). This is how I chose it.

## What strong projects have in common

I looked at student-built tools that reached real users and at work that changed something:

- **Campus tools.** Berkeleytime (course grades and enrollment, built by two Berkeley students) and Penn Labs (a student group that builds tools for Penn). Coursicle started as a student project at UNC. They work because they answer a question students already have, with data they can't easily get.
- **Data journalism that led to reform.** The Chicago Tribune and ProPublica's *The Tax Divide* showed that Cook County overvalued cheap homes and undervalued expensive ones. It led to a lawsuit and a new assessor.
- **Research.** Belot, Kircher, and Muller (Review of Economic Studies, 2019) found that a cheap online tool showing job seekers better information broadened their search and raised their interview rates. Information tools can change outcomes without costing much.
- **What hiring managers say they want.** A few deep projects with business context and a clear result, not tutorial copies.

## Criteria (weight)

1. **Reach and need (25%).** How many people have the problem, and how much does it cost them?
2. **A path to real users within about two months (20%).** A way to reach them, and a reason for them to come now.
3. **Fit with my target roles (15%).** Data, finance, software, consulting.
4. **Differentiation (15%).** Is there already a free, good answer?
5. **Measurable impact (10%).** Can I show numbers: people helped, money saved, a finding someone acts on?
6. **Feasibility for one student, free to run (10%).** Public data, no paid APIs, static hosting.
7. **Risk (5%).** Legal, privacy, and harm if the tool is wrong.

## Options, scored 1–5

| Option | Reach | Users | Roles | Different | Impact | Doable | Risk | **Weighted** |
|---|---|---|---|---|---|---|---|---|
| **Square Deal**: is your Franklin County home value in line with what similar homes sold for? | 5 | 5 | 4 | 4 | 5 | 4 | 3 | **4.50** |
| Fast-updating list of business internships (finance, consulting) | 4 | 3 | 4 | 2 | 3 | 3 | 4 | 3.30 |
| Ohio State course seats: when classes fill | 4 | 4 | 3 | 2 | 3 | 3 | 3 | 3.30 |
| Columbus rent fairness checker | 4 | 2 | 4 | 3 | 2 | 2 | 2 | 2.95 |
| SNAP eligibility guide for Ohio college students | 3 | 3 | 2 | 3 | 4 | 3 | 2 | 2.90 |
| Columbus hospital price comparison | 4 | 2 | 4 | 2 | 3 | 1 | 3 | 2.85 |
| COTA bus reliability tracker | 3 | 2 | 3 | 3 | 2 | 3 | 4 | 2.75 |
| Plain-English Ohio bill tracker (LLM) | 3 | 2 | 3 | 2 | 2 | 2 | 3 | 2.45 |

Why the others lost:
- **Internship list:** Simplify already covers finance and consulting roles on its site, Intern Dock posts a master list hourly, and one GitHub project already predicts when applications open.
- **Course seats:** Coursicle exists, and the data is unofficial.
- **Rent:** no clean public rent data.
- **SNAP:** the rules are complicated, a wrong answer could cost someone benefits, and the results are hard to measure.
- **Hospital prices:** months of data cleaning.
- **COTA:** riders already have real-time apps.
- **Bill tracker:** needs a paid API, and has few users.

## Why Square Deal, and what I checked first

**The timing.** Franklin County just updated every property value for 2026. Tentative residential values rose about 9% on average (Axios Columbus). They become final in December, and owners who disagree can file a free complaint with the county Board of Revision. Recent filing windows have closed on March 31, so this cycle's should close on March 31, 2027 (to be confirmed when the county posts it). In one past reappraisal, 7,681 owners filed (Columbus Dispatch).

**The research.** University of Chicago research led by Christopher Berry found that assessments across the US are usually regressive: cheaper homes are valued closer to their full price than expensive ones. Its 2022 report for Franklin County found a COD of 20.3, failing the IAAO's uniformity standard (below 15). The COD is the average gap between a home's value-to-price ratio and the typical ratio. Atuahene and Berry linked inflated assessments to about 10% of Detroit's tax foreclosures. Ohio State's own Kirwan Institute has studied Franklin County's appraisal process.

**The gap.** Homeowners have to prove their value is wrong, and the county says comparable sales are evidence to bring. The county explains the process but doesn't compare a home with similar sales. The paid options are AppealDesk's $49 packet and contingency firms that focus on commercial property. Nothing free and transparent does this for homeowners.

**Data check.** I downloaded the county's public files from November 20, 2026:
- 291,845 single-family homes with their tentative 2026 values (median change from 2025: +10.7%)
- home characteristics: size, age, quality grade, rooms, basement, garage
- every recorded sale, with the county's own validity codes: 9,631 valid single-family sales in 2025
- parcel boundaries, for finding comparable homes by distance

**Sales chasing.** If the county set sold homes' values to their sale prices, any fairness check on those sales would look better than reality. Within the same neighborhood, homes that sold in 2025 had their values changed by about the same amount as homes that didn't: the median difference was 0.3 percentage points.

**The county's values, tested two ways.** The ratio is the county's 2026 value divided by the sale price.

| Test | Sales | Median ratio | COD | PRD | PRB |
|---|---|---|---|---|---|
| 2025 sales the county validated (it used these to set values) | 9,491 | 0.90 | 6.1 | 1.00 | +0.005 |
| 2026 sales, after the valuation date (not yet validated; screened by deed type) | 9,739 | 0.88 | 12.3 | 1.02 | −0.023 |
| IAAO standard | | 0.90–1.10 | 5–15 | 0.98–1.03 | ±0.05 |

**The trap I almost fell into.** On the 2026 sales, sorting homes by sale price suggests cheap homes are valued at 102% of their price and expensive ones at 82%. That's largely an artifact. Sorting by the county's value flips the pattern (81% to 87%), and the bias-reduced IAAO method lands in between (93% to 85%): a mild tilt toward cheaper homes, inside the standard. A loud "regressive" headline would have been wrong.

**What this means.** Countywide, the 2026 values look fair. Individual homes are another story: about 1 in 6 homes that sold in 2026 sold for less than the county's value, and 1 in 12 for at least 10% less. Those owners are who the tool is for. It also has to tell everyone else, clearly, that their value looks fine. That saves them a filing.

## Decision

Build **Square Deal**: a free website where a Franklin County homeowner enters an address and sees:
- their 2026 value next to an estimate built from comparable sales, with a range;
- the comparable homes and how each was adjusted;
- a plain verdict: in line, worth a closer look, or likely too high;
- the tax difference if the value were corrected;
- how to file by the deadline.

A countywide fairness report runs alongside it. The data refreshes monthly from the county's files.

**Done means:**
1. The estimate is tested on 2026 sales it never saw, against the county's own accuracy.
2. Among homes the tool flags, the share that actually sold for less than the county's value is well above the 1-in-6 base rate.
3. Real use during filing season: visits, lookups, and owners who say they filed.

**Risks and how I handle them:**
- **The estimate is wrong for someone.** Show a range, show the comparable homes, flag only when the evidence is strong, and say it isn't an appraisal.
- **Legal advice.** It explains a free public process and links the official forms. No promises.
- **Privacy.** Addresses and values are public records, but owner names are never shown.
- **Looking official.** No county branding; "not affiliated with the Franklin County Auditor" on every page.

## What changed once I built it

Three things I learned while building that changed the numbers above.

- **The 2026 test sales were dirtier than I thought.** In 2025, only 71% of single-parcel deed sales were later judged valid by the county, and only 35% for homes under $150,000. The rest mostly sold below the county's value. The screen above (deed type only) let them through. I added a model of the county's own validity calls (company buyer or seller, quick resale, deed type; never the price). Rerun on the screened sales, the county's 2026 values look better than in the table above: a COD of 10.2, a PRD of 1.01, and a PRB of +0.006. About 15% of homes sold below their county value, not 1 in 6, and the low-end tilt disappeared.
- **The first verdict over-flagged expensive homes.** "County value above the top of the likely range" sent too many expensive homes to "too high," because their estimates are less certain than their comps suggest. It's now a calibrated chance that a home like this one sold below its county value, fitted on half of the 2026 sales and checked on the other half.
- **The result.** On sales it never saw, the estimate misses by 8.2% typically, against 8.9% for the county. Homes flagged "may be too high" sold below their county value 52% of the time, against 15% for all homes. The README has the full results.

## Sources
- Belot, Kircher, Muller, "Providing Advice to Jobseekers at Low Cost," *Review of Economic Studies* 86(4), 2019
- Berry, "Reassessing the Property Tax" (University of Chicago, 2021); Center for Municipal Finance, Franklin County, Ohio report
- Atuahene and Berry, "Taxed Out" (2019), on Detroit
- IAAO, *Standard on Ratio Studies* (2013)
- Franklin County Auditor: 2026 Property Value Update announcements, Board of Revision filing instructions, public data downloads
- Axios Columbus, May 20, 2026; ProPublica Illinois and Chicago Tribune, *The Tax Divide*
- Kirwan Institute (Ohio State), report on Franklin County's appraisal process
- NACE 2019 Student Survey and Berkeleytime, Penn Labs, Coursicle coverage, for what student tools look like
