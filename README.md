# NeuroPharmDB

An Apple-inspired, local-first drug-drug interaction web app powered by a DrugBank SQLite database. NeuroPharmDB lets users search medicines, audit prescription lists, inspect interaction risk, and generate explainable AI-style patient-context insights without sending data to any external API.

> Built for fast clinical-style exploration, academic demos, and explainable pharmacology workflows.

## Highlights

- **Drug-drug interaction checker** for two or more selected medicines
- **Automated prescription audit** from a pasted medicine list
- **Autocomplete drug search** backed by DrugBank names and synonyms
- **Patient-context risk scoring** for pregnancy, kidney disease, liver disease, bleeding risk, older adult, diabetes, hypertension, and alcohol use
- **Explainable AI panel** with matched terms, evidence snippets, source fields, and point contributions
- **Interaction graph** showing pairwise risk relationships
- **Food and supplement warnings** from DrugBank food interaction data
- **Shared biology insights** across categories, targets, and enzymes
- **Alternative drug suggestions** based on shared structured DrugBank signals
- **Drug profile modal** with description, targets, enzymes, categories, and food warnings
- **Exportable report** for printing or saving as PDF
- **Light and dark mode** with minimal glass-style UI

## Why It’s Different

Most interaction checkers simply say whether two medicines interact. NeuroPharmDB adds a transparent reasoning layer:

1. It checks every selected drug pair.
2. It scans local DrugBank pharmacology fields.
3. It matches patient-specific risk contexts.
4. It shows the exact evidence text used to score risk.
5. It produces a readable audit-style output.

The “AI” is intentionally explainable. It is a local rule-assisted risk summarizer, not a black-box clinical model.

## Screens / Demo Flow

Recommended demo:

1. Paste a medication list into **Automated prescription audit**.
2. Use autocomplete suggestions to normalize drug names.
3. Click **Run audit**.
4. Review interaction severity and graph.
5. Select patient context chips such as `Bleeding risk`, `Kidney disease`, or `Pregnancy`.
6. Open **Explainable AI** to show why the score was generated.
7. Export the report.

## Tech Stack

- **Backend:** Python standard library HTTP server
- **Database:** SQLite DrugBank export
- **Frontend:** Vanilla HTML, CSS, JavaScript
- **No build step**
- **No external API required**

## Project Structure

```text
NeuroPharmDB 2.0/
├── app.py                 # Python HTTP server and API endpoints
├── drugbank_full.db       # Local DrugBank SQLite database
├── drugbank_full.db.zip   # Compressed database archive
├── static/
│   ├── index.html         # App shell
│   ├── app.css            # Apple-like glass UI
│   └── app.js             # Search, audit, interactions, AI panels
└── README.md
```

## Setup

Clone the repo:

```bash
git clone <your-repo-url>
cd "NeuroPharmDB 2.0"
```

Make sure the database exists:

```bash
ls drugbank_full.db
```

If only the zip file is present:

```bash
unzip drugbank_full.db.zip
```

Run the app:

```bash
python3 app.py
```

Open:

```text
http://127.0.0.1:8000
```

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `/api/stats` | Database counts |
| `/api/search?q=` | Drug search by name/synonym |
| `/api/options?q=` | Dropdown/default drug options |
| `/api/check-many?ids=` | Pairwise interaction check |
| `/api/ai-insights?ids=` | Local AI-style summary, graph, food warnings, shared biology |
| `/api/patient-risk?ids=&contexts=` | Explainable patient-context risk score |
| `/api/similar?drug=` | Alternative/similar drug suggestions |
| `/api/drugs/<id>` | Drug profile |
| `/api/drugs/<id>/interactions?q=` | Browse interactions for one drug |

## Explainable AI Method

The patient-context scorer scans selected DrugBank records across:

- description
- indication
- pharmacodynamics
- mechanism
- toxicity
- metabolism
- absorption
- half-life
- route of elimination
- food interactions
- pairwise interaction text

It then matches context-specific terms, such as:

- `bleeding`, `anticoagulant`, `INR`
- `renal`, `kidney`, `ESRD`
- `hepatic`, `CYP`, `metabolism`
- `pregnancy`, `fetal`, `teratogen`
- `avoid alcohol`, `CNS depression`, `drowsiness`

Risk is boosted by high-attention language like:

- `contraindicated`
- `fatal`
- `life-threatening`
- `severe`
- `toxicity`
- `increased risk`

Every result includes:

- matched context
- matched drug
- source field
- evidence excerpt
- matched terms
- point contribution

## Important Disclaimer

NeuroPharmDB is a research and educational decision-support tool. It is not a medical device, does not provide medical advice, and should not be used as a substitute for professional clinical judgment.

DrugBank content may require appropriate licensing depending on use and distribution. Do not publish proprietary DrugBank data unless your license allows it.

## Roadmap Ideas

- Saved audit cases
- CSV upload for prescriptions
- PDF report styling
- Mechanism-based CYP/target risk graph
- Safer alternative ranking against the current medication list
- Lab monitoring recommendations
- Admin/import script for refreshing DrugBank data

## Author

Built by Harshit as a full-stack pharmacology informatics project.

