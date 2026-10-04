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

## 13. Whole-product review — 1 October 2026

### 13.1 Product surfaces reviewed

This review covers the connected product, not only the marketing site:

- Web landing page and registration flow in the backend repository.
- Web admin dashboard, including Students, Attendance, Sessions, Team, Billing,
    Audit Logs, and AI Summary.
- Flutter mobile app in `/home/abubaker/Smart_attendance_app`, including login,
    signup, session gating, biometric unlock, auto-lock, camera verification, and
    the mobile admin screen.
- The hosted Supabase authentication/data layer and the separate verification
    API used by the mobile client.

### 13.2 Overall assessment

The visual direction is credible for a Ugandan university pilot: the teal action
color, light/dark themes, restrained surfaces, and operational vocabulary make
FaceAttend feel more like a working institution product than a consumer app.
The landing page is approximately **8/10 visually** and the desktop dashboard
approximately **8/10**. The authenticated dashboard at a 390px viewport is
approximately **6/10** because nine sections compete for limited horizontal
space and the student table becomes dense.

The main risk is not visual quality. It is product coherence and trust across
surfaces: the landing page, dashboard, and Flutter app should describe the same
roles, institution context, data boundaries, and failure states.

### 13.3 Flutter mobile direction

The Flutter client has a strong operational foundation:

- Supabase email/password authentication and session persistence.
- Biometric unlock after an initial password login.
- A two-minute inactivity/background auto-lock.
- Camera capture, image compression, upload, and verification feedback.
- Session-aware verification with lecturer, course unit, and attendance context.

Prioritize the following mobile improvements:

1. Make the first screen task-led: **Start session**, **Scan student**, and
     **Review recent results** should be more prominent than account metadata.
2. Show institution, campus, course unit, lecturer, and active session context in
     one persistent header so a scan cannot silently go to the wrong session.
3. Design for intermittent connectivity: show queued uploads, retry state, last
     successful sync, and whether a result is local, pending, or server-confirmed.
4. Make camera guidance explicit: lighting, face position, movement, and what to
     do when verification fails. Never leave the user with only a spinner.
5. Keep biometric and logout states distinct. Explain that auto-lock preserves a
     session while hard logout destroys it.
6. Use the same semantic status language and colors as the dashboard: Verified,
     Review, Failed, Spoof detected, Pending, and Offline.
7. Test the primary scan flow on low-memory Android devices and smaller screens;
     camera startup time and recovery after app backgrounding are core UX metrics.

### 13.4 Dashboard priorities

The current desktop shell is strong, but the dashboard should evolve toward a
role-specific operational workspace:

- Central administrators need institution health, attendance trend, enrollment,
    billing, audit, and exceptions.
- Department administrators need department attendance, units, lecturers,
    students, and exceptions.
- Lecturers/coordinators need the active session, scan readiness, recent results,
    and a short route to review.

For mobile web, replace the nine-tab strip with two or three primary destinations
and a labelled **More** menu. Keep the current section available, but do not make
every administrative area compete in the first viewport.

The Students table should gain search, institution/course filters, pagination or
virtualized rows, clear loading/error/empty states, and a visible export action.
Destructive Delete actions should be visually separated from routine row actions
and should identify the scope of the deletion before confirmation.

### 13.5 Landing page priorities

The landing page has a strong workflow narrative: enrollment, scan, and review.
Make it more locally credible before treating it as production-ready:

- Remove visible `TODO` text from pricing, FAQ, and currency switching.
- Make UGX the default or provide confirmed UGX values and renewal terms.
- Explain mobile money/card support only when the payment workflow is available.
- Add concise Uganda-specific support, data protection, and connectivity language.
- Make biometric consent and dispute/review handling visible before registration.
- Use the real mobile scan workflow in product imagery instead of generic mockups
    where possible, with all names and records redacted.
- Keep one theme control in the header; avoid duplicate footer controls.
- Keep Privacy Policy and Terms in one dedicated legal row in the footer.
- Treat the WebSiteLaunches badge as a credibility link, not a product feature;
    keep its external destination and alt text explicit.

### 13.6 Shared content and trust rules

The web and mobile products must use the same vocabulary and boundaries:

| Concept | Preferred language |
|---|---|
| Successful scan | **Verified** |
| Uncertain result | **Review required** |
| Failed match | **Not verified** |
| Liveness failure | **Spoof check failed** |
| Network interruption | **Waiting to sync** |
| AI output | **AI-generated summary** |

Never imply that a face result is infallible. Always provide a human review path,
the supporting attendance record, timestamp, session, and institution scope.
Never show production student names, emails, face images, API keys, or realistic
records in marketing screenshots or tests.

### 13.7 Prioritized improvement plan

**P0 — before public institutional rollout**

