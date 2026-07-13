# Context Model

This document separates implemented historical environmental enrichment from
provider-neutral future contracts for scheduled, operational, and broader
context. The environmental enrichment described in the first section is
implemented; the later context-event and context-observation contracts remain
roadmap design.

## Implemented Historical Environmental Enrichment

Accepted phone-derived boundary events are enriched asynchronously after the
raw event has been committed to SQLite and after derived projections are
complete. Enrichment is not part of mobile acknowledgment and not part of the
raw acceptance transaction.

The enrichment lifecycle is intentionally sequential:

- select the oldest unfinished accepted event by `events.id ASC`
- process exactly one event per worker invocation
- use lifecycle states `pending`, `retry`, `complete`, and `terminal`
- retry transient failures without allowing newer events to jump ahead
- use a recovery timer for backlog, missed triggers, reboot recovery, and
  retry work

The inputs are the accepted event record:

- historical event timestamp
- stored event coordinates
- normalized UTC environmental hour

The outputs are historical-time context:

- astronomy calculated for the event's historical time
- weather selected for the corresponding UTC hour
- raw numeric environmental values preserved separately from descriptive labels

This is modeled regional context. It is not doorway-local sensor truth, not
current weather, and not a claim that environmental conditions caused movement
behavior. Route-level correlation, confidence scoring, learned windows, and
recommendations remain future work.

## Future Context Contracts

The following contracts define provider-neutral shapes for later context
expansion. They are not fully implemented yet.

Use two contracts rather than one overloaded table:

- `context_event`: bounded scheduled occurrences.
- `context_observation`: measured conditions at a time or over an interval.

## Context Categories

Environmental examples:

- weather
- precipitation
- temperature
- wind
- snow and ice
- visibility
- daylight
- sunrise
- sunset
- twilight
- air quality

Scheduled public context examples:

- holidays
- school calendars
- university calendars
- sports and venue events
- graduations
- concerts
- parades
- protests
- political visits
- construction
- planned road closures

Historical/operational context examples:

- weekday/weekend
- time-of-day bucket
- recurring route baseline
- recent route duration distribution
- known seasonal pattern
- unusual deviation from baseline

## Context Event Contract

For bounded scheduled occurrences:

| Field | Meaning | Kind | Null behavior | Privacy notes |
| --- | --- | --- | --- | --- |
| `id` | Local normalized event ID | generated | never null | public-safe synthetic ID in examples |
| `source_id` | Provider/source record ID | observed | nullable if manually entered | can fingerprint source; sanitize |
| `source_type` | Provider class, such as venue-calendar | normalized | never null | avoid private account names |
| `category` | Event category | normalized | never null | use broad categories publicly |
| `title` | Human-readable title | observed/normalized | nullable | can reveal sensitive schedules |
| `starts_at` | Scheduled start time | observed | nullable if unknown | public examples use fake times |
| `ends_at` | Scheduled end time | observed | nullable | event time is not impact time |
| `venue_name` | Venue/place name | observed/normalized | nullable | public examples use fictional venues |
| `venue_latitude` | Venue latitude | observed | nullable | public examples use synthetic coordinates |
| `venue_longitude` | Venue longitude | observed | nullable | public examples use synthetic coordinates |
| `status` | scheduled, cancelled, postponed, tentative | normalized | nullable | supports update behavior |
| `impact_profile_id` | Reference to a configured impact profile | normalized link | nullable | keep assumptions separate from source facts |
| `source_updated_at` | Source update timestamp | observed | nullable | useful for freshness |
| `retrieved_at` | Retrieval timestamp | system | never null | provenance metadata |

## Context Observation Contract

For measured or derived conditions:

| Field | Meaning | Kind | Null behavior | Privacy notes |
| --- | --- | --- | --- | --- |
| `id` | Local normalized observation ID | generated | never null | public-safe synthetic ID in examples |
| `source_id` | Provider/source record ID | observed | nullable | sanitize provider identifiers |
| `category` | Observation category | normalized | never null | examples: temperature, air-quality |
| `observed_at` | Instant observed by source | observed | nullable if interval-only | public examples use fake times |
| `valid_from` | Start of validity interval | observed/normalized | nullable | not always available |
| `valid_until` | End of validity interval | observed/normalized | nullable | not always available |
| `value_numeric` | Numeric value | observed/normalized | nullable | use units explicitly |
| `value_text` | Text value or bucket | observed/normalized | nullable | avoid free-form private notes |
| `unit` | Unit for numeric value | normalized | nullable | required when numeric value exists |
| `severity` | normalized severity bucket | normalized | nullable | provider-neutral |
| `location_scope` | point, corridor, city, region | normalized | nullable | limits overprecision |
| `latitude` | Point latitude if relevant | observed | nullable | synthetic in public examples |
| `longitude` | Point longitude if relevant | observed | nullable | synthetic in public examples |
| `retrieved_at` | Retrieval timestamp | system | never null | provenance metadata |

## Impact Windows

Event time is not impact time.

Example:

```text
scheduled event:
  starts_at = 19:00

possible arrival-pressure window:
  16:30-19:30

possible departure-pressure window:
  21:00-22:30
```

These windows are assumptions, not universal facts.

Conceptual impact profile:

| Field | Meaning |
| --- | --- |
| `profile_id` | Stable profile identifier |
| `category` | Context category this profile applies to |
| `lead_minutes` | Minutes before event start when impact may begin |
| `trailing_minutes` | Minutes after event end when impact may continue |
| `radius_m` | Approximate spatial reach |
| `expected_effect` | Expected operational effect such as delay or crowding |
| `confidence` | low, moderate, high |
| `rationale` | Public-safe explanation of the assumption |

Impact profiles may combine configured assumptions, source metadata, and learned
historical behavior. Keep configured assumptions separate from learned
observations so the system can explain which is which.
