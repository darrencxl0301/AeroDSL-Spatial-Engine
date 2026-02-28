# 🛫 AeroDSL Spatial Engine

> A spatial-temporal abstraction layer for legacy aviation GDS DSL systems — integrating symbolic parsing, indexed airport resolution, geodesic computation, timezone-aware modeling, and interactive route visualization.

![Demo](assets/demo.gif)

---

## 1. Background — The Invisible Infrastructure of Air Travel

Every time someone books a flight, the transaction passes through one of the world's oldest and most resilient software systems: a **Global Distribution System**, or GDS.

GDS platforms — primarily **Amadeus**, **Sabre**, and **Travelport** — were built in the 1960s and 70s as the backbone of airline reservation infrastructure. They connect airlines, travel agents, and booking engines worldwide, processing hundreds of millions of transactions daily. Decades later, they still run. Not because they haven't been replaced, but because they were engineered so efficiently that replacement has never been worth the cost.

These systems communicate through a compact **Domain-Specific Language (DSL)** — a symbolic command syntax designed for trained terminal operators who needed to issue complex queries in as few keystrokes as possible.

A typical availability query looks like this:

```
AN12DECKULSIN
```

To an uninitiated user, this is noise. To a GDS operator, it reads instantly:

| Token | Value | Meaning |
|-------|-------|---------|
| `AN` | Availability request | Query intent |
| `12DEC` | December 12th | Travel date |
| `KUL` | Kuala Lumpur Intl | Origin airport |
| `SIN` | Singapore Changi | Destination airport |

The syntax was never designed to be readable. It was designed to be **fast** — and for its era, it succeeded. A trained agent could issue dozens of queries per minute without lifting their eyes from the screen.

### The Cost of Symbolic Compression

This efficiency came with a set of fundamental constraints that have never been resolved:

**No spatial awareness.** The system has no concept of where KUL or SIN are in the world. It knows they are valid IATA codes. It does not know they sit 350 km apart, separated by the Strait of Malacca, or that crossing between them takes roughly 55 minutes at cruise altitude.

**No temporal reasoning.** A date like `12DEC` is accepted or rejected syntactically. The system does not model what `12DEC` means in local time at origin versus destination — the timezone gap between KUL and SIN is small, but on transatlantic or transpacific routes, the ambiguity becomes operationally significant.

**No validation feedback.** Malformed commands typically produce cryptic error codes rather than structured diagnostics. New operators spend months learning to interpret failure states.

**No discoverability.** If you don't already know the IATA code for an airport, the system will not help you find it. It assumes operator knowledge, not operator learning.

These are not bugs — they are deliberate design choices that made sense in 1970. The question AeroDSL asks is: **what if we could add spatial and temporal intelligence to this system without touching its syntax at all?**

---

## 2. Project Objective

AeroDSL is not a GDS replacement. Replacing GDS infrastructure is a multi-decade, multi-billion-dollar undertaking that the industry has attempted and largely abandoned several times.

Instead, AeroDSL introduces a **spatial-temporal abstraction layer** — a system that sits above GDS syntax, accepts the same symbolic input, and augments it with the spatial and temporal context that the original system was never designed to provide.

The same command that a GDS operator types today:

```
AN12DECKULSIN
```

Becomes, in AeroDSL:

- A parsed, validated structure with live error feedback
- A resolved pair of airports with full geographic metadata
- A geodesic route drawn on an interactive map
- A distance computation and estimated flight duration
- Departure and arrival times expressed in local timezone at each airport

The syntax is unchanged. The understanding is not.

---

## 3. System Architecture

The processing pipeline follows a strict unidirectional flow — each layer has a single responsibility and passes a structured artifact to the next:

```
DSL Input (raw string)
    ↓
Parser — Deterministic segmentation, intent and date validation
    ↓
Symbol Resolver — O(1) IATA index lookup, metadata enrichment
    ↓
Geospatial Computation — Haversine distance, cruise-based time estimate
    ↓
Temporal Modeling — Timezone-aware local time computation
    ↓
Visualization — Interactive Leaflet map, animated route rendering
```

Each layer is independently testable and replaceable. The parser does not know about maps. The resolver does not know about timezones. This separation was a deliberate design constraint — it keeps the system extensible and prevents the kind of cross-layer coupling that makes systems like GDS difficult to modernize.

---

## 4. DSL Parsing Layer

### Design Decision: Deterministic Segmentation over Pattern Matching

GDS commands follow a fixed-width format. This is not a limitation to work around — it is a guarantee to exploit.

