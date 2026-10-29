
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  FileSearch,
  MapPin,
  ShieldCheck,
  AlertCircle,
} from "lucide-react";

import beforeImage from "../assets/gemini1.png";
import afterImage from "../assets/gemini2.png";
import "./TrackResult.jsx";
import "./Track.css";

const demoReports = {
  "CW-2026-00123": {
    id: "CW-2026-00123",
    title: "Pothole near main gate",
    category: "Roads and Infrastructure",
    location: "BFCET, Bathinda",
    status: "Resolved",
    submitted: "12 October 2026",
    updated: "18 October 2026",
    department: "Road Maintenance Department",
    description:
      "A reported pothole near the main gate that may affect commuters and campus visitors.",
    stages: [
      {
        title: "Complaint submitted",
        description: "The complaint was recorded in the demo system.",
        date: "12 October 2026",
        completed: true,
      },
      {
        title: "Initial review",
        description: "The submitted complaint details were reviewed.",
        date: "13 October 2026",
        completed: true,
      },
      {
        title: "Department assigned",
        description: "The report was assigned to the responsible department.",
        date: "14 October 2026",
        completed: true,
      },
      {
        title: "Action taken",
        description: "The demo record indicates that corrective action was taken.",
        date: "17 October 2026",
        completed: true,
      },
      {
        title: "Complaint resolved",
        description: "The demo record is marked as resolved.",
        date: "18 October 2026",
        completed: true,
      },
    ],
  },

  "CW-2026-00118": {
    id: "CW-2026-00118",
    title: "Overflowing garbage bin",
    category: "Waste Management",
    location: "Handiaya Road",
    status: "In Progress",
    submitted: "15 October 2026",
    updated: "20 October 2026",
    department: "Sanitation Department",
    description:
      "A report about an overflowing public garbage bin requiring sanitation attention.",
    stages: [
      {
        title: "Complaint submitted",
        description: "The complaint was recorded in the demo system.",
        date: "15 October 2026",
        completed: true,
      },
      {
        title: "Initial review",
        description: "The complaint details were reviewed.",
        date: "16 October 2026",
        completed: true,
      },
      {
        title: "Department assigned",
        description: "The report was assigned to the sanitation department.",
        date: "17 October 2026",
        completed: true,
      },
      {
        title: "Action in progress",
        description: "The demo record indicates that the issue is being addressed.",
        date: "Awaiting update",
        completed: false,
      },
      {
        title: "Complaint resolved",
        description: "This stage has not yet been completed in the demo record.",
        date: "Pending",
        completed: false,
      },
    ],
  },
};

