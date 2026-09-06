# Topic queue

Tracks what's been researched into training data and what's next. Updated by
whoever (person or Claude session) runs a research round.

## Data schema (as of 2026-09-06)

Every entry in `data/*.jsonl` now carries:

```json
{
  "instruction": "...", "input": "",
  "think": "...", "reasoning_summary": "...",
  "output": "...",
  "metadata": {
    "domain": "...", "standard": "...",
    "category": "...", "difficulty": "...",
    "claim_type": "see taxonomy below"
  }
}
```

`think` and `reasoning_summary` are currently identical text - `think` is what
actually trains the model's `<think>` block (see README's note on why an
empty one is dangerous), `reasoning_summary` is the same content kept under
a name that survives if `think` is ever handled differently later.

`claim_type` is the important one: it's a decision tree, not a vibe. As of
the 2026-09-06 adversarial-review pass (see git history), the original
3-value scheme (explicit_standard_concept / interpretation / common_practice)
was replaced with a richer 7-value taxonomy that forces a real distinction
between "the standard says X," "the standard's own narrative explains why X"
(different from the requirement itself), and "I'm inferring why X":

- `explicit_requirement` - a directly quotable "shall"/"must" requirement.
- `explicit_standard_concept` - a defined term/structure/hierarchy the
  source states directly (not necessarily a binding "shall" clause).
- `mixed_requirement_and_rationale` - a requirement plus the source's *own*
  stated reasoning for it (e.g. the PMO's "Public Health Reason" narrative
  sections) - distinct from an entry where the rationale is our inference.
- `failure_mode_analysis` - reasoning built around enumerating independent
  ways a system/requirement could fail, and which mechanism catches each.
- `comparison_inference` - a comparison between two things (e.g. batch vs.
  continuous-flow) where the framing is our synthesis across sources, not
  something either source states in those terms.
- `engineering_rationale` - our own inferred "why," not sourced from the
  standard's own explanatory text.
- `derived_from_standard` - a conclusion that follows from a requirement but
  isn't itself stated.
- `common_practice` - general industry practice, not tied to a cited source.

High-confidence bucket (`scripts/audit_claims.py`'s heuristic treats these as
where absolute/unhedged wording is expected): `explicit_requirement`,
`explicit_standard_concept`, `mixed_requirement_and_rationale`,
`failure_mode_analysis`. Everything else is a "softer" claim where hedged
wording is expected - unhedged wording there is a sign of overclaiming.

The point throughout: prevent the model from learning "this is how ISA-18.2
works" when the honest lesson is "this is one reasonable way engineers
implement ISA-18.2 concepts," and prevent conflating "the standard explains
its own reasoning" with "I inferred this reasoning." `scripts/audit_claims.py`
heuristically flags entries where the wording and the `claim_type` label
disagree - it's not a truth oracle, just a tripwire for a human to look
again.

Before writing any comparison entry: ask whether the memorable one-line
takeaway actually is the precise distinction, or a simplification that
happens to sound like it (a batch-vs-continuous entry framed as "human
checking vs. automatic safety" taught the wrong generalizable lesson even
though every individual sentence in it was defensible).

Before finalizing any "why" entry: check whether the source's own
explanatory/narrative text (not just its "shall" requirements) already
states the rationale - if so, cite that directly (`mixed_requirement_and_rationale`)
rather than presenting the same explanation as if it were purely inferred
(`engineering_rationale`).

Before finalizing any "mechanism X protects against Y" entry: explicitly
enumerate every independent failure mode in play first, rather than
defaulting to whichever two mechanisms are most salient - a real gap was
found this way (a holding-tube-sizing entry that covered temperature and
residence-time protection but omitted flow-rate governance/measurement as
a third, independent failure mode).

## Done (merged into data/, audited 2026-09-06)

All four live files were audited this session - not just for schema, for
actual technical correctness. Real errors found and fixed, not just
relabeled:

- **`data/analog_io_seed.jsonl`** (6 entries, PPI AIMS-4X/8X manual) -
  content verified accurate against the manual directly (sentinel values,
  22-ohm lead compensation, 0-90% filter range, CJC purpose, resolution
  scaling all checked). No content errors found - just added the metadata
  schema.