```
[2 chars] [5 chars] [3 chars] [3 chars]
   AN       12DEC      KUL       SIN
```

Rather than using regex-based parsing (which introduces backtracking complexity and fragile edge cases), the parser uses **deterministic positional slicing**:

```python
prefix = command[0:2]    # → "AN"
date   = command[2:7]    # → "12DEC"
origin = command[7:10]   # → "KUL"
dest   = command[10:13]  # → "SIN"
```

Parsing complexity: **O(1)**. No lookahead, no backtracking, no ambiguity.

### Validation Rules

After segmentation, each token is validated independently:

- `prefix` must equal `AN` (the only currently supported intent)
- `date` must match the `DDMMM` pattern — day as two digits, month as three-letter abbreviation
- `origin` and `destination` must be exactly 3 characters and present in the IATA index
- Tokens are validated in isolation, so the system can identify *which* field is malformed, not just that the command failed

This produces structured diagnostics rather than binary pass/fail — the foundation for the live error feedback in the UI.

![Validation and Error Feedback](assets/error.png)

---

## 5. Airport Intelligence Layer

### The IATA Code Problem

There are approximately 9,000 active IATA airport codes worldwide. Operators of GDS systems memorize the codes relevant to their markets. Everyone else is lost.

AeroDSL resolves this through a **preprocessed, indexed airport dataset** — a normalized snapshot of global airport metadata that enables both exact symbolic lookup and fuzzy search from a single data structure.

### Airport Schema

Each airport is stored as a flat, normalized object:

```json
{
  "iata": "KUL",
  "icao": "WMKK",
  "name": "Kuala Lumpur International Airport",
  "city": "Kuala Lumpur",
  "country": "Malaysia",
  "lat": "2.7456",
  "lon": "101.7072",
  "tz": "Asia/Kuala_Lumpur"
}
```

The schema was deliberately pruned during preprocessing. Fields irrelevant to the spatial-temporal use case (airline affiliations, terminal counts, elevation data) were removed to minimize memory footprint and improve lookup speed.

### Indexing Strategy

On initialization, the resolver constructs a dictionary index keyed by IATA code:

```python
airport_iata_index = {
    "KUL": { ... },
    "SIN": { ... },
    # ~9,000 entries
}
```

| Operation | Strategy | Complexity |
|-----------|----------|------------|
| IATA lookup | Dictionary index | O(1) |
| Autocomplete search | Linear scan with early stop | O(n) |
| Name-based resolution | Linear scan | O(n) |

The O(1) path handles the primary GDS use case — symbolic code resolution — while the linear paths support the discoverability features that GDS never offered.

![Airport Search and Autocomplete](assets/list.png)

---

## 6. Geospatial Computation

### Why Haversine?

The shortest path between two airports is not a straight line on a map — it is a **great-circle arc** across a spherical surface. A flat Euclidean distance calculation would be meaningfully wrong for any route spanning more than a few hundred kilometers.

The **Haversine formula** computes great-circle distance on a spherical Earth model:

```
a = sin²(Δφ/2) + cos φ₁ · cos φ₂ · sin²(Δλ/2)
c = 2 · atan2(√a, √(1−a))
distance = R · c
```

Where:
- `φ` = latitude in radians
- `λ` = longitude in radians
- `R` = 6371 km (mean Earth radius)

This approximation introduces a maximum error of roughly 0.5% compared to more accurate ellipsoidal models (such as Vincenty) — acceptable for the estimation use case and significantly simpler to implement and reason about.

Computation complexity: **O(1)**

### Flight Time Estimation

Estimated flight duration is modeled as:

```
duration = (distance / cruise_speed) + operational_buffer
```

Where:
- `cruise_speed` ≈ 850 km/h (typical narrowbody cruise)
- `operational_buffer` ≈ 0.5 hours (taxi, climb, descent)

This is a deliberate simplification. Actual flight times vary with aircraft type, route altitude, wind, and airspace constraints. The model abstracts over all of these — its purpose is temporal orientation, not dispatch planning.

---

## 7. Temporal Modeling

One of the quiet complexities of aviation is that **times are always local**. A departure at 08:00 from KUL and an arrival at 09:00 in SIN does not mean the flight took one hour — it means you need to know both timezones to reconstruct the actual duration.

AeroDSL propagates timezone data from the airport schema into the computation layer:

```javascript
new Date().toLocaleString('en-US', { timeZone: airport.tz })
```

