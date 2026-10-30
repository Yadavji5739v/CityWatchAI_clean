# CityWatch AI — Project Summary

**Last updated:** 20 October 2026  
**Workspace:** `CityWatchAI`

This document summarizes the project as it currently exists, the work completed in this session, how the main workflows fit together, and the checks and limitations verified so far. It distinguishes implemented behavior from features that still need a working runtime or additional integration.

## 1. Project at a glance

CityWatch AI is a civic complaint reporting and case-management application. Citizens submit a complaint with location and optional photo/video evidence. The backend stores the complaint and evidence, attempts AI classification for supported issue categories, and can route a confident classification to a department. An authorized administrator remains responsible for verifying a complaint and assigning an officer. Officers can view their assignments and update work progress.

The implemented application stack is:

- **Frontend:** React, JavaScript/JSX, Vite, React Router, Lucide icons.
- **Backend:** Python, FastAPI, Uvicorn.
- **Primary application database:** Supabase PostgreSQL, using the isolated `citywatch` schema created by the backend at startup.
- **Evidence storage:** Local files under `backend/uploads/`; PostgreSQL stores their metadata and relative paths.
- **AI model artifacts:** Keras `.keras` files in `backend/models/`, with training and class-order information in `backend/notebooks/ab.ipynb`.

`workflow.md` contains a broader desired product specification, including a Node/Express stack. That specification is not the implementation: the running backend in this workspace is FastAPI, not Express.

## 2. Application areas and pages

The React application in `frontend/src/` has a public site and role-specific workspaces:

- **Public pages:** Home/landing page, How It Works, and Login.
- **Citizen pages:** Dashboard, Report a Problem, My Complaints, and Complaint Details.
- **Officer pages:** Officer dashboard, new/pending complaint lists, assigned complaints, and solved/work-history views.
- **Administrator pages:** Admin dashboard, all complaints, verification, and officer assignment workflows.

Role-protected routes and the main application shell are wired in `frontend/src/App.jsx`. Shared interface components live in `frontend/src/components/`; page implementations live in `frontend/src/pages/`. The interface uses a responsive sidebar, civic dashboard cards, complaint tables, status badges, detail views, and an assignment dialog.

## 3. Citizen submission and evidence workflow

The reporting form in `frontend/src/pages/SubmitComplaint.jsx` collects:

- Complaint title, selected category, location, description, and optional latitude/longitude.
- Up to one video (50 MB) and five images (10 MB each).
- Local previews and file removal before submission.

The form submits multipart data to `POST /api/complaints`. The backend route in `backend/routes/complaints.py` validates the file extensions, MIME types, counts, and sizes; generates unique server-side filenames; stores evidence below `backend/uploads/evidence/`; and writes the evidence metadata to Supabase PostgreSQL. The submitted evidence is analyzed during complaint creation where the selected category is supported.

Complaint details fetch persisted data from the server. Evidence is streamed through authenticated endpoints, rather than exposing local disk paths:

- `GET /api/complaints/{complaint_id}/video`
- `GET /api/complaints/{complaint_id}/evidence/{evidence_id}`

Complaint ownership and role checks are performed on the backend. The frontend displays the returned evidence and AI result in `frontend/src/pages/ComplaintDetails.jsx`.

## 4. AI model and department routing

The notebook documents a five-output model and its class-index order:

1. `crack`
2. `garbage`
3. `manhole`
4. `poor_drainage`
5. `pothole`

That model is `backend/models/road_damage_5class_model.keras`. The classifier adapter is `backend/services/civic_classifier.py`. It is configured for 224×224 RGB images with MobileNetV2 preprocessing (`pixel / 127.5 - 1`), extracts sampled frames for videos, averages predictions across frames, and requires a confidence of at least `0.40` (40%) before treating a result as an automatic department-routing suggestion.

Current intended mapping:

| Model class | Suggested department |
|---|---|
| `crack` | Roads & Public Works |
| `pothole` | Roads & Public Works |
| `garbage` | Sanitation Department |
| `manhole` | Drainage Department |
| `poor_drainage` | Drainage Department |

Routing rules and compatibility aliases are in `backend/services/routing_service.py`. A department suggestion does **not** assign an officer or verify the complaint. That remains an administrator action.

