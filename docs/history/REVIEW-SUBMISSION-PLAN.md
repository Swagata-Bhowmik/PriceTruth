# Price Truth: prioritize the 40-mark Lab Work

> **Historical document.** Superseded; kept for the record. Current status: [PROJECT-COMPLETION.md](../../PROJECT-COMPLETION.md).

## Final same-day decision — supersedes the schedule below

The user requires completion today. Freeze feature expansion and present the working historical price-assessment workflow, with unit comparison as supporting functionality. Existing tool scopes remain explicit: the code review covers the current application and its supporting files, while Mutmut covers three domain modules. Do not describe those results as isolated model-only measurements.

The final report is `submission/PRICE-TRUTH-FINAL-CODE-REVIEW.docx`; source, evidence and demonstration instructions are packaged with it. The October schedule below is historical planning, not a dependency or active plan. The data pilot, unified dashboard and Claude styling are deferred beyond this submission.

## Decision

Review the entire existing functional Python application now. Do not wait for the complete consumer-product vision, new historical data, or visual redesign. Keep the review current by regenerating it against the final submitted code. Do not reduce the submission to one function when the broader tested codebase already exists.

The rubric in PRICE-TRUTH-BUILD-HANDOFF.md assigns 10 marks each to codebase, frameworks, code quality and achieved NFRs. Running four tools addresses code quality and supports the other sections; it does not by itself establish all 40 marks or guarantee a grade.

## Current evidence

| Rubric area | Evidence available | Remaining limitation |
|---|---|---|
| Codebase | Source tree, layer/SLOC table, functional application and real data pipeline | Separate feature pages do not yet form a unified product-search journey |
| Frameworks | Actual versions and justifications in generated report | Any new frontend dependencies must be added to the final review |
| Code quality | Ruff, 98 passing PyTest cases, scoped Mutmut, all four Radon families, source hashes and raw outputs | 70 surviving mutants; elevated report-generator complexity; incomplete coverage |
| NFRs | Browser screenshots, measured latency, nine-category target/evidence table | Uptime, 100-user capacity, public HTTPS, other browsers and user study not established |

Baseline mutation result: 305/375 killed, 81.33%. Scope is calculations, catalogue and history only. Coverage is for the price_truth package; app.py has functional AppTest checks but is outside that coverage denominator. Current reports disclose these boundaries.

## Submission sequence

1. Retain the current report as a measured baseline. Verify its source hashes before citing its results for changed code.
2. Improve substantive review findings and feasible local NFR checks. Give these priority over adding another model or an unrelated dataset.
3. Complete the connected product flow only where exact identity and source evidence support it. Run the proposed 10-product data feasibility pilot before committing to broad current-price or timing claims. This pilot and the unified dashboard are pending work, not completed features.
4. Give Claude docs/CLAUDE-UI-HANDOFF.md plus the required files. Styling can follow the prototype without changing the target, replacing SHAP, or inventing data.
5. After final code/UI changes, rerun tests and browser checks, then regenerate the review. Keep report, raw outputs, screenshots and submitted source synchronized.
6. Assemble the final presentation/document from that frozen evidence: metadata, architecture/flow, source excerpts, framework table, four tool sections, model results, NFR table and explicit limitations. The generated Markdown report exists; a final Word/PDF or slide presentation has not been produced.

## Timeline from project documents

| Milestone | Recorded deadline | Working plan |
|---|---|---|
| Lab Work, 40 marks | October 2, 2026 | September 19–22: evidence and review fixes; September 23–26: supported integration/UI changes; September 27–29: final verification and document; September 30–October 1: rehearsal and buffer |
| Working Demo, 20 marks | October 16, 2026 | Continue product refinement, deployment checks and recording after the Lab Work snapshot |

These are the deadlines recorded in the supplied documents, not a newly verified institution schedule. The plan is feasible for a bounded submission; it is not a promise that all live data, longitudinal forecasts, public reliability targets or external dependencies will be resolved by October 2.

## Presentation emphasis

Show one actual quote flowing through validation, the trained model and real SHAP. Then show the data audit, grouped held-out evaluation, passing tests, actual killed/surviving mutation examples and the NFR evidence table. Explain the distinction between historical price estimation and verified discount authenticity. Use the unit comparator as a second complete, easily checked user task.

Do not present the prototype's 96% score, exact waiting period, simulated timelines or large marketing counts as measured outcomes. Do not present unmeasured NFRs as achieved. A complete report includes unresolved results; a complete product requires further evidence and engineering.
