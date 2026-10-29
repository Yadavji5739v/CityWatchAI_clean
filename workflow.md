make a professional new ui  u can also add or remove any webpages which will better # CityWatch AI — Complete Full-Stack Development Master Prompt

Act as a senior full-stack developer, AI integration engineer, database architect, and professional UI/UX designer. Build a complete, professional, responsive, and functional civic complaint management platform named **CityWatch AI**.

## 1. Project Objective

CityWatch AI allows citizens to report civic problems by uploading video evidence and providing location details. The system stores complaints, analyzes supported evidence using my existing trained AI model, assists authorized officials with prioritization, and tracks complaints through verification, assignment, resolution, and final review.

**Tagline:** “Smarter Cities. Faster Solutions.”

**Landing-page headline:** “Your City. Your Voice. Real Change.”

Do not claim partnerships with government agencies unless officially provided.

## 2. Mandatory Technology Stack

Use the following technologies:

**Frontend**
- React with Vite, JavaScript and JSX.
- React Router for navigation.
- Tailwind CSS and shadcn/ui where compatible.
- Lucide React for icons.
- Axios or Fetch for API requests.
- Recharts for analytics.
- React Leaflet with OpenStreetMap for complaint locations.
- Responsive design for desktop, tablet, and mobile.

**Backend**
- Node.js and Express.js using JavaScript ES modules.
- `mysql2` for MySQL database access.
- `dotenv` for environment configuration.
- Multer for video and image uploads.
- Zod or equivalent validation.
- Helmet, CORS configuration, and rate limiting.
- Secure authentication using JWT or secure sessions.
- Centralized error handling and structured logging.

**Database**
- Local MySQL Server.
- Database name: `citywatch_db`.
- Manage and inspect the database through MySQL Workbench 8.0.
- Use foreign keys, indexes, transactions, and parameterized SQL queries.

**Important restrictions:** Do not use FastAPI, Flask, SQLite, MongoDB, or Supabase as the primary backend/database. Do not rewrite the project in Python. Keep React and Node.js/Express as the main application stack.

MySQL Workbench is a database management tool; ensure the actual MySQL Server is installed and running before attempting database connections. Never assume my MySQL password or credentials.

## 3. Integrate My Existing Trained AI Model

I already have a trained AI model. **Reuse my existing model. Do not train a new model, replace mine, or fabricate predictions.**

First inspect the actual model files, model framework, file format, input dimensions, supported classes, preprocessing, postprocessing, inference code, and output structure.

Implement a modular backend AI service that:
1. Accepts an uploaded complaint video or supported extracted frames.
2. Validates and preprocesses the input according to the model's actual requirements.
3. Runs real inference using my existing trained model.
4. Returns supported detections, class labels, confidence scores, timestamps or bounding boxes when applicable, and processing status.
5. Stores analysis results in MySQL.
6. Displays genuine analysis results in the React dashboard.
7. Handles unsupported formats, invalid files, inference errors, and unavailable model files gracefully.

Do not invent model labels, confidence scores, or results. Do not automatically declare a complaint genuine or fraudulent based only on model predictions. AI should assist authorized human reviewers, not replace them.

**Model compatibility requirement:** Keep Node.js/Express as the main backend. If the model is compatible with ONNX Runtime for Node.js, TensorFlow.js, or another suitable JavaScript runtime, use that approach where technically supported. If the model requires Python or unsupported operators, explain the limitation and provide the smallest reliable integration option before introducing any Python inference service. Do not silently add a Python backend or pretend an incompatible model runs in Node.js. Make model integration configurable so the application can operate in a clearly labeled AI-unavailable mode until the real model is connected.

Create a documented model integration directory, inference adapter, configuration, and test instructions. Do not commit model secrets or unnecessarily large model files to Git.

## 4. Professional UI/UX Design

Create a premium, trustworthy civic-tech SaaS interface.

Visual direction:
- Dark navy sidebar.
- Electric-blue primary accent.
- Teal highlights.
- White and light-slate backgrounds.
- Clean typography, generous spacing, subtle shadows, rounded cards, and consistent icons.
- Professional charts, tables, filters, search, pagination, status badges, dialogs, toast notifications, and loading skeletons.
- Accessible color contrast and keyboard navigation.
- Mobile-friendly navigation and responsive layouts.
- Realistic demo data only when clearly identified as sample data.

Avoid clutter, excessive gradients, oversized cards, and generic unfinished templates.

## 5. Required Pages

### Public website
- Landing page.
- How It Works.
- Civic Issues / Supported Categories.
- Impact and Analytics overview.
- Sign In.
- Register.