The classifier does not invent predictions for unsupported categories. For example, water-supply reports stay unclassified for human review. Missing/unavailable model runtime, unreadable evidence, and low-confidence output also produce a review state rather than a fabricated class. If the model and the citizen-selected category map to different departments, automatic routing is skipped and staff review is required.

The submission route records the result in `ai_analyses`, associates a confident department recommendation with the complaint, and writes a routing history entry. Details responses include the latest saved AI summary and status.

### AI runtime compatibility

The `.keras` archive records `keras_version: 3.13.2` and its model configuration contains Keras 3 fields. The earlier TensorFlow 2.15.1/Keras 2.15 runtime failed to deserialize the model. The running API uses the project-root `.venv312`; `backend/venv` is a separate environment and is not the environment used for the verified model load.

The dependency pin and setup guide are aligned to TensorFlow 2.20.0 and Keras 3.13.2. The verified API environment is the project-root `.venv312`; `backend/venv` is a separate environment and should not be assumed to contain the active dependencies. The compatible TensorFlow/Keras versions were installed in the project-root environment, and the bundled model was loaded and run against a temporary synthetic image. This verifies runtime compatibility and inference execution only; it does not establish prediction accuracy on real civic evidence. The model has not been retrained or calibrated on a new labeled dataset.

## 5. Backend API and lifecycle

The FastAPI application is assembled in `backend/main.py`. It registers complaint, evidence, assignment, AI, dashboard, and authentication routers, enables local Vite CORS origins, initializes the Supabase PostgreSQL `citywatch` schema, and seeds local demo accounts on startup.

Implemented local-application route groups include:

- **Health:** `GET /api/health`
- **Authentication:** `/api/auth/login`, `/api/auth/me`
- **Complaints:** list, citizen list, details, create, verify, and evidence streaming under `/api/complaints`
- **Assignments:** departments, eligible officers, active assignments, assignment, and progress under `/api`
- **Notifications:** `/api/notifications`
- **Dashboards:** citizen, officer, and administrator dashboards under `/api/dashboard`

The intended case workflow is: submission → confidently classified reports that match the citizen-selected department appear in that department's Assigned Complaints review queue; unrouted, unsupported, low-confidence, or department-conflicting reports appear in New Complaints → administrator/officer approval with department selection → `Verified` complaints appear in Pending Complaints for the selected department → administrator may assign a specific officer → officer progress updates and resolution. Approval accepts both `Submitted` and `Pending Review` complaint statuses. Review and department selection are restricted to administrators and officers; the backend verifies the selected department is active and records the action in complaint history. The officer approving a complaint will not see it in their own Pending queue when they selected a different department.

Assigned Complaints is a department-level review queue for eligible AI-routed complaints plus individual assignments for the logged-in officer. Once an AI-routed complaint is approved, it leaves Assigned Complaints and enters the selected department's Pending queue. The AI-routed queue uses the latest analysis record and requires its status to be `completed`; historical records with unavailable, failed, review-required, unsupported, or conflicting analyses are not automatically listed there.

## 6. Database and authentication

`backend/database.py` connects to Supabase PostgreSQL using `SUPABASE_DB_HOST`, `SUPABASE_DB_PORT`, `SUPABASE_DB_NAME`, `SUPABASE_DB_USER`, and `SUPABASE_DB_PASSWORD`. It creates application tables in a separate `citywatch` schema, leaving the Supabase `public` schema and Auth tables untouched. At startup it creates tables when missing, adds selected complaint columns when needed, and can import older SQLite complaint rows without deleting the SQLite source.

Tables created by the local database initializer include:

- `complaints`
- `departments`
- `users`
- `evidence_files`
- `ai_analyses`
- `assignments`
- `complaint_history`
- `notifications`

The local demo authentication implementation is in `backend/services/local_auth.py`. It hashes passwords using PBKDF2-HMAC-SHA256 and issues signed, expiring bearer tokens. The backend looks up the current user and role in PostgreSQL on protected requests. Demo identities and departments are seeded without replacing existing rows.

The setup and local-run guide is `read.md`. It explains Supabase PostgreSQL connection settings, backend environment values, frontend/backend startup, and demo login accounts. Keep actual credentials in `backend/.env`; do not commit them.

## 7. Work completed in this project conversation

The citizen-to-classification-to-department workflow was extended across these files:

