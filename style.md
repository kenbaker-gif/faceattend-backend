# FaceAttend visual and UX style guide

**Status:** Recommended direction  
**Research date:** 2026-09-28  
**Scope:** `static/html/index.html` (landing page), `static/html/dashboard.html` (admin dashboard), and their CSS/JS surfaces.

## 1. Product direction

FaceAttend is a high-trust attendance and identity product for universities. The interface should feel:

- **Trustworthy:** attendance records, biometric workflows, audit logs, and billing must look controlled and explainable.
- **Fast:** a lecturer should understand the current state and start the next task without hunting through the UI.
- **Human:** use plain, calm language and show what the system is doing; do not make AI or face recognition feel mysterious.
- **Locally credible:** support university administrators working on variable bandwidth, smaller screens, and mixed levels of technical experience.
- **Quietly intelligent:** use AI to surface useful summaries and anomalies, not as a reason to add gradients, chat, or decorative motion.

The recommended visual theme is **Trusted Signal**: a neutral ink-and-surface foundation, one accessible teal action color, restrained amber for attention, and explicit text/icons for every status. Keep the current FaceAttend identity (cyan, orange, Syne + Instrument Sans, light/dark modes), but reduce visual noise and make the data hierarchy do the work.

## 2. What exists today

The current implementation already provides:

- A marketing landing page with a hero, stats, “How It Works,” features, pricing, and registration form.
- A dashboard with authentication, password recovery, metrics, tabs, filters, tables, modals, theme selection, and role indicators.
- Dark/light theme tokens in `styles.css` and `dashboard.css`.
- A distinctive palette (`--cyan`, `--orange`, `--blue`, `--purple`) and typography (`Syne`, `Instrument Sans`).
- Attendance, student, lecturer, AI summary, billing, audit, and institution workflows.

The main design risk is not lack of visual polish. It is **inconsistent meaning**: a marketing claim, a KPI, a recognition result, and an operational error currently risk looking like the same kind of colored decoration. Every color, card, chart, and animation should therefore answer a specific user question.

## 3. Current themes worth adopting

### 3.1 Trust-first minimalism

Use a calm layout, generous spacing, short copy, and a small number of prominent metrics. For a dashboard, show the answer to “what needs attention now?” before offering deeper exploration. Avoid a wall of equal-weight cards.

**Use on FaceAttend**

- Put today’s attendance status, sessions needing attention, and recent verification health above secondary administration.
- Keep one primary CTA per landing-page section and one primary action per dashboard panel.
- Prefer a useful empty state over a blank card or a fake zero.
- Keep decorative grid backgrounds subtle enough that tables, form controls, and focus indicators remain dominant.

### 3.2 Progressive disclosure and role-based views

Carbon’s dashboard guidance distinguishes presentation dashboards from exploration dashboards: the former gives a high-level status, while the latter supports search, filters, drill-down, and linked views. FaceAttend needs both, but not simultaneously at the same visual level.

**Use on FaceAttend**

- **Central administrator:** institution health, attendance trend, enrollment, departments/coordinators, billing and audit.
- **Department administrator:** department attendance, course units, lecturers, students, exceptions.
- **Lecturer/coordinator:** current session, scan readiness, recent results, and a short path to attendance records.
- Keep advanced filters, exports, API keys, and audit detail behind the relevant tab or “More actions,” not in the first viewport.
- Persist the selected date range and filters, and show them as removable chips so the current data scope is always visible.

### 3.3 Explainable AI and human-controlled automation

AI attendance summaries should be an interpretation layer over verifiable records. They must never replace the underlying table or imply certainty that the data does not support.

**Use on FaceAttend**

- Label AI content as **AI-generated summary** and show its source period, filters, and last-generated time.
- Include “View supporting records” and “Regenerate” actions.
- Use language such as “Attendance was lower than the previous 7-day period” rather than unsupported causal claims.
- Present confidence or data coverage when relevant; do not display a confidence score unless it has a defined meaning.
- Never use an AI-generated sentence as the only explanation for a failed, spoof, or disputed verification.

### 3.4 Performance as a design feature

Google’s Web Vitals guidance treats loading, interactivity, and visual stability as core experience qualities and recommends evaluating real users at the 75th percentile, split by mobile and desktop.