Each airport's `tz` field (e.g., `"Asia/Kuala_Lumpur"`, `"Asia/Singapore"`) is used to compute local departure and arrival times. For a KUL→SIN route both are UTC+8, so the offset is zero — but the same logic applied to a JFK→LHR route correctly handles the 5-hour gap.

This adds genuine temporal reasoning to what was previously a purely symbolic system.

---

## 8. Spatial Visualization Engine

The visualization layer is built on **Leaflet.js** — a lightweight, open-source mapping library that handles lat/lon projection, tile rendering, and interactive layer management without requiring a heavy frontend framework.

### Route Rendering

When a valid command is parsed and resolved, the engine:

1. Places markers at origin and destination coordinates
2. Draws a geodesic polyline between them
3. Initializes an animated aircraft icon along the route

### Animation Model

The flight animation uses linear interpolation along the polyline:

```javascript
progress ∈ [0, 1]

lat = lat₁ + (lat₂ - lat₁) × progress
lon = lon₁ + (lon₂ - lon₁) × progress
```

`progress` increments continuously on each animation frame and resets to 0 on completion, simulating a recurring flight loop. The interpolation is linear rather than great-circle — visually indistinguishable at the zoom levels used, and significantly cheaper to compute per frame.

![Route Visualization](assets/result.png)

---

## 9. Data Pipeline

Raw aviation datasets contain significant noise: duplicate entries, inconsistent field naming, deprecated codes, and irrelevant metadata. The preprocessing pipeline — implemented as a Jupyter notebook — normalizes the raw data before it enters the system.

**Input:**
```
data/airports.json
data/airlines.json
```

**Processing steps:**
- Field normalization (standardize key names and value formats)
- Key pruning (remove fields unused by the resolver or visualization layer)
- Coordinate preservation (retain lat/lon to full precision)
- Timezone retention (propagate tz strings for temporal modeling)
- Schema simplification (flatten nested structures)

**Output:**
```
data/clean_airports.json
data/clean_airlines.json
```

Preprocessing runs once at build time. The resolver loads only the cleaned output, keeping runtime memory footprint minimal and lookup paths simple.

---

## 10. Technical Summary

| Concern | Approach | Rationale |
|---------|----------|-----------|
| DSL parsing | Deterministic positional slicing | O(1), no regex fragility |
| IATA resolution | Dictionary index | O(1) exact lookup |
| Distance computation | Haversine formula | Spherical approximation, <0.5% error |
| Flight time estimation | Cruise speed + fixed buffer | Abstracts fleet complexity |
| Temporal modeling | IANA timezone strings | Standard, portable, DST-aware |
| Route animation | Linear interpolation | Visually sufficient, frame-efficient |
| Frontend | Vanilla JS + Leaflet.js | No framework overhead |
| Backend | FastAPI | Async-capable, minimal boilerplate |

---

## 11. Repository Structure

```
app/
    main.py                 # FastAPI entry point

core/
    parser.py               # DSL segmentation and validation
    resolver.py             # IATA index and airport lookup
    generator.py            # Response assembly
    date_utils.py           # Date parsing and normalization

data/
    airports.json           # Raw airport dataset
    airlines.json           # Raw airline dataset
    clean_airports.json     # Preprocessed airport index
    clean_airlines.json     # Preprocessed airline index
    preprocess.ipynb        # Data cleaning pipeline

templates/
    index.html              # Frontend (Leaflet + vanilla JS)

assets/
    demo.gif
    error.png
    list.png
    result.png

static/
    plane.png               # Animation sprite
```

---

## 12. Future Extensions

The current implementation handles single-segment availability queries. Several natural extensions follow from the existing architecture:

- **Multi-segment routing** — parsing and visualizing connecting itineraries (e.g., `KUL → SIN → NRT`)
- **Great-circle animation** — replacing linear interpolation with true spherical arc traversal
- **Aircraft performance modeling** — incorporating fleet-specific speed and range data
- **Weather overlay** — integrating real-time SIGMET/METAR data along the route
- **Airline network visualization** — rendering full carrier route maps from the airlines dataset

---

## 13. Project Scope

> **Symbolic DSL × Indexed Data Structures × Geospatial Computation × Temporal Modeling**

AeroDSL is a focused architectural experiment in one specific question: can a symbolic command system designed for terminal efficiency be given spatial and temporal awareness — without modifying the commands themselves?

The answer, demonstrated here, is yes. The same four tokens that a GDS operator types today contain enough information to place two airports on a globe, compute the arc between them, estimate how long it takes to fly it, and express that duration in the local time of both cities.

The syntax hasn't changed. The understanding has.