- Remove pricing/FAQ placeholders and confirm UGX, renewal, and payment wording.
- Add clear mobile/web loading, offline, retry, stale-data, and empty states.
- Verify every protected action uses the intended local or hosted API endpoint;
    do not let local testing silently mutate production data.
- Test role boundaries, institution isolation, biometric consent, and deletion
    confirmation end to end.

**P1 — next product iteration**

- Introduce role-specific dashboard starting views.
- Test the role-aware mobile section selector with each authenticated role.
- Add student search/filter/export and attendance exception workflows.
- Align mobile and web status components, wording, colors, and timestamps.

**P2 — polish and adoption**

- Add institution branding and campus context.
- Add a real redacted mobile scan preview to the landing page.
- Measure scan startup, upload retry, dashboard first meaningful state, and
    common task completion on representative Android devices and networks.

## 14. Implementation audit — 1 October 2026

This section records what is present in the current source and what still needs
work. It is an audit of implementation, not a replacement for the target
standards above. **Implemented** means visible in source or verified locally;
**partial** means the basic capability exists but does not meet the full
standard; **not implemented** means no supporting behavior was found; **not
verified** means runtime, device, or user testing is still required.

### 14.1 Web foundation and visual system

| Area | Status | Evidence and gap |
|---|---|---|
| Shared light/dark/system theme | **Implemented** | `static/css/theme.css` and `static/js/theme.js` provide shared tokens, preference persistence, and theme controls. |
| Responsive landing layout | **Implemented** | `static/html/index.html` and `static/css/styles.css` provide desktop/mobile layouts; local browser checks show no page-level horizontal overflow. |
| Responsive dashboard shell | **Implemented with follow-up** | Desktop keeps the sidebar while mobile uses a labelled section selector populated from the role-aware navigation configuration. Authenticated role-specific option population still needs end-to-end testing. |
| Semantic landmarks and skip links | **Implemented** | Landing, dashboard, privacy, and terms pages expose header/nav/main/footer landmarks and skip links. Full keyboard traversal remains **not verified**. |
| Focus and control accessibility | **Partial** | Focus-visible styling, named icon controls, labelled fields, tabs, and live regions exist. WCAG 2.2 AA, forced-colors, 200% zoom, and screen-reader behavior are not yet fully tested. |
| Reduced-motion behavior | **Not verified** | The guide requires `prefers-reduced-motion` handling; a dedicated end-to-end check and explicit rule coverage are still needed. |
| Visual consistency across Flutter and web | **Partial** | The web has a documented Trusted Signal system. The Flutter app has its own screen styling; shared tokens and status components have not been formalized. |

### 14.2 Landing page

| Area | Status | Evidence and gap |
|---|---|---|
| Hero, workflow story, features, pricing, FAQ, registration | **Implemented** | Present in `static/html/index.html`. The enroll → verify → review story is clear. |
| Theme control | **Implemented** | One header theme controller remains; duplicate footer theme control was removed. |
| Privacy and Terms access | **Implemented** | The trust/FAQ content and dedicated footer legal row link to `/privacy` and `/terms`. |
| Public launch badge | **Implemented** | `launch-badge` links to WebSiteLaunches and updates its image theme through `theme.js`. |
| Local contact identity | **Partial** | Current local landing/legal contact uses `abubaker@faceattend.app`; other dashboard/billing strings still contain `admin@faceattend.app` and need an ownership decision before global replacement. |
| Pricing localization | **Implemented for current scope** | The landing page now presents one clear USD price set with no unconfirmed UGX/RWF selector. Confirm renewal terms, payment availability, and any future local-currency offering before publishing. |
| Production-ready FAQ/legal copy | **Implemented with follow-up** | The landing FAQ now uses the privacy policy for consent, retention, and deletion guidance. Legal/product owners should still approve the wording before publishing. |
| Real product evidence | **Partial** | The page uses illustrative mockups. Add a redacted mobile scan/dashboard preview after confirming that no personal or production data is exposed. |
| Registration accessibility and recovery | **Not verified** | Labels and status region exist; field-level errors, focus movement, keyboard flow, and slow-network recovery need runtime testing. |

### 14.3 Web dashboard