export default function TrackResult() {
  const [searchParams] = useSearchParams();
  const complaintId = (searchParams.get("id") || "").trim().toUpperCase();
  const report = demoReports[complaintId];

  if (!report) {
    return (
      <main className="track-result-page">
        <div className="track-result-not-found">
          <div className="track-result-not-found-icon">
            <AlertCircle size={32} />
          </div>
          <h1>Complaint not found</h1>
          <p>
            We couldn't find a demo complaint with reference{" "}
            <strong>{complaintId || "not provided"}</strong>.
            Check the reference number and try again.
          </p>
          <Link to="/track-report" className="track-result-back-button">
            <ArrowLeft size={18} />
            Back to tracking
          </Link>
        </div>
      </main>
    );
  }

  const isResolved = report.status === "Resolved";
  const completedStages = report.stages.filter(
    (stage) => stage.completed
  ).length;

  return (
    <main className="track-result-page">
      <div className="track-result-container">
        <Link to="/track-report" className="track-result-back-link">
          <ArrowLeft size={17} />
          Back to complaint tracker
        </Link>

        {/* REPORT HEADER */}
        <section className="track-result-header">
          <div>
            <span className="track-result-eyebrow">
              <FileSearch size={15} />
              COMPLAINT TRACKING DETAILS
            </span>
            <h1>{report.title}</h1>
            <p className="track-result-subtitle">
              Follow the recorded progress of your civic complaint.
            </p>
          </div>

          <span
            className={`track-result-status ${
              isResolved ? "is-resolved" : "is-progress"
            }`}
          >
            <span />
            {report.status}
          </span>
        </section>

        {/* SUMMARY */}
        <section className="track-result-summary">
          <div className="track-result-summary-item">
            <span>Reference number</span>
            <strong>{report.id}</strong>
          </div>

          <div className="track-result-summary-item">
            <span>Category</span>
            <strong>{report.category}</strong>
          </div>

          <div className="track-result-summary-item">
            <span>Last updated</span>
            <strong>{report.updated}</strong>
          </div>
        </section>

        <div className="track-result-layout">
          <div className="track-result-main-column">
            {/* PROGRESS */}
            <section className="track-result-panel">
              <div className="track-result-panel-heading">
                <div>
                  <span className="track-result-section-kicker">
                    COMPLAINT JOURNEY
                  </span>
                  <h2>Progress timeline</h2>
                </div>
                <span className="track-result-stage-count">
                  {completedStages} of {report.stages.length} stages
                </span>
              </div>

              <div className="track-result-progress-track">
                <span
                  style={{
                    width: `${
                      (completedStages / report.stages.length) * 100
                    }%`,
                  }}
                />
              </div>

              <div className="track-result-timeline">
                {report.stages.map((stage, index) => (
                  <div
                    className={`track-result-stage ${
                      stage.completed ? "is-complete" : "is-pending"
                    }`}
                    key={stage.title}
                  >
                    <div className="track-result-stage-marker">
                      {stage.completed ? (
                        <CheckCircle2 size={21} />
                      ) : (
                        <Clock3 size={21} />
                      )}
                    </div>

                    <div className="track-result-stage-content">
                      <div className="track-result-stage-title-row">
                        <h3>{stage.title}</h3>
                        <span>
                          {stage.completed ? "Completed" : "Pending"}
                        </span>
                      </div>
                      <p>{stage.description}</p>
                      <small>{stage.date}</small>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* BEFORE / AFTER */}
            <section className="track-result-panel">
              <div className="track-result-panel-heading">
                <div>
                  <span className="track-result-section-kicker">
                    VISUAL EVIDENCE
                  </span>
                  <h2>Before and after</h2>
                </div>
              </div>

              <p className="track-result-evidence-note">
                These are illustrative project images, not verified
                photographic evidence of this complaint.
              </p>

              <div className="track-result-evidence-grid">
                <div className="track-result-evidence-card">
                  <div className="track-result-evidence-image">
                    <img src={beforeImage} alt="Illustrative before image" />
                    <span className="evidence-before">Before</span>
                  </div>
                  <div className="track-result-evidence-caption">
                    <strong>Reported condition</strong>
                    <p>Illustrative image for the interface demo.</p>
                  </div>
                </div>

                <div className="track-result-evidence-card">
                  <div className="track-result-evidence-image">
                    <img src={afterImage} alt="Illustrative after image" />
                    <span className="evidence-after">After</span>
                  </div>
                  <div className="track-result-evidence-caption">
                    <strong>Recorded outcome</strong>
                    <p>Illustrative image for the interface demo.</p>
                  </div>
                </div>
              </div>
            </section>
          </div>

          {/* COMPLAINT INFORMATION */}
          <aside className="track-result-sidebar">
            <section className="track-result-panel">
              <h2>Complaint information</h2>

              <div className="track-result-info-item">
                <span className="track-result-info-icon">
                  <MapPin size={19} />
                </span>
                <div>
                  <small>Reported location</small>
                  <strong>{report.location}</strong>
                </div>
              </div>

              <div className="track-result-info-item">
                <span className="track-result-info-icon">
                  <ShieldCheck size={19} />
                </span>
                <div>
                  <small>Responsible department</small>
                  <strong>{report.department}</strong>
                </div>
              </div>

              <div className="track-result-info-item">
                <span className="track-result-info-icon">
                  <Clock3 size={19} />
                </span>
                <div>
                  <small>Date submitted</small>
                  <strong>{report.submitted}</strong>
                </div>
              </div>

              <div className="track-result-info-item">
                <span className="track-result-info-icon">
                  <FileSearch size={19} />
                </span>
                <div>
                  <small>Issue category</small>
                  <strong>{report.category}</strong>
                </div>
              </div>
            </section>

            <section className="track-result-description-card">
              <h3>About this complaint</h3>
              <p>{report.description}</p>

              <div className="track-result-demo-warning">
                <ShieldCheck size={17} />
                <span>
                  Demo data only. This page does not contact a government
                  department or verify a real-world resolution.
                </span>
              </div>
            </section>
          </aside>
        </div>

        <div className="track-result-bottom">
          <Link to="/track-report" className="track-result-back-button">
            <ArrowLeft size={18} />
            Track another complaint
          </Link>
        </div>
      </div>
    </main>
  );
}
