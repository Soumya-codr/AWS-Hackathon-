# Autonomous SecOps Precision Terminal — Design System
**Project**: CloudSentinel Enterprise Platform (ID: 6025857470371367910)
**Design System Asset ID**: `assets/8a26c44450cd49a998448e550d5885ea`

---

## Brand & Style

The design system targets enterprise security architects, Site Reliability Engineers (SREs), and DevSecOps operators who supervise autonomous remediation agents across distributed cloud infrastructures. The operational context is zero-tolerance, mission-critical infrastructure where ambiguous interfaces directly increase mean-time-to-remediation (MTTR) and introduce human error.

The brand persona is unapologetically analytical, clinical, authoritative, and deeply functional. It rejects consumer-facing SaaS fluff, superficial decorative gradients, and atmospheric lighting blurs in favor of a surgical, dark-mode terminal environment inspired by high-frequency trading terminals, modern hyper-engineered developer ecosystems, and kernel-level trace diagnostics.

Key design tenants:
- **Zero Ambiguity:** Every pixel must convey deterministic state. Border-driven layouts replace soft elevation to guarantee crisp segmentations across dense multi-monitor arrays.
- **Extreme Density & Information Velocity:** Compact vertical line heights, rigid tabular structures, and monospaced anchors allow simultaneous inspection of thousands of audit trails, policy diffs, and security tree graphs.
- **Deterministic Color Signatures:** Color is never ornamental; it serves as real-time diagnostic status alerts (enforcement, sandboxing, violation, containment).

---

## Colors & Tokens

The palette is engineered specifically for deep-dark, low-fatigue operations with mathematically strict contrast ratios against an obsidian ground.

### Base Canvas & Structural Neutrals
- **Canvas Base (`#09090b`):** The primary root canvas representing infinite depth.
- **Surface Elevation 1 (`#0c0a09` / `#121215`):** Container background for panels, code workbenches, and tree sidebars.
- **Surface Elevation 2 (`#18181b`):** Hover states, active table rows, and secondary input controls.
- **Surface Elevation 3 (`#27272a`):** Active selections, pill backgrounds, and subtle dividers.
- **Structural Border Crisp (`#27272a`):** Razor-thin 1px division line. Use `#3f3f46` sparingly for active focus rings or selected panes.
- **Text Primary (`#fafafa`):** High-contrast optical read for labels, metrics, and code statements.
- **Text Secondary (`#a1a1aa`):** Explanatory metadata, timestamps, and AST hierarchy indicators.
- **Text Muted (`#71717a`):** Line numbers, gutter keys, and disabled states.

### Operational State Accents
- **Compliance & Verified Pass (`#10b981` / `#059669`):** Represents verified Cedar policy integrity, successful non-destructive sandbox runs, and healthy autonomous state.
- **Simulation & Engine Replay (`#0284c7` / `#38bdf8`):** Applied strictly to offline Moto/SAM simulations, predictive execution trees, and graph traversal states.
- **Active Remediation & Warning (`#f59e0b` / `#d97706`):** Signals active agent rollbacks, throttled operations, bounded loops, and remediation locks.
- **Zero-Trust Critical Violation (`#f43f5e` / `#e11d48`):** High-alert interrupt for policy breaches, rogue egress attempts, and sandbox escape vectors.

---

## Typography

- **Headlines & Structural Titles:** Geist, negative tracking (`-0.02em` to `-0.03em`).
- **Interface & Operational Reading:** Inter (`11px`-`13px`) with high x-height and tabular figures.
- **Execution Code, Diffs, and Hashes:** JetBrains Mono (`font-feature-settings: "zero", "tnum"`).
- **Diff Rules:**
  - Additions: `#10b981` with subtle background tint `rgba(16, 185, 129, 0.08)`, left border `2px solid #10b981`.
  - Deletions: `#f43f5e` with subtle background tint `rgba(244, 63, 94, 0.08)`, left border `2px solid #f43f5e`.

---

## Shapes & Radii
- All buttons, inputs, cards, badges, and panes fixed at `0.25rem` (`4px`) maximum radius (`rounded: sm/md`).
- Status beacons: 6px geometric dots.
- Rounded radii greater than 4px are strictly prohibited.
