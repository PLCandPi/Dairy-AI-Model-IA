# Topic queue

Tracks what's been researched into training data and what's next. Updated by
whoever (person or Claude session) runs a research round.

## Done (merged into data/)

- Analog input module domain (Modbus sentinel values, alarm hysteresis, RTD
  wiring, IIR filtering, CJC) - `data/analog_io_seed.jsonl`, sourced from the
  PPI AIMS-4X/8X user manual.
- FDA Grade "A" Pasteurized Milk Ordinance, 2017 revision (HTST temp/time
  table, FDD behavior and placement, holding tube sizing/slope, HHST timing
  basis, thermal-limit-controller sealing) - `data/pmo_regulatory_seed.jsonl`.

## Needs work (flagged by auto_eval.py or manual review)

_(auto_eval.py appends here when a case fails - see eval_report.json for the
actual flagged answer)_

## Queued (not yet researched)

- ISA-88 batch/procedural control model - maps onto CIP cycle stages.
- ISA-18.2 alarm management / rationalization - broader than the single
  hysteresis fact already covered.
- Confirm whether `poller.py`'s "AIME 8U" is actually the PPI AIMS-8U
  (Modbus/RS-485) found this session, or a different device reached through
  an HTTP/XML gateway - `AIME_URL = "http://192.168.1.2/index.xml"` doesn't
  match a Modbus-only device directly.
- RTD/thermocouple wiring fault modes beyond what's already seeded (open
  circuit vs. short vs. drift signatures on a trend).