**Targets for the web surfaces**

| Measure | Target | Design implication |
|---|---:|---|
| Largest Contentful Paint | ≤ 2.5 s at p75 | Keep the landing hero lightweight; avoid blocking decorative assets. |
| Interaction to Next Paint | ≤ 200 ms at p75 | Avoid expensive table re-renders and synchronous chart work. |
| Cumulative Layout Shift | ≤ 0.1 at p75 | Reserve space for metrics, tables, images, alerts, and async AI summaries. |
| First meaningful dashboard state | ≤ 1.5 s after auth response on a normal connection | Render shell and loading states immediately; fetch panels independently. |

These are acceptance targets, not promises. Measure with PageSpeed Insights/CrUX where available and browser performance tooling for authenticated dashboard flows.

### 3.5 Accessible by default, not as a later theme

Use WCAG 2.2 AA as the baseline. USWDS and GOV.UK both emphasize the four principles—perceivable, operable, understandable, and robust—and explicitly warn that adopting a design system alone does not make a service accessible. Test the implementation, including with real users and assistive technology.

## 4. Shared visual system

### 4.1 Color roles

Keep color semantic. Do not use the same hue for unrelated concepts.

| Token role | Current direction | Use |
|---|---|---|
| `--color-bg` | Ink/dark or cool off-white/light | Page background only. |
| `--color-surface` | Elevated surface | Cards, panels, dialogs. |
| `--color-text` | High-contrast text | Body and headings. |
| `--color-muted` | Readable secondary text | Metadata, helper text, timestamps. |
| `--color-action` | FaceAttend teal/cyan | Primary CTA, selected navigation, positive interactive focus. |
| `--color-accent` | Orange/amber | Attention, trial/pricing emphasis, pending states. |
| `--color-info` | Blue | Informational status and neutral links. |
| `--color-ai` | Purple, sparingly | AI-generated content only; always pair with a label. |
| `--color-success` | Green or accessible teal variant | Confirmed attendance/success; pair with text/icon. |
| `--color-danger` | Red | Destructive action, failed state, security alert. |

Required rules:

1. Test every text/background pair in both light and dark themes. Target WCAG AA: at least **4.5:1** for normal text and **3:1** for large text; non-text controls and focus indicators need **3:1** against adjacent colors.
2. Never communicate success, failure, spoof, or pending using color alone. Use a visible label, icon, and (where useful) shape.
3. Reserve red for a real risk or destructive action. Do not use it to make a marketing CTA feel urgent.
4. Avoid transparency that causes text contrast to change unpredictably over the grid background.
5. Add a high-contrast/focus treatment that remains visible in both themes.

### 4.2 Typography

Retain `Syne` for short display headings and the brand wordmark. Use `Instrument Sans` for all body, form, table, and status content.

- Body: 16px minimum; line-height 1.5.
- Dashboard table/meta text: do not go below 14px.
- Landing hero: fluid size with a sensible mobile cap; never force horizontal scrolling.
- Use sentence case for labels, tabs, buttons, and alerts. Avoid all-caps labels for important information.
- Keep headings concise and descriptive. A user scanning only headings should understand the page.
- Use tabular numerals for metrics and table columns where supported.
- Use a readable measure: approximately 60–75 characters per line for long landing-page copy.

### 4.3 Spacing, shape, and elevation

Use a 4px base unit and a small scale (4, 8, 12, 16, 24, 32, 48, 64). Use 8–16px radii for controls/cards and larger radii only for major landing-page containers. Avoid every component having a different radius.

Elevation should communicate interaction and grouping, not decoration:

- Dashboard: mostly borders and surface contrast; minimal shadows.
- Landing page: one or two hero/pricing elevations; avoid card-on-card stacking.
- Dialog: clear backdrop, strong surface contrast, and a visible heading.

### 4.4 Motion

Motion should explain state changes: loading, opening a dialog, filter updates, or confirmation. Avoid perpetual animated backgrounds, parallax, auto-rotating carousels, and motion behind data.

- Keep transitions around 150–250ms.
- Respect `prefers-reduced-motion: reduce`; remove transforms and nonessential animation.
- Never flash content.
- Do not make a primary action appear only on hover.