- **`data/pmo_regulatory_seed.jsonl`** (6 entries, FDA Grade "A" PMO 2017
  revision) - two real errors fixed: thermal-limit-controller sealing was
  misattributed to batch pasteurizers (it's an HTST continuous-flow
  requirement); the "holding tube sized for 2x the fastest particle" rule
  was presented as a general holding-tube requirement when the PMO text
  scopes it specifically to HHST systems.
- **`data/heatwatch_codebase_seed.jsonl`** (15 entries, HeatWatch
  poller.py/server.js) - verified against the live code on the deployed Pi
  (not just read once, re-checked this session). Two real errors fixed: one
  entry had a failure mode backwards (claimed a parse error leaves the
  chilling alarm "stuck" suppressed - tracing the actual control flow shows
  it already fails toward safety instead); another falsely claimed
  server.js uses the same atomic tmp-file-write pattern poller.py does -
  verified directly, it doesn't (every server.js write is a plain
  `fs.writeFileSync`), which is itself a real, more interesting finding.
  Also: this file had **no `think` field at all** before this pass - all 15
  entries would have trained on empty reasoning blocks.
- **`data/dairy_domain_seed.jsonl`** (20 entries, general HTST/CIP domain
  knowledge) - two real errors fixed: the FDV was described as necessarily
  "hard-wired, not software-mediated," but the PMO explicitly permits
  evaluated computerized/PLC-based control (Appendix H.VI); the ambient
  temperature channel entry gave a different, unverified explanation than
  the *verified* cold-junction-compensation answer already established in
  `analog_io_seed.jsonl` - two files contradicting each other on the same
  question. Also had **no `think` field at all** before this pass, same gap
  as heatwatch_codebase.
- **`data/isa_standards_seed.jsonl`** (30 entries, ISA-88/ISA-18.2) -
  drafted, adversarially audited, and corrected in the same session (see
  git history for the full correction list); merged from `data/pending/`
  after review.

## Drafted, pending review (data/pending/)

- **Computerized/PLC-based public health controls** (FDA PMO Appendix
  H.VI) - `data/pending/computerized_systems_seed.jsonl`, 8 entries. Covers
  why computerized systems are treated differently from hard-wired ones
  (sequential task cycling, easily-changed logic, error-free requirement),
  dedicated-computer requirement, fail-safe/last-state-switch behavior, ROM
  program storage, FORCE-ON/FORCE-OFF indicator requirement, the LOSA/HFA/
  PDD acronyms from the FDD logic diagrams, and sealed hardware-disable
  switches for reprogrammable peripherals. One entry directly cross-checks
  PMO criterion 11 (no accessible operator override switches) against
  HeatWatch's own manual-test override design. All entries directly
  verified against the primary PMO text (not a secondary source), tagged
  `explicit_standard_concept` throughout.
- **Batch vs. continuous-flow HTST comparison** -
  `data/pending/batch_vs_htst_seed.jsonl`, 5 entries. Covers why continuous
  flow needs an automatic FDD while batch doesn't (no natural single
  gating moment vs. product always in motion), what's actually shared
  between the two (cross-checked indicating/recording thermometers), batch-
  specific airspace heating and close-coupled valves (both about physical
  locations the bulk-liquid thermometer can't see), and why HTST needs both
  tube-geometry sizing *and* a real-time thermal interlock (two different
  failure modes - not enough time vs. not enough heat).

Both passed `scripts/review_pending.py` and `scripts/audit_claims.py`.
Need a human read before merging into `data/`.

## Needs work (flagged by auto_eval.py or manual review)

_(auto_eval.py appends here when a case fails - see eval_report.json for the
actual flagged answer)_

## Queued (not yet researched)

- Confirm whether `poller.py`'s "AIME 8U" is actually the PPI AIMS-8U
  (Modbus/RS-485) found this session, or a different device reached through
  an HTTP/XML gateway - `AIME_URL = "http://192.168.1.2/index.xml"` doesn't
  match a Modbus-only device directly.
- RTD/thermocouple wiring fault modes beyond what's already seeded (open
  circuit vs. short vs. drift signatures on a trend).
- ISA-88 recipe types (General/Site/Master/Control recipe) - deliberately
  left out of the ISA batch since I wasn't confident enough in the exact
  terminology to avoid inventing something. Worth doing properly with
  better source access.