- `backend/services/civic_classifier.py` — added the Keras inference adapter, five-class labels, image/video preprocessing, confidence handling, and explicit unavailable/failed/review states.
- `backend/services/routing_service.py` — added routing for supported model classes and aliases for seeded department names.
- `backend/services/routing_service.py` and `backend/routes/complaints.py` — compare the citizen-selected category's department with the model prediction's department; mismatches skip auto-routing and remain in the staff New Complaints review queue.
- `backend/routes/complaints.py` — wired evidence storage, classification during submission, AI-analysis persistence, confident department routing, history logging, protected file streaming, and AI/evidence fields in complaint responses.
- `backend/routes/complaints.py` and `backend/routes/assignments.py` — allow administrators and officers to approve `Submitted` or `Pending Review` complaints with an active department selection; the backend rejects complaints in other states.
- `backend/routes/assignments.py` — includes AI-completed, department-routed pending complaints in that department's officer review queue; queue filtering normalizes status values and uses the latest AI analysis, and approval removes the item from this queue.
- `backend/routes/complaints.py` — scopes officer complaint listings to unrouted reviews, their department's routed reviews/approved cases, and cases assigned directly to them.
- `frontend/src/pages/OfficerComplaints.jsx` and `frontend/src/App.jsx` — keep AI-routed reports out of New Complaints and include approved (`Verified`) cases in Pending Complaints. Status values returned by the API are normalized consistently before queue filtering.
- `frontend/src/pages/ComplaintDetails.jsx` — after approval, confirms the selected department and that the complaint should appear in that department's Pending Complaints queue.
- `frontend/src/pages/AssignedComplaints.jsx` — clarifies that this is a department review/individual assignment queue and that approved cases move to Pending Complaints.
- `backend/routes/complaints.py` and `frontend/src/pages/SubmitComplaint.jsx` — require a human-readable issue location and optionally capture browser GPS coordinates; coordinates are validated and persisted alongside the location text.
- `frontend/src/pages/ComplaintDetails.jsx` and `frontend/src/pages/AssignedComplaints.jsx` — display saved GPS coordinates and clarify when a complaint is waiting in its department queue for an officer assignment.
- `backend/database.py` — added startup creation of evidence metadata and AI-analysis tables.
- `backend/requirements.txt` — pins TensorFlow 2.20.0 and Keras 3.13.2 to match the bundled model's Keras serialization format.
- `frontend/src/pages/SubmitComplaint.jsx` — added optional image evidence alongside video, client previews, limits, and submission of the selected files.
- `frontend/src/pages/ComplaintDetails.jsx` — added server detail loading, protected image/video display, and an AI classification section.
- `frontend/src/pages/ComplaintDetails.jsx` — adds a department selector and “Approve & assign department” action for pending complaints opened from the officer or administrator workspace.
- `frontend/src/pages/ComplaintDetails.jsx` — corrected malformed bearer-token headers on the complaint, department, and image-evidence requests; this was causing 401 responses, an empty department dropdown, and evidence-access errors.
- `frontend/src/components/AssignOfficerModal.jsx` — prefers the department returned by AI routing when suggesting an assignment department.
- `frontend/src/index.css` — added evidence image preview styling.
- `backend/tests/test_civic_classifier.py` — added focused tests for class results, low confidence, unsupported categories, and department mapping.
- `backend/tests/test_civic_classifier.py` — tests department disagreement handling so a conflicting prediction cannot automatically route to another department.
- `backend/tests/test_complaint_review.py` — covers officer approval for `Submitted` and `Pending Review`, rejects repeat approval after verification, validates queue query behavior, and checks citizen authorization denial.
- `read.md` — documented the submission, AI, routing, model classes, and upload limits.

## 8. Validation completed

The following checks passed during the implementation:

- Focused classifier and routing tests were run with mocked model outputs. These validate the inference adapter's mapping/handling and routing logic, not the real model's predictive accuracy.
- Focused complaint review and classifier test suites: **14 passed** after the latest approval and queue fixes.
- Frontend production build: `npm run build` completed successfully.
- Frontend lint: `npm run lint` completed successfully.
- Python syntax and editor diagnostics for the changed backend code were checked; no syntax errors or new route diagnostics were reported.
- The `.keras` archive was inspected without loading TensorFlow: it contains a Keras configuration and weights archive, and the final dense layer has five outputs, matching the class map.