## 5. Landing page guidance

### 5.1 Above-the-fold hierarchy

The current hero is strong but makes several claims at once. Make the first viewport answer three questions:

1. **What is FaceAttend?** “Attendance verification and reporting for universities.”
2. **What outcome does it provide?** “Start a session quickly, verify attendance, and see the evidence in one place.”
3. **What can I do next?** One primary action (`Start free trial`) and one secondary action (`See how it works`).

Recommended hero structure:

- Eyebrow: category or audience, not a string of unsupported superlatives.
- Outcome-led H1, one sentence or two short lines.
- Supporting copy with the operational workflow: enroll → scan → review.
- Primary CTA and secondary explainer link.
- A real, static dashboard/mobile workflow preview below or beside the copy. If it is a mockup, label it as a preview.
- A compact trust row: security/privacy approach, supported workflow, and contact/support—not invented customer logos.

Avoid claiming “98%+ accuracy,” “0.03 seconds,” “any angle,” or “challenging lighting” unless the product has reproducible test methodology and the claim is current. Link to methodology or change the copy to an observable product benefit.

### 5.2 Page sequence

Recommended sequence:

1. Hero: value, audience, CTA.
2. Proof of workflow: three steps with one concrete screenshot/illustration.
3. Outcomes: fewer manual errors, faster session start, searchable records, exportable reports.
4. Product surfaces: dashboard, mobile enrollment/scan, reporting, controls.
5. Trust and privacy: data boundaries, roles, auditability, retention/contact details.
6. Pricing: clear limits, included features, currency/renewal terms, support expectations.
7. FAQ: device requirements, enrollment process, false matches/disputes, data handling, trial conversion.
8. Registration: short form, clear role description, privacy notice, and recovery path.

Do not use “features” as the only proof. Show what the administrator or lecturer can accomplish and what happens when something goes wrong.

### 5.3 Landing-page content rules

- Use one CTA label consistently; do not alternate between “Get Started,” “Start Free Trial,” and “Register” when they lead to the same action.
- Put the 30-day trial terms, credit-card requirement, and conversion/renewal behavior next to the CTA and pricing—not only below the form.
- Explain biometric handling in plain language and link to the privacy policy before registration.
- Use testimonials or institutional logos only with permission and a verifiable source.
- Replace emoji-only feature icons with accessible labels and consistent iconography; emoji may remain decorative with `aria-hidden="true"`.
- Use real screenshots with redacted data. Do not expose student names, face images, emails, API keys, or realistic personal records in marketing assets.
- Make the nav usable on mobile with a labelled menu button, Escape-to-close, focus trap while open, and focus return to the trigger.

## 6. Dashboard guidance

### 6.1 Dashboard home

The first view should be a decision surface, not a database dump:

1. Page title, institution/department scope, and “last updated” time.
2. A short date-range control and a visible refresh action.
3. Four or fewer KPI cards: attendance rate, verified records, exceptions/spoof attempts, and active sessions.
4. A primary “Start/continue session” or “Review exceptions” action based on role.
5. One trend visualization with an accessible text summary.
6. Recent attendance/activity table with clear status and drill-down.
7. Secondary administration below or in tabs.

Each KPI card needs:

- A descriptive label (“Verified attendance today,” not “Total”).
- A value and unit.
- A comparison period only when the comparison is meaningful.
- A timestamp or data scope.
- A text equivalent when represented visually.

Do not show a percentage without its denominator or period. “92%” should be “92% of 1,248 scheduled check-ins, today.”

### 6.2 Attendance records

- Keep filters close to the table and show active filters as chips.
- Provide a clear “No records match these filters” state with “Clear filters.”
- Use a responsive table pattern: preserve column headers, allow horizontal scrolling only when necessary, and provide a card/stacked representation for narrow screens.
- Status values should be explicit: **Verified**, **Failed**, **Spoof suspected**, **Pending review**, **Manually corrected**.
- Include date/time, student identifier, course/session, method, and status; use local timezone and expose it.
- When an action changes records, show a toast plus an inline state where the change occurred. Do not rely on a toast alone.
- Export must state the active scope and file contents before download where feasible.

