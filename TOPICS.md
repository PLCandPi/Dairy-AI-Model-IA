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
    "claim_type": "explicit_standard_concept | interpretation | common_practice"
  }
}
```

`think` and `reasoning_summary` are currently identical text - `think` is what
actually trains the model's `<think>` block (see README's note on why an
empty one is dangerous), `reasoning_summary` is the same content kept under
a name that survives if `think` is ever handled differently later.

`claim_type` is the important one: it's a decision tree, not a vibe.

```
Is this explicitly required/defined by the file's cited source
(an ISA standard, the FDA PMO, a manufacturer's manual, the actual
codebase)?
  YES -> explicit_standard_concept
  NO, but standard industry implementation practice -> common_practice
  NO, this is engineering judgment/interpretation -> interpretation
```

The point: prevent the model from learning "this is how ISA-18.2 works" when
the honest lesson is "this is one reasonable way engineers implement
ISA-18.2 concepts." `scripts/audit_claims.py` heuristically flags entries
where the wording and the `claim_type` label disagree - it's not a truth
oracle, just a tripwire for a human to look again.

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

_(empty right now)_

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
- FDA PMO Appendix H.VI ("Criteria for the Evaluation of Computerized
  Systems for Grade 'A' Public Health Controls") - surfaced during this
  session's audit (it's what makes a PLC-based FDD legal, contradicting an
  error we just fixed) but never actually read. Directly relevant to
  HeatWatch's own PLC-based, non-hard-wired design.
- Batch vs. continuous-flow HTST pasteurization control differences, deeper
  than what's seeded - the audit surfaced that these use genuinely different
  compliance mechanisms (cross-checked indicating/recording thermometers vs.
  a sealed thermal-limit-controller), which is richer material than a single
  entry captures.