### Citizen portal
- Citizen dashboard with complaint statistics and recent activity.
- Report a Complaint.
- My Complaints.
- Complaint Details and Timeline.
- Notifications.
- Profile and Account Settings.

### Officer portal
- Officer dashboard.
- Assigned Complaints.
- Complaint Review.
- Update Progress.
- Upload Resolution Evidence.
- Work History.

### Administrator portal
- Admin dashboard.
- All Complaints.
- Verification Queue.
- Departments Management.
- Officers Management.
- Complaint Assignment and Routing.
- Analytics and Reports.
- Audit History.
- System Settings.

Implement role-based navigation and protect restricted routes. A user must not gain administrator or officer privileges simply by changing frontend data.

## 6. Complaint Reporting Form

Create a complete form with:
- Complaint title.
- Detailed description.
- Civic category: pothole, garbage, drainage, streetlight, water supply, road obstruction, illegal parking, or other supported categories.
- Address and locality.
- GPS coordinates when available and permission is granted.
- Video evidence upload.
- Optional supporting images.
- Upload progress and file preview.
- Validation, success messages, and clear error messages.
- Generated complaint reference number.

Validate uploads on the server. Configure a reasonable video size limit, initially 50 MB, and allow supported formats only. Store uploaded files on the local filesystem, not as database BLOBs.

Use separate storage directories such as:
- `backend/uploads/complaint-videos/`
- `backend/uploads/supporting-images/`
- `backend/uploads/resolution-evidence/`

Store file paths, MIME types, sizes, ownership, and metadata in MySQL. Prevent path traversal and unsafe file access. Do not execute uploaded files. Configure retention and access controls appropriately.

## 7. Complaint Lifecycle

Implement the following workflow:

`Submitted → AI Analysis → Pending Review → Verified → Assigned → In Progress → Resolved → Final Review → Closed`

Also support:
- `Needs Information`
- `Rejected`
- `Reopened`

Rules:
- Citizens submit complaints and view their own complaint history.
- AI analyzes evidence only for supported classes and records actual results.
- Authorized reviewers manually verify or reject complaints with a reason.
- Verified complaints are assigned to an appropriate department and officer.
- Officers add progress notes and upload resolution evidence.
- Authorized reviewers inspect the evidence before final closure.
- Citizens can see progress and request reopening where permitted.
- Every meaningful status change is recorded with actor, timestamp, and optional notes.
- Enforce valid status transitions on the backend, not only in the frontend.

## 8. MySQL Database Design

Create a database schema and SQL migration files for these tables:

1. `users` — user identity, hashed password, role, contact details, and timestamps.
2. `departments` — department details and supported complaint categories.
3. `complaints` — complaint reference, title, description, category, location, coordinates, status, priority, creator, and timestamps.
4. `evidence_files` — original complaint videos, supporting images, and resolution evidence metadata.
5. `ai_analyses` — model version, processing status, actual predictions, confidence values, timestamps, and error information where appropriate.
6. `assignments` — complaint, department, assigned officer, assignment time, and assignment status.
7. `complaint_history` — status changes, actors, notes, and timestamps.
8. `resolution_records` — resolution notes, evidence references, reviewer decisions, and closure details.
9. `notifications` — recipient, message, read status, related complaint, and timestamp.

Use appropriate data types, foreign keys, unique constraints, indexes, and transactional updates. Hash passwords with a suitable password-hashing library. Use parameterized queries exclusively.

Provide an initial SQL migration file that creates the database tables and indexes. Do not automatically delete or overwrite existing data during startup.

## 9. Backend API

Create documented REST APIs, including:

- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout` where applicable
- `GET /api/auth/me`
- `POST /api/complaints`
- `GET /api/complaints`
- `GET /api/complaints/:id`
- `PATCH /api/complaints/:id`
- `POST /api/complaints/:id/evidence`
- `GET /api/complaints/:id/analysis`
- `POST /api/complaints/:id/analyze`
- `POST /api/complaints/:id/verify`
- `POST /api/complaints/:id/assign`
- `POST /api/complaints/:id/progress`
- `POST /api/complaints/:id/resolve`
- `POST /api/complaints/:id/final-review`
- `POST /api/complaints/:id/reopen`
- `GET /api/dashboard/stats`
- `GET /api/notifications`

Add appropriate department, officer, administration, and analytics endpoints as needed.

Implement authentication, role-based authorization, ownership checks, input validation, pagination, filtering, secure upload handling, and consistent JSON responses. Never expose database passwords, JWT secrets, internal stack traces, or unrestricted server filesystem paths.

## 10. Project Structure

Organize the project cleanly, for example:

`frontend/`
- `src/components/`
- `src/pages/`
- `src/layouts/`
- `src/services/`
- `src/hooks/`
- `src/context/`
- `src/utils/`

`backend/`
- `src/config/`
- `src/routes/`
- `src/controllers/`
- `src/services/`
- `src/middleware/`
- `src/validators/`
- `src/utils/`
- `src/database/`
- `uploads/`
- `migrations/`
- `tests/`

Include `README.md`, `.env.example`, `.gitignore`, API documentation, database setup instructions, and model integration documentation. Keep frontend and backend independently runnable.

## 11. Environment Configuration

Backend `.env.example`:

`PORT=8000`
`NODE_ENV=development`
`FRONTEND_URL=http://localhost:5173`
`DB_HOST=127.0.0.1`
`DB_PORT=3306`
`DB_NAME=citywatch_db`
`DB_USER=your_mysql_username`
`DB_PASSWORD=your_mysql_password`
`JWT_SECRET=replace_with_a_secure_random_secret`
`UPLOAD_DIR=./uploads`
`MAX_VIDEO_SIZE_MB=50`

Frontend `.env.example`:

`VITE_API_BASE_URL=http://localhost:8000/api`

Load credentials from environment variables. Never hardcode real passwords or secrets. Never place backend secrets in frontend environment variables. Add `.env` and uploaded private evidence to `.gitignore` as appropriate.

## 12. React–Backend Integration

Connect every relevant page to the real Express APIs. Replace mock-only interactions with working API requests wherever the corresponding backend feature exists.

Implement:
- API client with centralized base URL.
- Authentication state and protected routes.
- Upload progress.
- Loading, empty, success, and error states.
- Complaint filtering and pagination.
- Dashboard metrics derived from database records.
- Real-time-looking status timelines based on persisted history.
- Clear handling of API unavailability.

The React application must continue using `http://localhost:5173` and the Express API must run on `http://localhost:8000` during local development, unless configuration is changed.

A hosted Lovable preview cannot automatically access my local MySQL database. Document how to run the application locally or configure a properly secured, reachable backend for hosted deployment. Never expose the local database directly to the public internet.

## 13. Security and Reliability

Implement:
- Password hashing.
- Role-based authorization and server-side ownership validation.
- Secure CORS configuration.
- Request validation and rate limiting.
- Parameterized SQL.
- Safe upload names and file type/size checks.
- Private evidence access controls.
- Audit history for important actions.
- Transactional complaint status changes and assignments.
- Safe error handling.
- Environment-based configuration.
- Tests for authentication, authorization, complaints, uploads, database access, and lifecycle transitions.

Do not fabricate successful uploads, database records, AI results, or status updates when the operation fails.

## 14. Development and Delivery Plan

Work in these phases while preserving one coherent project:

**Phase 1:** Build the complete polished responsive React interface and all required pages.

**Phase 2:** Implement the Express backend, authentication, validation, middleware, and REST API.

**Phase 3:** Create the MySQL schema, migration scripts, connection pool, and setup instructions for MySQL Server and Workbench 8.0.

**Phase 4:** Implement local video/image uploads, secure file access, and metadata persistence.

**Phase 5:** Inspect and integrate my actual existing trained AI model through the most compatible supported runtime. Explain any format or runtime limitations.

**Phase 6:** Connect all frontend features to real backend endpoints and database records.

**Phase 7:** Test the complete workflow, fix errors, and document local execution and deployment.

## 15. Final Acceptance Criteria

The project is complete only when:
- The React frontend starts successfully.
- The Express backend starts successfully.
- The backend can connect to the configured MySQL Server.
- Database migrations execute safely.
- Users can register and log in.
- Citizens can submit complaints with video evidence.
- Uploaded files and their metadata persist correctly.
- Complaint history and statuses persist in MySQL.
- Authorized officers can review and update assigned complaints.
- Administrators can manage assignments and view analytics.
- The existing trained AI model is integrated only after its actual format and runtime requirements are verified.
- Genuine inference results are displayed and stored without fabricated predictions.
- Protected resources and role permissions are enforced server-side.
- The README explains installation, configuration, database setup, running both applications, model integration, and testing.

Start by inspecting any existing project files and preserving working functionality. Do not unnecessarily recreate or delete existing work. If information about my trained model or local MySQL installation is missing, clearly identify what needs to be checked instead of guessing.

**Now build the project step by step, produce real source files, and prioritize a working end-to-end application over a visual-only prototype.**  and i uploading few screenshots , make a page of how it works make little similar like it a cartoon explaining how you will use it  and front page reference , i added last two images 