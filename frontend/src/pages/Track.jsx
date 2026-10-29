
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  FileSearch,
  MapPin,
  Search,
  ShieldCheck,
  Sparkles,
  Building2,
  Wrench,
} from "lucide-react";

import trackHero from "../assets/gemini1.png";
import trackIllustration from "../assets/gemini2.png";
import "./Track.css";

const DEMO_REFERENCE = "CW-2026-00123";

const demoStages = [
  {
    title: "Submitted",
    description: "Report received",
    time: "12 Oct · 10:24 AM",
    icon: "submitted",
  },
  {
    title: "Under Review",
    description: "Details verified",
    time: "12 Oct · 2:15 PM",
    icon: "review",
  },
  {
    title: "Assigned to Department",
    description: "Department assigned",
    time: "13 Oct · 9:40 AM",
    icon: "assigned",
  },
  {
    title: "Work in Progress",
    description: "Repair work carried out",
    time: "16 Oct · 11:00 AM",
    icon: "work",
  },
  {
    title: "Resolved",
    description: "Issue marked resolved",
    time: "18 Oct · 4:30 PM",
    icon: "resolved",
  },
];

function StageIcon({ type }) {
  switch (type) {
    case "submitted":
      return <ClipboardCheck size={14} />;
    case "review":
      return <FileSearch size={14} />;
    case "assigned":
      return <Building2 size={14} />;
    case "work":
      return <Wrench size={14} />;
    default:
      return <CheckCircle2 size={14} />;
  }
}

