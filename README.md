# Automated CO–PO & CO–PSO Mapping System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.4%2B-orange.svg)](https://scikit-learn.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Accreditation](https://img.shields.io/badge/Accreditation-NBA%20%7C%20NAAC%20%7C%20Washington%20Accord-navy.svg)](#)

An intelligent, explainable Outcome-Based Education (OBE) articulation and mapping platform engineered for higher education institutions following the National Board of Accreditation (NBA) and Washington Accord frameworks.

Developed for **Sant Dnyaneshwar Shikshan Sanstha's Annasaheb Dange College of Engineering and Technology (ADCET), Ashta** (Department of Artificial Intelligence & Data Science and Multi-Department Support).

---

## Table of Contents
- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Objectives](#objectives)
- [Key Features](#key-features)
- [Methodology & Mapping Engine](#methodology--mapping-engine)
- [Technology Stack](#technology-stack)
- [Project Architecture & Directory Structure](#project-architecture--directory-structure)
- [Installation & Setup](#installation--setup)
- [Running the Application](#running-the-application)
- [Automated Test Suite](#automated-test-suite)
- [API Reference](#api-reference)
- [User Roles & Workflow](#user-roles--workflow)
- [Future Scope](#future-scope)
- [Contributor](#contributor)
- [License](#license)

---

## Overview

Outcome-Based Education (OBE) requires every engineering course to demonstrate clear alignment between Course Outcomes (COs), Program Outcomes (POs), and Program Specific Outcomes (PSOs). Traditionally, faculty members manually create articulation matrices—a tedious, subjective process vulnerable to inconsistencies and audit queries.

The **Automated CO–PO & CO–PSO Mapping System** automates this process using a rigorous two-stage academic evaluation engine. It computes correlation values (`-`, `1`, `2`, `3`), provides pedagogical justifications citing Bloom's taxonomy and curricular competency, flags borderline cases for faculty review, and generates NBA-compliant Excel reports without modifying original reference documents.

---

## Problem Statement

Engineering accreditation bodies (NBA, ABET, Washington Accord) require verifiable proof that course curricula satisfy targeted graduate attributes. Common challenges include:
1. **Subjectivity & Inconsistency:** Different faculty members score identical competency alignments differently.
2. **False Positives from Generic Wording:** Naive keyword-matching engines falsely map unrelated outcomes simply because common words (e.g., "problems", "cost", "apply") appear in both statements.
3. **Audit Vulnerability:** Inability to provide clear, defensible pedagogical justification for why a specific cell is mapped to level 1, 2, or 3.
4. **Time Consumption:** Manually cross-referencing 6 COs against 12 POs and 2–4 PSOs across dozens of courses every semester.

---

## Objectives

- **Automate Mapping:** Determine correlation levels between CO statements and official PO/PSO descriptions using NLP and taxonomy rules.
- **Enforce Academic Relevance:** Use a two-stage evaluation methodology to eliminate superficial lexical overlap.
- **Provide Explainability:** Generate detailed rationale for every mapping decision to defend during accreditation visits.
- **Support Multi-Department & Multi-Course Scale:** Enable isolated management of department outcomes and course offerings.
- **Seamless Excel Integration:** Ingest syllabus workbooks directly and export audit-ready 4-sheet NBA articulation workbooks.

---

## Key Features

- **Two-Stage Academic Evaluation Engine:**
  - **Stage A (Academic Relevance Gate):** Filters out false lexical correlations (e.g., algorithmic cost vs. financial management) before scoring.
  - **Stage B (Multi-Factor Scoring):** Blends domain competency alignment (40%), Bloom's cognitive demand (25%), substantive phrase overlap (15%), and cosine semantic similarity (20%).
- **Standard NBA Mapping Scale:**
  - `-` : No Meaningful Relationship (0.0%)
  - `1` : Low Correlation (< 50.0%)
  - `2` : Moderate Correlation (50.0% – 80.0%)
  - `3` : High Correlation (> 80.0%)
- **Borderline / Teacher Review Flags:** Automatically alerts faculty when a cell falls near a threshold for expert verification.
- **Interactive Articulation Dashboard:** Real-time matrix view with dynamic column and row PO/PSO average calculation.
- **Excel Syllabus Parser:** Upload course workbooks (`.xlsx`, `.xlsm`) to auto-extract course metadata and CO statements.
- **Audit-Ready Excel Export:** Generates standalone workbooks featuring:
  1. *Course Details & COs*
  2. *12 CO-PO Mapping* (with live Excel `=AVERAGE()` formulas)
  3. *Mapping Justifications* (pedagogical rationale for every cell)
  4. *Department Outcomes* (POs, PSOs, Washington Accord Knowledge Profiles WK1–WK9)
- **Zero In-Place Mutation:** Preserves original institutional reference workbooks completely untouched.

---

## Methodology & Mapping Engine

The core algorithm in [`mapping_engine.py`](mapping_engine.py) operates in two distinct stages:

```
+-------------------------------------------------------------+
|                      CO & PO / PSO Input                    |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|            Stage A: Academic Relevance Gate                 |
|  - Domain Isolation (e.g., Mech thermal vs AI/DS)           |
|  - Academic Stopwords Filtering (strips filler verbs)       |
|  - Contextual Sense Validation (financial vs algorithmic)   |
+-------------------------------------------------------------+
             |                                 |
      [Not Relevant]                      [Relevant]
             |                                 |
             v                                 v
     Strictly '-' (0.0%)       +-------------------------------+
                               |  Stage B: Multi-Factor Score  |
                               |  - Domain Alignment (40%)     |
                               |  - Bloom's Demand (25%)       |
                               |  - Substantive Overlap (15%)  |
                               |  - TF-IDF Cosine Sim (20%)    |
                               +-------------------------------+
                                               |
                                               v
                                   Standard OBE Conversion
                                  [-], [1], [2], [3] + Reason
```

---

## Technology Stack

- **Backend:** Python 3.10+, Flask
- **Natural Language Processing & Scoring:**
  - `scikit-learn` (TF-IDF Vectorization, Cosine Similarity)
  - `rapidfuzz` (Token Set & Partial Phrase Ratio Matching)
- **Spreadsheet Processing:** `openpyxl` (Workbook parsing and multi-sheet styled export)
- **Frontend:** Semantic HTML5, Vanilla Modern CSS (Glassmorphic cards, responsive grid, status badges), Vanilla JavaScript (ES6+ async fetch, live calculations)
- **Data Persistence:** JSON-backed repository pattern (`data/departments_data.json`) seeded from institutional curriculum records (`for project.xlsx`)

---

## Project Architecture & Directory Structure

```
antigravityCO_PO_Mapping_System/
├── app.py                      # Flask application factory, REST endpoints, routes
├── mapping_engine.py           # Two-stage academic relevance & correlation engine
├── store.py                    # Department & course data persistence layer
├── excel_export.py             # Formatted 4-sheet NBA Excel export generator
├── test_app.py                 # Comprehensive unit & integration test suite
├── for project.xlsx            # Baseline ADCET curriculum reference workbook
├── requirements.txt            # Python package dependencies
├── .env.example                # Sample environment configuration template
├── .gitignore                  # Git exclusions for Python, caches, and backups
├── data/
│   └── departments_data.json   # Persistent department, PO/PSO, and course storage
├── templates/
│   └── index.html              # Interactive OBE articulation web interface
└── static/
    ├── css/
    │   └── style.css           # Modern, responsive design system & component styles
    └── js/
        └── app.js              # Matrix interactions, API bridge, modal management
```

---

## Installation & Setup

### Prerequisites
- Python 3.10 or higher installed on your system
- `git` version control

### 1. Clone the Repository
```bash
git clone https://github.com/Sakshi-Patil1/CO-PO-Mapping-System.git
cd CO-PO-Mapping-System
```

### 2. Create and Activate a Virtual Environment
- **Windows (Command Prompt / PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\activate
  ```
- **macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment (Optional)
Copy the example environment template:
```bash
copy .env.example .env     # On Windows
# cp .env.example .env     # On Linux / macOS
```

---

## Running the Application

Launch the Flask development server:
```bash
python app.py
```

The application will start locally at:
```
http://127.0.0.1:5000/
```

Open your browser and navigate to the URL to access the interactive dashboard.

---

## Automated Test Suite

A comprehensive test suite verifies threshold boundary conditions, academic gates, negative/superficial matches, persistence, and backward compatibility:

```bash
python test_app.py
```

### Test Coverage Highlights:
- **Threshold Boundaries:** Validates strict mapping boundaries (0%, <50%, 50%–80%, >80%).
- **Academic Relevance Gate:** Verifies negative cases (e.g., minimum cost graph algorithms mapping to PO10 finance are blocked).
- **Domain Isolation:** Confirms cross-department outcomes (e.g., Mechanical vs. AI/DS PSOs) do not leak.
- **REST Endpoints:** Tests department creation, course uploads, matrix saving, and workbook exports.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the interactive mapping dashboard |
| `GET` | `/api/departments` | Retrieves the list of all configured departments |
| `POST` | `/api/departments` | Registers a new academic department |
| `GET` | `/api/departments/<dept_id>` | Returns department metadata, POs, PSOs, and WKs |
| `GET` | `/api/departments/<dept_id>/courses/<course_id>` | Fetches course details, live matrix, and AI suggestions |
| `POST` | `/api/departments/<dept_id>/courses` | Adds a new course manually to a department |
| `POST` | `/api/departments/<dept_id>/courses/upload` | Ingests an Excel file to extract metadata and register a course |
| `POST` | `/api/departments/<dept_id>/courses/<course_id>/save` | Persists faculty edits to the articulation matrix |
| `POST` | `/api/departments/<dept_id>/courses/<course_id>/suggest` | Recomputes AI correlation suggestions with justifications |
| `POST` | `/api/departments/<dept_id>/courses/<course_id>/export` | Generates and downloads the 4-sheet NBA Excel workbook |
| `POST` | `/api/parse-course-excel` | Previews uploaded workbook metadata and COs without saving |

---

## User Roles & Workflow

1. **Course Coordinator / Faculty:**
   - Selects department and course from the dashboard.
   - Uploads course syllabus (`.xlsx`) or enters COs manually.
   - Inspects AI suggestions and pedagogical rationales by clicking any matrix cell.
   - Adjusts correlation levels where pedagogical expertise warrants.
   - Saves final mapping to the repository.
   - Exports the official NBA articulation workbook.
2. **Head of Department (HOD) / NBA Coordinator:**
   - Adds new departments, programs, and accreditation criteria (POs/PSOs/PEOs/WKs).
   - Audits course mappings across semesters to ensure curriculum compliance.

---

## Future Scope

- **Direct LMS Integration:** Direct sync with Moodle, Canvas, or Google Classroom for automated syllabus ingestion.
- **Attainment Calculation Module:** Automatic computation of direct/indirect course attainment from continuous internal evaluations (CIE) and semester end examinations (SEE).
- **Curriculum Gap Analysis:** Automated identification of unmapped POs across an entire 4-year degree curriculum.
- **Multi-Role Authentication:** Role-based access control (RBAC) with granular faculty and auditor permissions.

---

## Contributor

- **Sakshi Patil**
  - GitHub: [@Sakshi-Patil1](https://github.com/Sakshi-Patil1)
  - Project: Automated CO–PO & CO–PSO Mapping System

---

## License

This project is licensed under the [MIT License](LICENSE) — see the LICENSE file for details.
