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

`claim_type` is the important one: it's a decision tree, not a vibe. It's
been through two revision rounds (2026-09-06, see git history for both
adversarial-review passes) as gaps in the taxonomy itself turned up during
real audits - not just gaps in individual entries:

- `explicit_requirement` - a directly quotable "shall"/"must" requirement.
- `explicit_standard_concept` - a defined term/structure/hierarchy the
  source states directly (not necessarily a binding "shall" clause).
- `explicit_standard_rationale` - the source's *own* explanatory/background
  text stating its reasoning for a requirement (e.g. the PMO's Appendix
  H.VI "Background" section, or its "Public Health Reason" narratives) -
  distinct from a requirement itself, and distinct from an entry where the
  rationale is our inference.
- `mixed_requirement_and_rationale` - a requirement plus the source's own
  stated reasoning for it, blended in one entry.
- `requirement_with_exception` - a requirement stated alongside the source's
  own explicit carve-out/exception to it (distinct from rationale - this is
  about scope, not "why"). Added after a review caught an entry that stated
  a rule as absolute while the source's very next sentence gave a permitted
  exception.
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
`explicit_standard_concept`, `explicit_standard_rationale`,
`mixed_requirement_and_rationale`, `requirement_with_exception`,
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

From the second adversarial-review pass (Appendix H.VI computerized-systems
batch):

- If a requirement includes an exception clause ("may be acceptable,
  provided..."), the exception must be stated in the same entry - never
  present the base rule as absolute and drop the carve-out
  (`requirement_with_exception`).
- When citing a specific numeric example from explanatory/background text
  (e.g. "1 millisecond," "100 milliseconds"), preserve the exact numbers
  rather than paraphrasing into vaguer language like "a fraction of a
  cycle" - the specificity is often the entire point of the example.
- Before writing about any project-specific system (HeatWatch or otherwise)
  in a hypothetical-regulatory-comparison entry, re-verify the specific
  factual claim about that system against its actual code in the same
  session, even if it was verified in an earlier entry - don't let a
  verified fact drift into an unverified restatement elsewhere (an earlier
  draft claimed HeatWatch "never touches a real actuator/relay," directly
  contradicted by this project's own verified poller.py code).
- When a source defines several closely related technical terms in its own
  glossary (e.g. ROM vs. EPROM vs. EEPROM vs. EAPROM), check whether a
  requirement's wording ("some form of ROM") is actually resolved by those
  definitions or genuinely ambiguous against them - don't silently pick the
  convenient reading; flag the ambiguity instead.
- Any entry combining a bare "shall" requirement with an explanatory "why"
  must use the explicit template: "The [source] requires X. From an
  engineering perspective, this addresses Y." - never blend the two into
  one unmarked sentence.

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
- **`data/computerized_systems_seed.jsonl`** (8 entries, FDA PMO Appendix
  H.VI part 1) and **`data/appendix_hvi_part2_seed.jsonl`** (7 entries,
  part 2) - covers why computerized systems are treated differently from
  hard-wired ones (with the PMO's own exact numbers), dedicated-computer
  requirement (with its actual exceptions/scope), fail-safe/last-state
  behavior, ROM terminology ambiguity (flagged, not resolved), FORCE-ON/
  FORCE-OFF, LOSA/HFA/PDD (verified verbatim), sealed reprogrammable
  peripherals, scan-cycle timing, sealed modem access with the PMO's own
  compromise-testing method, printing-diversion limits, event/temperature
  correlation, clean-power RAM-corruption risk, and CIP-mode interlocks.
  Both went through two full adversarial-review passes. **Note:** part 2's
  7 entries have no `think` field (explicit user instruction on that
  round) - they will train empty `<think>` blocks unless that's addressed
  before the next training run.
- **`data/batch_vs_htst_seed.jsonl`** (5 entries) - why continuous flow
  needs an automatic FDD while batch doesn't (a discrete release boundary
  checked once vs. the same decision made continuously on a moving stream
  - not "human vs. automatic"), what's shared between the two (cross-
  checked indicating/recording thermometers), batch-specific airspace
  heating (the PMO's own stated Public Health Reason, not inferred) and
  close-coupled valves (the actual 0.5C/1F tolerance), and why HTST needs
  tube geometry, flow-rate monitoring (LOSA/HFA), *and* a temperature
  interlock together - three independent failure modes, not two.

## Drafted, pending review (data/pending/)

_(empty right now)_

## Needs work (flagged by auto_eval.py or manual review)

_(auto_eval.py appends here when a case fails - see eval_report.json for the
actual flagged answer)_

## Queued (not yet researched)

- ~~Confirm whether `poller.py`'s "AIME 8U" is the PPI AIMS-8U~~ - confirmed
  by the user directly: the poller(s) are Modbus-based. No further
  investigation needed on this specific question.
- **Generic Modbus protocol fundamentals** (register types - coils, discrete
  inputs, input registers, holding registers; RTU vs. TCP; function codes;
  master/slave polling model; addressing conventions) - raised by the user
  explicitly: dataset should stay universal/transferable, not centered on
  the AIMS-8U module or HeatWatch specifically (see
  `feedback_dairy_ai_universal_scope` in cross-session memory). Needs new
  research (protocol spec, not project-specific).
- RTD/thermocouple wiring fault modes beyond what's already seeded (open
  circuit vs. short vs. drift signatures on a trend).
- ISA-88 recipe types (General/Site/Master/Control recipe) - deliberately
  left out of the ISA batch since I wasn't confident enough in the exact
  terminology to avoid inventing something. Worth doing properly with
  better source access.