### 6.3 Charts and analytics

Use charts only when they reveal a trend, comparison, distribution, or anomaly faster than a table.

- Use a fixed color assignment for the same series across all views.
- Include a visible title, units, date range, legend, and a text summary.
- Provide an accessible data table or “View data” alternative.
- Do not encode more than one meaning in color, and avoid red/green-only comparisons.
- Mark missing data explicitly; do not draw a continuous line through unavailable periods.
- Keep chart interactions predictable: filter/sort/drill down, then update related views and announce the update.
- Add annotations only for useful events (semester start, system outage, threshold), not for every point.

### 6.4 Forms, dialogs, and destructive actions

- Use visible labels, not placeholder text as the label.
- Keep validation next to the field, announce the error summary, and move focus to the first invalid field when appropriate.
- State required fields and input format before submission.
- Use native controls where possible; custom controls require keyboard, focus, name, role, and value behavior.
- Dialogs need a labelled heading, Escape behavior, focus management, and focus return.
- Destructive confirmation must name the object and consequence: “Delete student Maya A. and remove their photos and attendance records?”
- Prefer reversible actions or an undo period for non-security-sensitive changes.
- Never use “Remove” and “Delete” interchangeably when the consequences differ.

### 6.5 Loading, empty, error, and stale states

Every asynchronous panel needs all four states:

- **Loading:** skeleton or spinner with a useful label; reserve final layout space.
- **Empty:** explain why it is empty and provide the next action.
- **Error:** say what failed, preserve the user’s filters/input, and offer retry; do not silently show zero.
- **Stale:** show when data was last updated and whether refresh is available.

Use an `aria-live="polite"` region for nonurgent updates such as filter completion, export readiness, and successful saves. Use assertive announcements only for urgent errors that require immediate attention.

## 7. Accessibility acceptance checklist

Before a page is considered ready:

- [ ] Keyboard-only navigation reaches every control in a logical order.
- [ ] Focus is visible in both themes and never hidden behind sticky navigation.
- [ ] Skip link and semantic landmarks (`header`, `nav`, `main`, `footer`) are present.
- [ ] Every page has one meaningful `h1`; headings do not skip levels for styling.
- [ ] Icon-only controls have an accessible name; decorative icons are hidden from assistive technology.
- [ ] Forms have programmatic labels, required state, format guidance, and recoverable errors.
- [ ] Tables, charts, dialogs, tabs, menus, and toasts have tested semantics.
- [ ] No information depends on color, hover, sound, or motion alone.
- [ ] Zoom to 200% and text spacing changes do not hide content or create unusable overlap.
- [ ] Touch targets are comfortably selectable; target at least 44×44 CSS px for web controls.
- [ ] Reduced-motion mode is respected.
- [ ] Test with a keyboard, screen reader, browser zoom, high-contrast/forced-colors mode, mobile viewport, and a slower network.
- [ ] Run automated checks (axe/pa11y or equivalent) and manually review the results. Automated checks are not a substitute for user testing.

## 8. Research and measurement plan

Do not treat a visual trend as validated simply because it is common in 2026. Validate the product’s critical tasks:

1. Interview one central administrator, one department administrator, and two lecturers.
2. Observe: create a course/session, enroll a student, record attendance, investigate a failed/spoof result, export a report, and invite a user.
3. Test a low-fidelity landing-page variant with prospective institutions. Ask participants to explain the product, identify the next step, and describe data/privacy implications.
4. Measure task success, time on task, errors, confidence, and the point where users need help.
5. Instrument meaningful events: landing CTA click, form completion, first successful login, session start, filter use, export, retry after error, and AI-summary expansion.
6. Compare a focused dashboard against a card-dense version using the same tasks. Prefer the version with higher task success and lower error rate, not merely longer engagement.
7. Review analytics and accessibility feedback monthly; revisit tokens and content when evidence changes.

## 9. Implementation order

