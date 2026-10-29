# CityWatch AI - Setup and Workflow Guide

CityWatch AI is a local civic complaint application:

- **Frontend:** React + Vite
- **Backend:** FastAPI + Uvicorn
- **Complaint database:** MySQL Server 8.0
- **Database viewer:** MySQL Workbench 8.0
- **Video storage:** local files in `backend/uploads/`
- **AI model and training notebook:** `backend/models/` and `backend/notebooks/`

MySQL Workbench is the graphical client used to connect to MySQL Server. The backend connects to the local MySQL Server; it does not connect to Workbench itself.

## Project locations

```text
CityWatchAI/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── routes/
│   ├── data/                 # Legacy SQLite file, if present
│   ├── uploads/              # Uploaded videos and images
│   ├── models/               # Trained model
│   ├── notebooks/            # Model notebook
│   ├── requirements.txt
│   └── .env                  # Local MySQL credentials; do not commit
├── frontend/
│   ├── src/
│   └── package.json
└── read.md
```

## What happens when a complaint is submitted

1. Open the React site and choose **Report a Problem**.
2. Enter the complaint title, category, location, and description; attach one video and/or up to five images.
3. React sends the form to the FastAPI complaint API as multipart form data.
4. FastAPI validates the complaint and each evidence file, stores uniquely named files under `backend/uploads/evidence/`, and saves their metadata in MySQL.
5. For supported pothole/road damage, garbage/waste, and drainage reports, the API runs the bundled five-class Keras model and stores its actual predictions and confidence.
6. Confident predictions route `pothole`/`crack` to Roads & Public Works, `garbage` to Sanitation, and `manhole`/`poor_drainage` to Drainage. This routes to a department only; an authorized administrator still verifies the report and assigns an officer.
7. Unsupported categories (such as water supply), unavailable model/runtime, and low-confidence results stay unclassified and unrouted for human review. The API response includes the analysis result and routed department, where applicable.

Evidence is stored as files, not as binary data in MySQL. Complaint records persist across backend and computer restarts.

## 1. Prepare MySQL Server using Workbench

Ensure the local **MySQL Server 8.0** service is running. In Workbench, open your local MySQL connection and open a new SQL tab. Create a database and an application account. Replace the example password with a strong password of your choice; do not share it or commit it.

```sql
CREATE DATABASE IF NOT EXISTS citywatch_ai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'citywatch_app'@'127.0.0.1'
  IDENTIFIED BY 'replace-this-with-a-strong-password';

GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX
  ON citywatch_ai.*
  TO 'citywatch_app'@'127.0.0.1';

FLUSH PRIVILEGES;
```

Click the lightning-bolt **Execute** button. This creates the database and a restricted account for the backend. The backend creates the `complaints` table automatically at startup.

If you already created a MySQL account for the app, use its username/password in the next section instead. The account must be allowed to connect from the configured host and must have permission to create and access tables in `citywatch_ai`.

## 2. Configure the backend connection

Open PowerShell:

```powershell
cd C:\Users\Hp\OneDrive\Desktop\CityWatchAI\backend

if (-not (Test-Path .\.env)) {
    Copy-Item .\.env.example .\.env
}

notepad .\.env
```

In `.env`, set these values to match your local server and the account created above:

```dotenv
CITYWATCH_DB_HOST=127.0.0.1
CITYWATCH_DB_PORT=3306
CITYWATCH_DB_USER=citywatch_app
CITYWATCH_DB_PASSWORD=the-password-you-chose
CITYWATCH_DB_NAME=citywatch_ai
```

Save the file. Keep `.env` private; it is excluded from version control. The `.env.example` file is only a template and is not read as the active configuration.

## 3. Install dependencies and run the backend

Use the project-root `.venv` for the backend so the server and AI model use the same installed packages. Create it if it is missing:

```powershell
cd C:\Users\Hp\OneDrive\Desktop\CityWatchAI

if (-not (Test-Path .\.venv\Scripts\python.exe)) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --reload
```

Keep this terminal open. At startup, the backend connects to MySQL, creates the `complaints` table if needed, and checks for old SQLite records to import.

Backend URLs:

- API status: <http://127.0.0.1:8000/>
- Database health: <http://127.0.0.1:8000/api/health>
- Complaint list: <http://127.0.0.1:8000/api/complaints>
- Interactive API documentation: <http://127.0.0.1:8000/docs>

