
import { Link } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  MapPin,
  ShieldCheck,
  UserRound,
  Wrench,
  Clock3,
  MessageCircle,
} from "lucide-react";

import heroImage from "../assets/howitworks-hero.png";
import reportImage from "../assets/step-1-report-issue.png";
import reviewImage from "../assets/step-2-review-verification.png";
import assignImage from "../assets/step-3-assign-department.png";
import followImage from "../assets/step-4-follow-up.png";

const steps = [
  {
    number: "01",
    title: "Report an Issue",
    description:
      "Sign in as a citizen, upload a photo or video of the problem, add its location, and describe what needs attention.",
    detail: "Road damage, garbage, water leakage, and other civic issues.",
    image: reportImage,
    className: "step-report",
    icon: FileText,
  },
  {
    number: "02",
    title: "Review & Verification",
    description:
      "The submitted complaint can be reviewed for relevant details, location, and authenticity before it proceeds.",
    detail: "Review helps identify incomplete or potentially duplicate reports.",
    image: reviewImage,
    className: "step-review",
    icon: ShieldCheck,
  },
  {
    number: "03",
    title: "Department Assignment",
    description:
      "After verification, the complaint can be assigned to the appropriate department or responsible authority.",
    detail: "The responsible team can review the issue and take action.",
    image: assignImage,
    className: "step-assign",
    icon: Wrench,
  },
  {
    number: "04",
    title: "Follow Up & Track",
    description:
      "Sign in to check your complaint's latest status and review available updates until the issue is resolved.",
    detail: "Keep your complaint reference number for future follow-up.",
    image: followImage,
    className: "step-track",
    icon: Clock3,
  },
];

export default function HowItWorks() {
  return (
    <main className="public-site how-page">
      {/* Hero */}
      <section className="how-hero">
        <div className="how-hero-copy">
          <span className="public-eyebrow">
            <span className="eyebrow-dot" />
            HOW CITYWATCH AI WORKS
          </span>

          <h1>
            From reporting
            <br />
            to <span>real action.</span>
          </h1>

          <p>
            Help make your city better. Report civic problems, follow the
            verification process, and stay informed about the progress of
            your complaint.
          </p>

          <div className="public-hero-actions">
            <Link
              to="/login?role=citizen"
              className="public-button public-button-primary"
            >
              Report an Issue <ArrowRight size={17} />
            </Link>

            <Link
              to="/login?role=citizen"
              className="public-button public-button-secondary"
            >
              Track a Complaint
            </Link>
          </div>

          <div className="public-assurance">
            <span className="assurance-icon">
              <ShieldCheck size={19} />
            </span>
            <div>
              <strong>Your voice matters</strong>
              <small>Every report can help improve your community.</small>
            </div>
          </div>
        </div>

        <div className="how-hero-art how-image-art">
          <img
            src={heroImage}
            alt="Citizen reporting a pothole with help from CityWatch AI"
            className="how-illustration how-hero-image"
          />

          <div className="how-art-bubble bubble-top">
            <MapPin size={17} />
            Location-based reporting
          </div>

          <div className="how-art-bubble bubble-bottom">
            <CheckCircle2 size={17} />
            Track complaint progress
          </div>
        </div>
      </section>

      {/* Process steps */}
      <section className="how-steps-section">
        <div className="section-heading">
          <span className="public-eyebrow">
            <span className="eyebrow-dot" />
            SIMPLE & TRANSPARENT
          </span>

          <h2>How it works</h2>

          <p>
            Four simple stages help citizens report problems and follow
            their progress.
          </p>
        </div>

        <div className="how-steps-grid how-steps-grid-four">
          {steps.map((step) => {
            const StepIcon = step.icon;

            return (
              <article
                className={`how-step-card ${step.className}`}
                key={step.number}
              >
                <div className="step-card-art step-image-art">
                  <img
                    src={step.image}
                    alt={step.title}
                    className="step-illustration"
                    loading="lazy"
                  />
                  <span className="step-image-number">
                    {step.number}
                  </span>
                </div>

                <div className="step-card-copy">
                  <div className="step-card-heading">
                    <span className="step-card-number">
                      STEP {step.number}
                    </span>

                    <span className="step-card-icon">
                      <StepIcon size={19} />
                    </span>
                  </div>

                  <h3>{step.title}</h3>
                  <p>{step.description}</p>

                  <div className="step-card-detail">
                    <span>
                      <CheckCircle2 size={12} />
                    </span>
                    {step.detail}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      {/* Status journey */}
      <section className="how-status-section">
        <div className="status-story">
          <span className="public-eyebrow">
            <span className="eyebrow-dot" />
            STAY INFORMED
          </span>

          <h2>Know what happens after you report.</h2>

          <p>
            Your complaint may move through review, assignment, and action.
            The status displayed in your account depends on the latest
            updates recorded by the responsible team.
          </p>
        </div>

        <div className="status-path-card">
          <div className="status-path-header">
            <span className="status-path-mark">
              <ClipboardCheck size={20} />
            </span>

            <div>
              <strong>Complaint journey</strong>
              <small>Typical reporting workflow</small>
            </div>
          </div>

          <div className="status-path">
            <div className="status-path-item complete">
              <span><CheckCircle2 size={16} /></span>
              <div>
                <strong>Complaint submitted</strong>
                <small>Your report has been received.</small>
              </div>
            </div>

            <div className="status-path-item current">
              <span><ShieldCheck size={16} /></span>
              <div>
                <strong>Review and verification</strong>
                <small>Details are checked before further action.</small>
              </div>
            </div>

            <div className="status-path-item">
              <span><UserRound size={16} /></span>
              <div>
                <strong>Department assigned</strong>
                <small>The relevant authority can be notified.</small>
              </div>
            </div>

            <div className="status-path-item">
              <span><Wrench size={16} /></span>
              <div>
                <strong>Action and resolution</strong>
                <small>Progress can be updated by the responsible team.</small>
              </div>
            </div>
          </div>

          <div className="status-path-note">
            <MessageCircle size={15} />
            Check your account for the actual status of your complaint.
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="how-final-cta">
        <span className="final-cta-icon">
          <MapPin size={22} />
        </span>

        <span className="public-eyebrow">
          MAKE YOUR CITY BETTER
        </span>

        <h2>See a problem? Speak up.</h2>

        <p>
          Start by signing in as a citizen and submitting a clear report
          of the issue you want to bring to attention.
        </p>

        <Link
          to="/login?role=citizen"
          className="public-button public-button-primary"
        >
          Get Started <ArrowRight size={17} />
        </Link>

        <div className="final-cta-note">
          <ShieldCheck size={14} />
          Sign in to submit and manage your civic complaints.
        </div>
      </section>
    </main>
  );
}