1. Consolidate shared tokens and focus/contrast rules across `styles.css` and `dashboard.css`.
2. Fix semantic labels, keyboard behavior, modal focus management, error announcements, and reduced-motion behavior.
3. Refactor dashboard home around role, scope, date, freshness, and exceptions.
4. Improve table/chart empty, error, stale, and accessible-data states.
5. Simplify landing-page claims and add a credible workflow preview plus privacy/trust section.
6. Optimize font loading, image dimensions, async panel rendering, and Web Vitals measurement.
7. Validate with task-based testing and real data before adding more visual effects.

## 10. Research sources

These sources were consulted on 2026-09-28. Institutional guidance is prioritized over trend articles.

- W3C, **Web Content Accessibility Guidelines (WCAG) 2.2**: <https://www.w3.org/TR/WCAG22/>
- W3C, **Understanding the four principles of accessibility**: <https://www.w3.org/WAI/WCAG22/Understanding/intro>
- IBM Carbon Design System, **Dashboards**: <https://carbondesignsystem.com/data-visualization/dashboards/>
- U.S. Web Design System, **Accessibility**: <https://designsystem.digital.gov/documentation/accessibility/>
- GOV.UK Design System, **Accessibility strategy**: <https://design-system.service.gov.uk/accessibility/accessibility-strategy/>
- Google Material Design 3, **Foundations and accessibility guidance**: <https://m3.material.io/foundations/overview/principles>
- Google web.dev, **Web Vitals**: <https://web.dev/articles/vitals>
- Nielsen Norman Group, **F-shaped pattern for reading web content**: <https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/>

The sources agree on the durable principles: establish hierarchy, reduce unnecessary complexity, make interactions predictable, provide alternatives to visual data, use semantic structure, test with assistive technology, and measure real user experience. The “Trusted Signal” theme above applies those principles to FaceAttend without depending on short-lived aesthetic trends.

## 11. Agent execution brief

This section is written as an implementation handoff for a coding agent. The agent should make the changes in small, reviewable phases and preserve existing authentication, API calls, role permissions, billing behavior, and attendance data behavior.

### Agent task

> Implement the FaceAttend “Trusted Signal” visual and UX direction across the landing page and admin dashboard. Improve hierarchy, accessibility, responsive behavior, loading/error/empty states, and content clarity without changing backend contracts or inventing product data.

### Execution rules

1. Inspect `static/html/index.html`, `static/html/dashboard.html`, `static/css/styles.css`, `static/css/dashboard.css`, `static/js/main.js`, `static/js/dashboard.js`, and `static/js/theme.js` before editing.
2. Preserve existing IDs, function names, API routes, authentication flows, role checks, and data fields unless a compatibility-safe migration is necessary.
3. Reuse existing CSS variables and theme behavior; consolidate duplicated tokens instead of introducing a second unrelated palette.
4. Use semantic HTML and native controls before adding ARIA. Add ARIA only where the native element does not provide the required behavior.
5. Do not add fabricated testimonials, customer logos, accuracy claims, attendance records, or performance numbers.
6. Do not expose real student or institution data in any preview or marketing example.
7. Keep changes limited to the landing page/dashboard surfaces and directly related assets. Do not modify backend security, billing, or database behavior as part of the visual refresh.

### Phase A — foundation

- Add shared focus-visible styles, reduced-motion rules, minimum readable type sizes, and contrast-safe light/dark tokens.
- Add a skip link and semantic landmarks to the landing page and dashboard.
- Normalize button, input, select, table, tab, modal, toast, and status styles.
- Ensure every icon-only action has an accessible name and decorative icons are hidden from assistive technology.
- Reserve layout space for asynchronous metrics, charts, and tables to reduce layout shift.

### Phase B — landing page

- Rewrite the hero around one outcome-led message and one primary CTA.
- Keep the secondary “See how it works” action, but make it a normal link with a visible focus state.
- Add a compact workflow preview for enroll → scan → review using redacted/static content.
- Reframe feature cards as user outcomes; keep technical details in supporting text.
- Add a privacy/trust section explaining roles, auditability, and biometric-data handling in plain language.
- Make pricing terms, trial conditions, renewal expectations, and support scope explicit.
- Improve registration labels, error summary, field-level errors, privacy acknowledgement, and mobile layout.
- Make the navigation menu keyboard accessible, including Escape-to-close and focus return.

### Phase C — dashboard