The health response should include `"database":"ready"` and `"database_name":"citywatch_ai"`.

The bundled model was saved with Keras 3.13.2. The requirements pin TensorFlow 2.20.0 and Keras 3.13.2; TensorFlow 2.15/Keras 2.15 cannot deserialize this model's Keras 3 input configuration. The model uses the notebook's 224×224 MobileNetV2 preprocessing and its verified class order: `crack`, `garbage`, `manhole`, `poor_drainage`, `pothole`. The automatic-routing confidence threshold defaults to `0.40` (40%) and can be changed with `CITYWATCH_AI_CONFIDENCE_THRESHOLD`; the model path can be changed with `CITYWATCH_ROAD_MODEL_PATH`. Categories outside those model-supported issues, such as water supply, remain for human review.

Administrators and officers can approve a pending report from its **View** page by selecting an active department and choosing **Approve & assign department**. This approves the complaint and sets its department. AI-routed reports awaiting approval appear in the selected department's **Assigned Complaints** queue rather than **New Complaints**; after approval they leave that queue and appear in **Pending Complaints**. If the model prediction maps to a different department than the citizen-selected report category, automatic routing is skipped and the report stays in **New Complaints** for manual review. An administrator can then assign an individual officer from the complaint details.

The citizen report form requires the issue location (street, area, ward, or landmark); citizens can optionally use the browser's **Use my current location** permission prompt to save GPS coordinates with the report. The address/landmark and coordinates are stored on the complaint and displayed in its details.

## 4. Run the frontend

Open a second PowerShell window:

```powershell
cd C:\Users\Hp\OneDrive\Desktop\CityWatchAI\frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173/> in your browser.

## Demo login accounts

Choose **Log in / Sign up** in the top navigation to open the demo login page. The sample accounts are:

| Role | Account ID | Password |
| --- | --- | --- |
| Citizen | `CW-CIT-1001` | `Citizen@123` |
| Officer | `CW-OFF-2001` | `Officer@123` |
| Administrator | `CW-ADM-3001` | `Admin@123` |

Selecting a sample account fills its credentials. The backend creates these demo accounts in MySQL on first startup. Passwords are stored as PBKDF2 hashes; successful login returns a signed bearer token, and the API checks the user's active MySQL role on protected routes. These are public test credentials, not production accounts; do not use them with private or sensitive data.

The seeded officer records are assigned to real department rows in MySQL:

| Officer ID | Department |
| --- | --- |
| `CW-OFF-2001` | Roads & Public Works |
| `CW-OFF-2002` | Sanitation Department |
| `CW-OFF-2003` | Drainage Department |
| `CW-OFF-2004` | Electrical Maintenance Department |
| `CW-OFF-2005` | Water Supply Department |
| `CW-OFF-2006` | Traffic Department |

All seeded officer test accounts use `Officer@123`. Admin can also sign in with `CW-ADM-3001` / `Admin@123`.

## Complaint verification, assignment, and officer work

1. Sign in as the administrator, open **All Complaints**, and open a pending-review report.
2. Choose **Verify complaint**. Only verified complaints can be assigned.
3. Click **Assign Officer**. Departments and active officers are loaded from MySQL. The department is suggested from the complaint category; select an eligible officer, set priority and optional due date/instructions, then confirm.
4. Assignment, status change, history entry, and officer notification are saved together in MySQL. Reassignment creates a new current assignment while retaining the previous assignment and requires a reason.
5. Sign out and sign in as the assigned officer. The case appears in **Assigned Complaints**; officers can start work or mark it resolved through the valid status transitions.

`GET /api/complaints/{id}/video` and `GET /api/complaints/{id}/evidence/{evidence_id}` stream local evidence after checking the logged-in user's access. Complaint details load evidence with the session token; the raw local filesystem path is never sent as the file URL.

## 5. Use and verify the complaint flow

1. Confirm the backend is running and `/api/health` reports the database as ready.
2. Confirm the frontend is running at `http://127.0.0.1:5173/`.
3. Submit a complaint from **Report a Problem**.
4. Confirm the new complaint appears in the citizen's complaint list/dashboard.
5. Confirm the row is present in Workbench using the instructions below.
6. If a video was attached, confirm a corresponding file exists in `backend/uploads/`.
7. Restart the backend and reload the app; the complaint should still appear.

