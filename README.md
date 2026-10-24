# OrderShield AI — Autonomous Risk Intelligence

A decentralized vendor compliance, Indian GSTIN verification, and multi-agent risk auditing platform powered by **FastAPI**, **Fetch.ai uAgents**, and a forensic **Three.js WebGL** interface.

---

## Features

- **Autonomous Risk Engine**: Multi-factor forensic scoring evaluating customer velocity, cross-border shipping/billing mismatch, disposable email detection, high-value transaction scrutiny, and vendor compliance.
- **Indian GSTIN Verification & State Registry**: Real-time checksum, state-code extraction (01-38), PAN parsing, and entity status validation.
- **Fetch.ai uAgent Protocol**: Decentralized agent communication running natively on port `8001` alongside FastAPI on port `8000`, enabling trustless agent-to-agent order auditing.
- **Forensic Investigation Workspace**: Dark titanium/silver glassmorphic UI with real-time discrepancy inspection, log stream provenance, and PDF invoice intake.
- **3D Liquid Chrome Cybernetic Core**: Interactive Three.js WebGL hero animation featuring a liquid silver Torus Knot, chiseled Quantum Prism, and 4D Tesseract with gyroscopic telemetry rings and real-time cursor parallax.

---

## Project Structure

```
ordershield/
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules (secrets, venv, cache)
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
├── server.py                 # Unified server entrypoint
├── uagent_service.py         # Fetch.ai uAgent protocol service
├── app/
│   ├── __init__.py
│   ├── config.py             # Pydantic v2 application settings
│   ├── validators.py         # Order validation & GSTIN regex/checksum rules
│   ├── registries.py         # Vendor registry client & state lookup tables
│   ├── verify.py             # Forensic risk scoring engine
│   └── main.py               # FastAPI routes & static file mounting
├── frontend/
│   └── index.html            # Forensic single-page app (Tailwind + Lucide + Three.js)
└── tests/
    ├── __init__.py
    ├── test_validators.py    # Unit tests for validation & GSTIN rules
    └── test_uagent.py        # Unit tests for uAgent message handler
```

---

## Quickstart

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/Antrikshcodes/ordershield.git
cd ordershield

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

### 3. Start the Server

```bash
python server.py
```

- **Web Dashboard**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Fetch.ai uAgent Node**: [http://localhost:8001](http://localhost:8001)

---

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Forensic Investigation Dashboard |
| `GET` | `/health/ready` | Readiness check & live Fetch.ai agent address |
| `POST` | `/v1/orders/verify` | Comprehensive order forensic risk evaluation |
| `POST` | `/v1/vendors/scan` | Vendor proof & Indian GSTIN lookup |
| `POST` | `/v1/documents/scan-pdf` | PDF invoice intake, OCR regex, and discrepancy analysis |

---

## Testing

Run unit tests with pytest:

```bash
pytest
```

---

## License

MIT License. Developed for autonomous risk intelligence and evidence-based auditing.