The live MySQL health endpoint returned healthy after the queue fixes. A browser check confirmed that an approved Roads complaint appeared in Pending Complaints for a Roads officer. The current live database showed no complaints with a latest `completed` AI analysis, so the AI-routed Assigned queue contained no rows during that check; existing reports in unavailable or review-required states are correctly not treated as completed AI routes. Earlier live inference produced a high-confidence disagreement (a citizen report labeled Pothole was classified as Garbage), which led to the department-conflict safeguard. This demonstrates why runtime compatibility and a confident output do not guarantee classifier accuracy. A full new citizen upload through the browser was not performed as part of the latest queue fixes.

## 9. End-to-end verification completed

The full citizen complaint and officer assignment lifecycle was tested end-to-end against the running backend and MySQL database:

1. **Citizen complaint submission:** Citizen account (`CW-CIT-1001`) logged in and submitted a new complaint with image evidence (`CW-20261020065655-1EAC04`).
2. **AI analysis & routing safeguard:** The 5-class Keras model processed the evidence in ~394ms. Because the synthetic image was classified as `garbage` (Sanitation) while the citizen reported `Pothole` (Roads), the department conflict safeguard correctly marked `analysis_status: 'review_required'` and preserved the report for human review without misrouting.
3. **Admin review and verification:** Admin (`CW-ADM-3001`) verified the complaint, explicitly routing it to Roads & Public Works. Status changed from `Pending Review` to `Verified`.
4. **Officer assignment:** Admin assigned the complaint to the active Roads Officer (`CW-OFF-2001`).
5. **Officer progression:** The Roads Officer logged in, retrieved the assignment, moved the complaint to `In Progress`, and subsequently moved it to `Resolved`. The entire lifecycle (`Pending Review` → `Verified` → `Assigned` → `In Progress` → `Resolved`) succeeded with status updates persisted in MySQL.

## 10. Known limitations

- **AI accuracy is unverified on representative labeled evidence.** Runtime compatibility and inference execution are verified, but model accuracy has not been measured using a representative labeled set of real civic photos/videos. The department-conflict safeguard prevents model/category disagreements from auto-routing, but does not improve underlying model accuracy.
- **Mixed storage integrations remain.** Main complaint submission, MySQL, and local evidence storage are separate from Supabase-related behavior in `backend/routes/ai.py`, `backend/routes/evidence.py`, and `backend/database/schema.sql`.
- **Citizen self-registration is not implemented or verified.** Demo accounts are seeded by the backend. Public officer/administrator registration is not part of the current design. Registration and broader features in `workflow.md` need product confirmation before being considered in scope or complete.

## 11. Known integration notes

1. **Use the verified Python environment.** Install `backend/requirements.txt` into the project-root `.venv`, matching the API environment used for model verification. Restart the FastAPI process after changing dependencies or backend code if auto-reload is not active.
2. **Old analysis results are persisted.** A complaint created while the model runtime was unavailable keeps that saved result. This workflow does not automatically rerun inference for historical reports; submit a new supported-category complaint with evidence to generate a fresh analysis.
3. **Check uploads and login when evidence cannot display.** Evidence is protected by bearer-token authentication. A “Sign in to access this resource” response means the file request did not have a valid session. A “No video evidence attached” message means that complaint response has no video path; it may still have image evidence, which is listed separately.
4. **AI category coverage is limited to five model classes.** Water supply, street lights, parking, and other unsupported categories do not receive model predictions. The model output is decision support, not proof that a complaint is valid.
5. **The app is not the full target described in `workflow.md`.** The actual backend is Python/FastAPI and local MySQL; a Node/Express backend and several broader target features are not established by this implementation summary.

## 12. Local run commands

Start the backend from the project root in one PowerShell terminal:

```powershell
cd C:\Users\Hp\OneDrive\Desktop\CityWatchAI
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --reload
```

Start the frontend in another terminal:

```powershell
cd C:\Users\Hp\OneDrive\Desktop\CityWatchAI\frontend
npm install
npm run dev
```

Frontend default: <http://127.0.0.1:5173/>  
Backend API docs: <http://127.0.0.1:8000/docs>  
Backend health: <http://127.0.0.1:8000/api/health>

Install backend dependencies into the project-root environment, then verify the runtime:

```powershell
cd C:\Users\Hp\OneDrive\Desktop\CityWatchAI
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -c "import tensorflow as tf, keras; print(tf.__version__, keras.__version__)"
```