- Add page title, current institution/department scope, date range, and last-updated information.
- Restructure the first viewport around no more than four decision-useful KPI cards.
- Add a prominent role-appropriate action such as “Start session” or “Review exceptions.”
- Make attendance statuses explicit text values: Verified, Failed, Spoof suspected, Pending review, and Manually corrected.
- Add loading, empty, error, stale, retry, and clear-filter states to every asynchronous panel.
- Show active filters as removable chips and preserve filters when a request fails.
- Add accessible summaries and data alternatives for charts.
- Improve table responsiveness without hiding column meaning on small screens.
- Add modal focus management, labelled dialogs, Escape handling, and descriptive destructive confirmations.
- Make success, error, export-ready, and filter-update announcements available through a polite live region.
- Label AI content as AI-generated, show its scope and timestamp, and link it to supporting records.

### Phase D — validation

The agent should run the smallest applicable checks after each phase, then perform a final review:

- Validate HTML structure and check for duplicate IDs.
- Run the project’s existing test or verification scripts.
- Run an automated accessibility scan if the project has one available.
- Test keyboard-only navigation, focus visibility, Escape behavior, browser zoom at 200%, reduced motion, light theme, dark theme, and a narrow mobile viewport.
- Verify login, password recovery, tabs, filters, export, invite/remove dialogs, delete confirmations, theme switching, and logout still work.
- Check that no API request, selector, or event handler was unintentionally renamed.
- Record any remaining accessibility or content limitation rather than hiding it.

### Agent completion report

The agent should report:

- Files changed and the purpose of each change.
- User-visible behavior changes.
- Checks run and their results.
- Any claims or content intentionally left unchanged because they lack evidence.
- Any follow-up work that requires product, legal/privacy, or user-research decisions.

## 12. Visual preview

This is a structural preview, not a screenshot. It shows the intended information hierarchy and representative copy. The agent should implement the structure using the existing FaceAttend brand tokens and responsive CSS.

### 12.1 Landing page — desktop

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ FaceAttend             How it works  Product  Pricing  Privacy   [Sign in]   │
│                                                          [Start free trial]  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ATTENDANCE VERIFICATION FOR UNIVERSITIES                                   │
│                                                                              │
│  Verify attendance.                                                         │
│  Understand every session.                                                  │
│                                                                              │
│  FaceAttend helps universities enroll students, verify attendance, and      │
│  review reliable records from one connected workflow.                       │
│                                                                              │
│  [Start free trial]    [See how it works]                                   │
│  30 days · No credit card required                                          │
│                                                                              │
│                         ┌───────────────────────────────────────────────┐   │
│                         │ TODAY · SESSION 08:00                         │   │
│                         │ Intro to Computing              84 / 92 verified│   │
│                         │                                                   │   │
│                         │ ✓ Verified     84                               │   │
│                         │ ! Pending       6                               │   │
│                         │ × Failed        2                               │   │
│                         │                                                   │   │
│                         │ [Open dashboard]                                  │   │
│                         └───────────────────────────────────────────────┘   │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  ENROLL                         VERIFY                         REVIEW       │
│  Capture approved photos        Record attendance               Explore      │
│  with the mobile workflow.      during a live session.           evidence.    │
├──────────────────────────────────────────────────────────────────────────────┤
│  Built for the work your institution does                                  │
│  [Real-time records] [Role-based access] [Audit-ready history]              │
│  [Exportable reports] [Course units] [Privacy controls]                     │
├──────────────────────────────────────────────────────────────────────────────┤
│  Clear records. Clear responsibility.                                       │
│  Understand how data is used, who can access it, and how actions are logged. │
│  [Read privacy and security details]                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│  Simple plans · 30-day trial · Clear limits                                 │
│  [Starter]              [Growth — recommended]            [Enterprise]       │
│  [Contact / start]      [Contact / start]                  [Talk to us]       │
├──────────────────────────────────────────────────────────────────────────────┤
│  Ready to replace manual registers?                                         │
│  [Start your free trial]                                                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 12.2 Landing page — mobile