| Area | Status | Evidence and gap |
|---|---|---|
| Authentication and recovery | **Implemented** | Supabase login, password recovery, session checks, logout, and role-based shell rendering are present. |
| Role-specific navigation | **Implemented** | `ROLE_CONFIG` in `static/js/dashboard.js` defines super admin, central admin, department admin, coordinator, and lecturer navigation. Permission/API parity still needs full matrix testing. |
| Institution/department scope | **Partial** | Scope is displayed and backend role helpers enforce boundaries. The first viewport should show richer institution, department, campus, date, and freshness context. |
| Attendance/students/lecturers/course/session/team/billing/audit workflows | **Implemented** | Routes, tabs, loaders, tables, dialogs, and mutations are present. End-to-end behavior against each role is not fully verified. |
| Loading, empty, and error states | **Partial** | Many loaders and empty/error messages exist. Stale-data indicators, consistent retry actions, filter preservation, and panel-by-panel coverage are incomplete. |
| Search, filters, chips, pagination, and export | **Partial** | Filters and exports exist in selected views. Student search, removable filter chips, pagination/virtualization, and a consistently visible export workflow remain gaps. |
| Destructive-action confirmation | **Partial** | Delete/remove dialogs name the object in several paths. Consequence wording, focus return, and consistency across every destructive action need verification. |
| AI explainability | **Partial** | AI summary controls and supporting dashboard context exist. Confirm that every generated result shows scope, period, timestamp, source coverage, and a supporting-record route. |
| Accessibility semantics | **Partial** | Tabs, tables, labels, dialogs, and `aria-live` regions are present. Automated axe/pa11y and manual keyboard/screen-reader testing are still required. |
| Mobile web navigation | **Implemented with follow-up** | Mobile hides the crowded tab strip and shows a labelled selector; verify the available options for every authenticated role. |

### 14.4 Flutter mobile app

| Area | Status | Evidence and gap |
|---|---|---|
| Flutter project available locally | **Implemented** | `/home/abubaker/Smart_attendance_app` contains the Flutter project, Android/iOS/web/desktop targets, and local configuration files. |
| Supabase authentication/session gate | **Implemented** | `main.dart`, `login_screen.dart`, `session_gate_screen.dart`, and `config.dart` provide authentication and session routing. |
| Biometric unlock and auto-lock | **Implemented** | The README and `security_wrapper.dart` document biometric unlock and a two-minute inactivity/background lock. Device-level verification is still required. |
| Camera verification flow | **Implemented** | `verification_screen.dart` initializes cameras, compresses images, uploads verification requests, and tracks session scan counts. |
| Session/course/lecturer context | **Partial** | Verification accepts session, lecturer, and course-unit identifiers. Confirm that this context is persistently visible and cannot be accidentally changed during scanning. |
| Verification feedback | **Partial** | Scanning, waking, result, and session flags exist. Confirm clear guidance for lighting, positioning, failure, spoof, timeout, and retry states on real devices. |
| Offline queue and sync recovery | **Not implemented** | No verified queue, retry ledger, last-sync state, or local/pending/server-confirmed status was found in the reviewed files. |
| Shared web/mobile status language | **Not implemented** | The target vocabulary is documented in Section 13.6, but a shared implementation or localization source has not been established. |
| Mobile admin experience | **Partial** | `admin_screen.dart` exists with role and student-management behavior. Its information hierarchy and mobile usability need a device-based review against the web dashboard. |
| Low-memory and network testing | **Not verified** | Test camera startup, background/foreground recovery, upload latency, and failure recovery on representative Android devices and Ugandan network conditions. |

### 14.5 Environment and deployment boundaries

| Area | Status | Evidence and gap |
|---|---|---|
| Local backend run | **Implemented** | The backend runs with `/home/abubaker/venvs/env_3.14` and a user systemd service on port `8080`. |
| Automatic local backend reload | **Implemented** | The service uses Uvicorn `--reload`; browser refresh is still required for visible frontend changes. |
| Local backend without `.env` | **Implemented with limitation** | Public pages and health checks start without server Supabase variables; protected server-side operations require credentials. |
| Local dashboard API isolation | **Implemented** | `faceattendApiBase()` in `static/js/dashboard.js` and `static/js/main.js` use the current localhost/127.0.0.1 origin. Supabase authentication and any explicitly hosted services remain separate. |
| Mobile API environment separation | **Partial** | The Flutter app loads `.env` and centralizes config, but verify that debug builds point to a safe development/test backend rather than production. |
| Production secret handling | **Partial** | Server secrets are environment-based on the backend; frontend public Supabase values are embedded by design. Audit every build and mobile artifact to ensure service-role keys never ship. |

### 14.6 Completion state

The product has a credible visual foundation and a working pilot path across web
and mobile. It is **not yet standard-complete for broad institutional rollout**.
The highest-confidence gaps are:

1. Confirm Uganda-specific commercial and privacy wording, including renewal and
    payment availability; add local-currency pricing only when approved.
2. Verify local and production API behavior with a destructive-action test matrix.
3. Add mobile offline/queued-sync behavior and verify camera failure guidance.
4. Test the role-aware mobile dashboard selector with every authenticated role.
5. Run WCAG, device, slow-network, role-boundary, and end-to-end tests and record
    the results here.

Until those checks are complete, describe the system as **pilot-ready with
documented rollout gaps**, not fully production-ready.