The complaint API accepts form fields including `title`, `category`, `location`, and `description`. Videos are limited to 50 MB by default (configurable with `CITYWATCH_MAX_VIDEO_SIZE_MB`); images are limited to 10 MB each, with up to five images. Accepted formats are MP4, MOV, AVI, MKV, WEBM, JPEG, PNG, WebP, and GIF.

## 6. View complaint data in MySQL Workbench

1. Open MySQL Workbench and connect to your local MySQL Server.
2. In the **SCHEMAS** panel, refresh the schema list if necessary.
3. Expand `citywatch_ai`, then **Tables**.
4. Right-click `complaints` and choose **Select Rows - Limit 1000** to browse records.
5. Or open a SQL tab and run any of these queries:

```sql
SELECT *
FROM citywatch_ai.complaints
ORDER BY created_at DESC;
```

```sql
SELECT status, COUNT(*) AS total
FROM citywatch_ai.complaints
GROUP BY status;
```

```sql
SELECT category, COUNT(*) AS total
FROM citywatch_ai.complaints
GROUP BY category;
```

Useful fields include the complaint ID, category, location, status, priority, timestamps, video filename, and relative video path. Evidence metadata is in `evidence_files`, and actual files remain in the local uploads directory. AI predictions and routing outcomes are in `ai_analyses` and `complaint_history`.

## 7. Existing SQLite records

If `backend/data/citywatch.db` from the earlier setup exists and contains a `complaints` table, the backend imports those complaint rows into MySQL at startup. It uses the complaint ID to avoid duplicate inserts on later restarts. The SQLite file and its uploaded videos are left in place as a backup; they are not deleted by this migration.

New complaint records are written to MySQL. MySQL becomes the source used by the complaint list and detail endpoints.

## 8. Database schema

The backend creates and incrementally extends its MySQL schema automatically without deleting existing complaint data. In addition to `complaints`, it creates `users`, `departments`, `evidence_files`, `ai_analyses`, `assignments`, `complaint_history`, and `notifications` tables. Its complaint columns include:

- `id` — complaint identifier and primary key
- `title`, `category`, `location`, `description`
- `latitude`, `longitude` — optional coordinates
- `video_name`, `video_path` — local upload metadata
- `priority`, `status`
- `created_by_user_id`, `assigned_department_id`, `assigned_officer_id`, `due_date`, and `assignment_instructions`
- `created_at`, `updated_at`

The table uses InnoDB and `utf8mb4`, with indexes for creation time and status.

## 9. Troubleshooting

### Backend reports MySQL as unavailable or cannot start

- Check that the **MySQL80** Windows service is running (open Windows Services and start it if stopped).
- In Workbench, test the local server connection.
- Confirm that the host, port, database name, username, and password in `backend\.env` match your server/account.
- Confirm the `citywatch_ai` schema exists and the backend account has table privileges.
- Check the backend terminal for the connection error. Do not paste passwords or other credentials into chat.

### Access denied for user

The MySQL user may have been created for a different host. Create/grant the account for the configured host in Workbench, or adjust `CITYWATCH_DB_HOST` and the MySQL account host so they match.

### Frontend cannot reach the backend

Make sure Uvicorn is running on port 8000 and the frontend is running on port 5173. Visit `http://127.0.0.1:8000/api/health` directly to check the backend/database.

### Complaint submission fails

Check the backend terminal response, required text fields, video file format/size, and MySQL connection. The API does not expose database credentials in its error responses.

### Port is already in use

Stop the existing process that owns port 8000, or run Uvicorn on a different port and update the frontend API configuration accordingly.

## 10. Data and security notes

- Do not commit `backend/.env`, MySQL passwords, the generated SQLite backup, or uploaded videos.
- MySQL stores complaint metadata only; uploaded videos remain local.
- Back up the `citywatch_ai` schema/data and `backend/uploads/` separately.
- This local application does not configure MySQL for remote access. Keep the server bound to localhost unless you intentionally secure and configure remote access.
- Complaint, authentication, assignment, dashboard, notification, and local video routes use MySQL. Optional AI-analysis and Supabase Storage routes still depend on their existing Supabase configuration.