```text
┌──────────────────────────────┐
│ FaceAttend             [☰]  │
├──────────────────────────────┤
│ ATTENDANCE VERIFICATION      │
│ FOR UNIVERSITIES             │
│                              │
│ Verify attendance.           │
│ Understand every session.   │
│                              │
│ [Start free trial]           │
│ [See how it works]           │
│ 30 days · No card required   │
│                              │
│ ┌──────────────────────────┐ │
│ │ TODAY · 08:00             │ │
│ │ 84 / 92 verified          │ │
│ │ ✓ 84  ! 6  × 2            │ │
│ └──────────────────────────┘ │
│                              │
│ ENROLL → VERIFY → REVIEW     │
│                              │
│ [Read privacy and security]  │
│                              │
│ [Start your free trial]      │
└──────────────────────────────┘
```

### 12.3 Dashboard — desktop

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ FaceAttend / DASHBOARD     Institution: North Campus   Admin   Theme  Sign out│
├──────────────────────────────────────────────────────────────────────────────┤
│ Attendance overview                                      [Start session]     │
│ North Campus · Today, 28 Sep 2026 · Updated 10:42       [Refresh]           │
│                                                                              │
│ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ │
│ │ Verified today │ │ Attendance     │ │ Active sessions│ │ Needs review   │ │
│ │ 1,248          │ │ 92%            │ │ 3              │ │ 8              │ │
│ │ of 1,356 checks│ │ 1,248 / 1,356  │ │ 2 in progress │ │ 5 failed       │ │
│ └────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘ │
│                                                                              │
│ [Attendance records] [Students] [AI summary] [Lecturers] [More]             │
│                                                                              │
│ Attendance trend · Last 7 days                    [Date range ▾]            │
│ ┌────────────────────────────────────────────────────────────────────────┐ │
│ │  Text summary: attendance ranged from 88% to 94%; lowest was Tuesday.  │ │
│ │  Accessible data table: [View data]                                     │ │
│ │                  ╱╲        ╱╲                                          │ │
│ │             ╱╲  ╱  ╲  ╱╲  ╱  ╲                                         │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ Recent attendance                                      [Export CSV]          │
│ [Today ×] [North Campus ×] [Clear filters]                                  │
│ ┌──────────────┬──────────────┬───────────────┬──────────────┬────────────┐ │
│ │ Time         │ Student      │ Course/session│ Method       │ Status     │ │
│ ├──────────────┼──────────────┼───────────────┼──────────────┼────────────┤ │
│ │ 10:42 EAT    │ ST-00482     │ CSC 101       │ Face scan    │ ✓ Verified │ │
│ │ 10:41 EAT    │ ST-00117     │ CSC 101       │ Face scan    │ ! Review   │ │
│ └──────────────┴──────────────┴───────────────┴──────────────┴────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 12.4 Dashboard — mobile

```text
┌──────────────────────────────┐
│ FaceAttend          [☰] [⋯] │
├──────────────────────────────┤
│ Attendance overview          │
│ North Campus · Today         │
│ Updated 10:42                │
│                              │
│ [Start session]              │
│                              │
│ ┌──────────────────────────┐ │
│ │ Verified today            │ │
│ │ 1,248 of 1,356            │ │
│ └──────────────────────────┘ │
│ ┌──────────────────────────┐ │
│ │ Attendance                │ │
│ │ 92%                       │ │
│ └──────────────────────────┘ │
│                              │
│ [Review exceptions · 8]      │
│                              │
│ [Attendance] [Students]      │
│ [AI summary] [More]          │
│                              │
│ Recent attendance            │
│ [Today ×] [Clear filters]    │
│                              │
│ ST-00482 · CSC 101           │
│ 10:42 EAT · Face scan        │
│ ✓ Verified                   │
│                              │
│ ST-00117 · CSC 101           │
│ 10:41 EAT · Face scan        │
│ ! Pending review             │
└──────────────────────────────┘
```

### 12.5 State preview

```text
Loading:  [spinner] Loading attendance records…

Empty:    No attendance records match these filters.
          [Clear filters]

Error:    We couldn’t load attendance records.
          Your filters were kept. [Try again]

Stale:    Showing data from 10:42 EAT. [Refresh]

AI:       AI-generated summary · Today · Based on 1,356 records
          Attendance was 92%, up 3 percentage points from yesterday.
          [View supporting records] [Regenerate]
```