export default function Track() {
  const navigate = useNavigate();

  const [reference, setReference] = useState(DEMO_REFERENCE);
  const [error, setError] = useState("");

  const handleTrack = (event) => {
    event.preventDefault();

    const complaintId = reference.trim().toUpperCase();

    if (!complaintId) {
      setError("Please enter your complaint reference number.");
      return;
    }

    setError("");

    navigate(
      `/track-report/result?id=${encodeURIComponent(complaintId)}`
    );
  };

  const scrollToTracker = () => {
    document
      .getElementById("track-search")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <main className="track-v2-page">
      {/* =====================================
          1. HERO SECTION
      ====================================== */}
      <section className="track-v2-hero">
        <div className="track-v2-hero-copy">
          <div className="track-v2-eyebrow">
            <span className="track-v2-dot" />
            TRANSPARENT. ACCOUNTABLE. CONNECTED.
          </div>

          <h1>
            Your complaint.
            <br />
            <span>Its progress.</span>
            <br />
            Your right to know.
          </h1>

          <p>
            Stay informed at every step. Track your civic complaint,
            follow its progress, and see the action recorded by the
            responsible department.
          </p>

          <div className="track-v2-hero-points">
            <div>
              <CheckCircle2 size={19} />
              <span>Complaint status updates</span>
            </div>

            <div>
              <ShieldCheck size={19} />
              <span>Transparent complaint tracking</span>
            </div>
          </div>

          <button
            className="track-v2-hero-button"
            onClick={scrollToTracker}
            type="button"
          >
            Track your complaint
            <ArrowRight size={18} />
          </button>
        </div>

        <div className="track-v2-hero-art">
          <div className="track-v2-hero-image-wrap">
            <img
              src={trackHero}
              alt="CityWatch AI complaint tracking illustration"
            />
          </div>

          <div className="track-v2-floating-card track-v2-float-top">
            <span className="track-v2-float-icon">
              <ShieldCheck size={21} />
            </span>

            <span>
              <strong>Stay informed</strong>
              <small>Every step matters</small>
            </span>
          </div>

          <div className="track-v2-floating-card track-v2-float-bottom">
            <span className="track-v2-float-check">
              <CheckCircle2 size={22} />
            </span>

            <span>
              <strong>Progress updates</strong>
              <small>From report to resolution</small>
            </span>
          </div>
        </div>
      </section>

      
      {/* PAGE 1: COMPLAINT JOURNEY */}
      <section className="track-journey-page">
        <div className="track-journey-container">
          <div className="track-journey-heading">
            <span className="track-journey-eyebrow">
              <ClipboardCheck size={16} />
              COMPLAINT JOURNEY
            </span>
            <h2>From Submission to Resolution</h2>
            <p>
              Follow the progress of a civic complaint, from the
              initial report through to its final resolution.
            </p>
          </div>

          <div className="track-journey-card">
            <div className="track-journey-card-header">
              <div>
                <span className="track-journey-label">REFERENCE ID</span>
                <h3>CW-2026-00123</h3>
              </div>
              <span className="track-journey-status">
                <CheckCircle2 size={14} />
                Resolved
              </span>
            </div>

            <div className="track-journey-timeline">
              {[
                {
                  title: "Submitted",
                  description: "Your report has been received.",
                  time: "12 Oct 2026 · 10:24 AM",
                  icon: <ClipboardCheck size={17} />,
                  color: "submitted",
                },
                {
                  title: "Under Review",
                  description: "The submitted details were reviewed.",
                  time: "12 Oct 2026 · 2:15 PM",
                  icon: <FileSearch size={17} />,
                  color: "review",
                },
                {
                  title: "Assigned to Department",
                  description: "The complaint was assigned for action.",
                  time: "13 Oct 2026 · 9:40 AM",
                  icon: <Building2 size={17} />,
                  color: "assigned",
                },
                {
                  title: "Work in Progress",
                  description: "Corrective work was recorded.",
                  time: "16 Oct 2026 · 11:00 AM",
                  icon: <Wrench size={17} />,
                  color: "work",
                },
                {
                  title: "Resolved",
                  description: "The demo record is marked as resolved.",
                  time: "18 Oct 2026 · 4:30 PM",
                  icon: <CheckCircle2 size={17} />,
                  color: "resolved",
                },
              ].map((stage, index, stages) => (
                <div className="track-journey-step" key={stage.title}>
                  <div className="track-journey-visual">
                    <div
                      className={`track-journey-marker ${stage.color}`}
                    >
                      {stage.icon}
                    </div>

                    {index < stages.length - 1 && (
                      <div className="track-journey-connector" />
                    )}
                  </div>

                  <div className="track-journey-step-content">
                    <div className="track-journey-step-heading">
                      <h4>{stage.title}</h4>
                      <span className="track-journey-completed">
                        Completed
                      </span>
                    </div>

                    <p>{stage.description}</p>

                    <span className="track-journey-time">
                      <Clock3 size={13} />
                      {stage.time}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <p className="track-journey-demo-note">
            This timeline uses sample data for demonstration.
          </p>
        </div>
      </section>

      {/* PAGE 2: ATTACHED EVIDENCE */}
      <section className="track-evidence-page">
        <div className="track-evidence-container">
          <div className="track-evidence-heading">
            <span className="track-journey-eyebrow">
              <ShieldCheck size={16} />
              ATTACHED EVIDENCE
            </span>

            <h2>See the Difference</h2>

            <p>
              Compare the previous condition with the current condition
              after corrective action.
            </p>
          </div>

          <div className="track-evidence-comparison">
            <article className="track-evidence-card">
              <div className="track-evidence-image">
                <img
                  src={trackHero}
                  alt="Illustrative image of the previous condition"
                />
                <span className="track-evidence-before">BEFORE</span>
              </div>

              <div className="track-evidence-caption">
                <span>01</span>
                <div>
                  <h3>Previous Condition</h3>
                  <p>Condition before corrective action.</p>
                </div>
              </div>
            </article>

            <div className="track-evidence-transition">
              <ArrowRight size={23} />
              <span>Comparison</span>
            </div>

            <article className="track-evidence-card">
              <div className="track-evidence-image">
                <img
                  src={trackIllustration}
                  alt="Illustrative image of the current condition"
                />
                <span className="track-evidence-after">AFTER</span>
              </div>

              <div className="track-evidence-caption">
                <span>02</span>
                <div>
                  <h3>Current Condition</h3>
                  <p>Condition after corrective action.</p>
                </div>
              </div>
            </article>
          </div>

          <div className="track-evidence-notice">
            <ShieldCheck size={18} />
            <p>
              Demo images are shown here. Actual evidence should be
              loaded from the complaint record.
            </p>
          </div>
        </div>
      </section>


      {/* =====================================
          5. COMPLAINT TRACKER — AT THE BOTTOM
      ====================================== */}
      <section
        className="track-v2-search-section"
        id="track-search"
      >
        <div className="track-v2-search-layout">
          <div className="track-v2-search-intro">
            <span className="track-v2-section-label">
              <Sparkles size={15} />
              COMPLAINT TRACKER
            </span>

            <h2>
              Find your complaint.
              <br />
              <span>Know what happens next.</span>
            </h2>

            <p>
              Enter the reference number you received after submitting
              your complaint to view its status and progress.
            </p>

            <div className="track-v2-search-benefits">
              <div>
                <span className="track-v2-benefit-icon">
                  <FileSearch size={20} />
                </span>

                <div>
                  <strong>Clear status updates</strong>
                  <small>
                    Understand the progress of your report.
                  </small>
                </div>
              </div>

              <div>
                <span className="track-v2-benefit-icon">
                  <Clock3 size={20} />
                </span>

                <div>
                  <strong>Follow each stage</strong>
                  <small>
                    See the recorded steps in the process.
                  </small>
                </div>
              </div>

              <div>
                <span className="track-v2-benefit-icon">
                  <MapPin size={20} />
                </span>

                <div>
                  <strong>Know the issue location</strong>
                  <small>
                    Review the location linked to your report.
                  </small>
                </div>
              </div>
            </div>
          </div>

          <div className="track-v2-search-card">
            <div className="track-v2-search-card-header">
              <span className="track-v2-search-card-icon">
                <Search size={23} />
              </span>

              <div>
                <h3>Track a complaint</h3>
                <p>Enter your complaint reference ID below.</p>
              </div>
            </div>

            <form
              className="track-v2-search"
              onSubmit={handleTrack}
            >
              <label htmlFor="complaint-reference">
                Complaint reference number
              </label>

              <div className="track-v2-input-wrap">
                <FileSearch size={19} />

                <input
                  id="complaint-reference"
                  className="track-v2-input"
                  type="text"
                  placeholder="e.g. CW-2026-00123"
                  value={reference}
                  onChange={(event) => {
                    setReference(event.target.value);
                    setError("");
                  }}
                  autoComplete="off"
                />
              </div>

              {error && (
                <p className="track-v2-message" role="alert">
                  {error}
                </p>
              )}

              <button
                className="track-v2-submit"
                type="submit"
              >
                Track Complaint
                <ArrowRight size={18} />
              </button>
            </form>

            <div className="track-v2-demo-note">
              <div className="track-v2-demo-note-icon">
                <Sparkles size={17} />
              </div>

              <div>
                <strong>Try the UI demo</strong>

                <p>
                  Select a sample reference to test the tracking page.
                </p>

                <button
                  type="button"
                  className="track-v2-demo-reference"
                  onClick={() => {
                    setReference("CW-2026-00123");
                    setError("");
                  }}
                >
                  CW-2026-00123
                  <span>Resolved demo</span>
                </button>

                <button
                  type="button"
                  className="track-v2-demo-reference"
                  onClick={() => {
                    setReference("CW-2026-00118");
                    setError("");
                  }}
                >
                  CW-2026-00118
                  <span>In progress demo</span>
                </button>
              </div>
            </div>

            <div className="track-v2-search-secure">
              <ShieldCheck size={16} />
              Demo records are for interface testing only.
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
