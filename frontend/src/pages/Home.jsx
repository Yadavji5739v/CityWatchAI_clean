import { useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Camera,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Construction,
  Lightbulb,
  MapPin,
  MessageSquareText,
  ShieldCheck,
  Trash2,
  Truck,
  Droplets,
  TreeDeciduous,
  CircleHelp,
  Users,
  Toilet,
  ParkingCircle,
  HardHat,
  MoreHorizontal,
  TrendingUp,
  Building2,
  Clock3,
  Star,
} from "lucide-react";
import { Link } from "react-router-dom";

import heroIllustration from "../assets/citywatch-hero-illustration.png";
// import { TrendingUp, CheckCircle2, Users, Building2, Clock3, Star } from "lucide-react";

import potholeImage from "../assets/pothole.png";
import garbageImage from "../assets/garbage.png";
import openManholeImage from "../assets/open_manhole.png";
import waterloggingImage from "../assets/waterlogging.png";
import streetlightImage from "../assets/streetlight_issue.png";
import parkingImage from "../assets/illegal_parking.png";
import treeImage from "../assets/tree_issue.png";
import constructionImage from "../assets/construction_issue.png";
import toiletImage from "../assets/public_toilet_issue.png";
import otherImage from "../assets/other_civic_issue.png";

const categories = [
  {
    label: "Pothole",
    description: "Damaged roads and potholes",
    image: potholeImage,
    icon: Construction,
    color: "blue",
  },
  {
    label: "Garbage",
    description: "Overflowing bins and litter",
    image: garbageImage,
    icon: Trash2,
    color: "mint",
  },
  {
    label: "Open Manhole",
    description: "Missing or damaged covers",
    image: openManholeImage,
    icon: Construction,
    color: "slate",
  },
  {
    label: "Waterlogging",
    description: "Water accumulation on roads",
    image: waterloggingImage,
    icon: Droplets,
    color: "sky",
  },
  {
    label: "Streetlight Issue",
    description: "Broken or non-working lights",
    image: streetlightImage,
    icon: Lightbulb,
    color: "amber",
  },
  {
    label: "Illegal Parking",
    description: "Vehicles in restricted zones",
    image: parkingImage,
    icon: ParkingCircle,
    color: "rose",
  },
  {
    label: "Tree Issue",
    description: "Fallen or hazardous trees",
    image: treeImage,
    icon: TreeDeciduous,
    color: "mint",
  },
  {
    label: "Construction Issue",
    description: "Unsafe construction work",
    image: constructionImage,
    icon: HardHat,
    color: "orange",
  },
  {
    label: "Public Toilet Issue",
    description: "Dirty or damaged public toilets",
    image: toiletImage,
    icon: Toilet,
    color: "blue",
  },
  {
    label: "Other",
    description: "Any other local civic problem",
    image: otherImage,
    icon: MoreHorizontal,
    color: "slate",
  },
];

const faqs = [
  {
    question: "What is CityWatch AI?",
    answer:
      "CityWatch AI helps citizens report neighborhood problems and follow updates about their complaints.",
  },
  {
    question: "What types of problems can I report?",
    answer:
      "You can report potholes, garbage, open manholes, waterlogging, streetlight issues, illegal parking, tree issues, construction problems, public toilet issues, and other civic concerns supported by the reporting form.",
  },
  {
    question: "How do I submit a report?",
    answer:
      "Open Report an Issue, sign in as a citizen if prompted, provide the issue details and location, attach evidence if available, and submit the form.",
  },
  {
    question: "Do I need to upload a photo or video?",
    answer:
      "Photos and videos can help explain the problem. Follow the reporting form to see whether an attachment is optional or required.",
  },
  {
    question: "How does AI help?",
    answer:
      "AI can assist with supported tasks such as suggesting issue categories or organizing evidence. It does not replace human review or guarantee a complaint's validity.",
  },
  {
    question: "Can I track my complaint?",
    answer:
      "Use the Track page to enter your report ID and check the status and updates associated with your complaint.",
  },
  {
    question: "How long does resolution take?",
    answer:
      "Resolution time depends on the issue, verification, department workload, and the action required. An immediate resolution cannot be guaranteed.",
  },
  {
    question: "What if my complaint is not resolved?",
    answer:
      "Check the latest status and any instructions provided. If follow-up is supported, add relevant information or contact the responsible civic authority.",
  },
];



{/* Impact / Measurable Change */}
<section className="impact-section">
  <div className="impact-heading">
    <span className="impact-eyebrow">OUR IMPACT</span>
    <h2>
      Real Results.
      <br />
      <span>Measurable Change.</span>
    </h2>
    <p>
      Every report is a step toward a cleaner, safer, and more
      responsive community.
    </p>
  </div>

  <div className="impact-stats-grid">
    <article className="impact-stat-card blue">
      <span className="impact-stat-icon">
        <TrendingUp size={23} />
      </span>
      <strong>1,248+</strong>
      <p>Issues Reported</p>
    </article>

    <article className="impact-stat-card green">
      <span className="impact-stat-icon">
        <CheckCircle2 size={23} />
      </span>
      <strong>942+</strong>
      <p>Issues Resolved</p>
    </article>

    <article className="impact-stat-card purple">
      <span className="impact-stat-icon">
        <Users size={23} />
      </span>
      <strong>760+</strong>
      <p>Active Citizens</p>
    </article>

    <article className="impact-stat-card orange">
      <span className="impact-stat-icon">
        <Building2 size={23} />
      </span>
      <strong>12+</strong>
      <p>Departments Connected</p>
    </article>
  </div>

  <div className="impact-summary">
    <article>
      <strong className="green-text">75.5%</strong>
      <span>Resolution Rate</span>
    </article>

    <article>
      <strong className="blue-text">4.2 days</strong>
      <span>Average Resolution Time</span>
    </article>

    <article>
      <strong className="purple-text">
        <Star size={22} fill="currentColor" /> 4.8/5
      </strong>
      <span>Citizen Satisfaction</span>
    </article>
  </div>

  <p className="impact-disclaimer">
    <Clock3 size={14} />
    Illustrative demo statistics — actual impact metrics will be
    displayed when connected to verified report data.
  </p>
</section>


export default function Home() {
  const [openFaq, setOpenFaq] = useState(0);

  return (
    <main className="public-main home-flow">
      {/* PHASE 1: HERO */}
      <section className="public-hero home-flow-hero" id="home">
        <div className="public-hero-inner">
          <div className="public-hero-copy">
            <span className="public-eyebrow home-reference-eyebrow">
              <span className="eyebrow-dot" />
              A CLEANER, SAFER, SMARTER CITY
            </span>

            <h1>
              Your city.
              <br />
              Your voice.
              <br />
              <span>Real change.</span>
            </h1>

            <p>
              Report local problems easily, track progress in real time,
              and help build a cleaner, safer, and smarter city together.
            </p>

            <div className="public-hero-actions">
              <Link
                to="/report"
                className="public-button public-button-primary"
              >
                Report an issue <ArrowRight size={18} />
              </Link>

              <Link
                to="/how-it-works"
                className="public-button public-button-secondary"
              >
                See how it works <ChevronRight size={17} />
              </Link>
            </div>

            <div className="home-flow-trust">
              <span>
                <ShieldCheck size={15} />
                Human-reviewed process
              </span>
              <span>
                <Check size={15} />
                Track your report
              </span>
            </div>
          </div>

          <div className="public-hero-art home-reference-art">
            <img
              className="home-reference-illustration"
              src={heroIllustration}
              alt="Citizen reporting a pothole with CityWatch AI"
            />

            <div className="home-reference-bubble pothole-bubble">
              Spotted a pothole?
              <br />
              <strong>
                Just click, upload
                <br />
                and report!
              </strong>
            </div>

            <div className="home-reference-bubble ai-bubble">
              <strong>
                Our AI helps
                <br />
                find the right
                <br />
                issue category!
              </strong>
            </div>
          </div>
        </div>

        <div className="home-reference-benefits">
          <span>
            <i className="benefit-icon violet">✣</i>
            AI-assisted
            <br />
            classification
          </span>

          <span>
            <i className="benefit-icon mint">
              <MapPin size={17} />
            </i>
            Easy to use
          </span>

          <span>
            <i className="benefit-icon amber">ϟ</i>
            Track your report
          </span>

          <span>
            <i className="benefit-icon rose">♥</i>
            Make a real impact
          </span>
        </div>
      </section>

      {/* PHASE 2: COMMON CIVIC ISSUES */}
      <section
        className="public-section category-section home-flow-section"
        id="issues"
      >
        <div className="section-heading home-issues-heading">
          <span className="public-eyebrow">WHAT NEEDS ATTENTION?</span>

          <h2>
            Common <span>Civic Issues</span>
          </h2>

          <p>
            Report local problems and help make your city cleaner,
            safer, and better for everyone.
          </p>
        </div>

        <div className="home-issues-grid">
          {categories.map(
            ({ label, description, image, icon: Icon, color }) => (
              <Link
                to="/report"
                className="home-issue-card"
                key={label}
                aria-label={`Report ${label.toLowerCase()}`}
                title={`Report ${label}`}
              >
                <div className="home-issue-image-wrap">
                  <img
                    className="home-issue-image"
                    src={image}
                    alt={label}
                    loading="lazy"
                  />

                  <span className={`home-issue-image-icon ${color}`}>
                    <Icon size={19} />
                  </span>
                </div>

                <div className="home-issue-card-content">
                  <h3>{label}</h3>
                  <p>{description}</p>

                  {/* <span className="home-issue-action">
                    Report issue
                    <ArrowUpRight size={16} />
                  </span> */}
                </div>
              </Link>
            )
          )}
        </div>

        <div className="home-issues-bottom">
          <p>
            <Truck size={17} />
            Don't see your issue? Choose Other to report another
            neighborhood concern.
          </p>

          <Link
            to="/report"
            className="public-button public-button-primary"
          >
            Report a civic issue <ArrowRight size={17} />
          </Link>
        </div>
      </section>

      {/* PHASE 3: REDESIGNED REPORTING JOURNEY */}
      <section className="public-process-section process-redesign">
        <div className="process-redesign-copy">
          <span className="process-redesign-badge">
            <ShieldCheck size={15} />
            SIMPLE. TRANSPARENT. COMMUNITY-POWERED.
          </span>

          <span className="public-eyebrow">
            FROM REPORT TO FOLLOW-THROUGH
          </span>

          <h2>
            Your report.
            <br />
            <span>Real action.</span>
            <br />
            A better neighborhood.
          </h2>

          <p className="process-redesign-description">
            Spotted something that needs attention? Share it with CityWatch
            AI. We help organize your report so you can follow its progress
            every step of the way.
          </p>

          <div className="process-redesign-checklist">
            <div>
              <span><Check size={14} /></span>
              <p>Report a local issue with details and photos</p>
            </div>

            <div>
              <span><Check size={14} /></span>
              <p>Get your report organized for human review</p>
            </div>

            <div>
              <span><Check size={14} /></span>
              <p>Follow updates using your report ID</p>
            </div>

            <div>
              <span><Check size={14} /></span>
              <p>See the latest status as updates become available</p>
            </div>
          </div>

          <div className="process-redesign-actions">
            <Link
              to="/report"
              className="public-button public-button-primary"
            >
              Start a report <ArrowRight size={17} />
            </Link>

            <Link
              to="/how-it-works"
              className="process-redesign-text-link"
            >
              Explore how it works <ChevronRight size={16} />
            </Link>
          </div>

          <div className="process-redesign-trust">
            <ShieldCheck size={17} />
            <span>
              <strong>People remain in control.</strong>
              <small>
                AI may assist with organizing reports; reviewers make
                decisions.
              </small>
            </span>
          </div>
        </div>

        <div className="process-redesign-visual">
          <div className="process-visual-heading">
            <div>
              <span className="process-visual-kicker">
                YOUR REPORT JOURNEY
              </span>
              <h3>Three steps. One clearer process.</h3>
            </div>

            <span className="process-visual-icon">
              <MapPin size={19} />
            </span>
          </div>

          <div className="process-journey">
            <div className="process-journey-line" />

            <article className="process-journey-step step-blue">
              <div className="process-journey-icon">
                <Camera size={22} />
                <span className="process-journey-number">01</span>
              </div>

              <div className="process-journey-copy">
                <span className="process-step-tag">START HERE</span>
                <h4>Report the issue</h4>
                <p>
                  Add a description, location and optional evidence.
                </p>
              </div>

              <span className="process-journey-check">
                <Check size={14} />
              </span>
            </article>

            <article className="process-journey-step step-amber">
              <div className="process-journey-icon">
                <MessageSquareText size={22} />
                <span className="process-journey-number">02</span>
              </div>

              <div className="process-journey-copy">
                <span className="process-step-tag">REVIEW</span>
                <h4>Details are checked</h4>
                <p>
                  A reviewer checks the submitted information and evidence.
                </p>
              </div>

              <span className="process-journey-check">
                <Check size={14} />
              </span>
            </article>

            <article className="process-journey-step step-green">
              <div className="process-journey-icon">
                <CheckCircle2 size={22} />
                <span className="process-journey-number">03</span>
              </div>

              <div className="process-journey-copy">
                <span className="process-step-tag">STAY INFORMED</span>
                <h4>Follow the progress</h4>
                <p>
                  Check the report status and read updates when available.
                </p>
              </div>

              <span className="process-journey-check">
                <Check size={14} />
              </span>
            </article>
          </div>

          <div className="process-journey-footer">
            <span className="process-live-dot" />
            <span>
              One place to keep track of your civic report
            </span>
            <Link to="/track-report" aria-label="Track a report">
              <ArrowRight size={17} />
            </Link>
          </div>

          <div className="process-decoration process-decoration-one" />
          <div className="process-decoration process-decoration-two" />
        </div>
      </section>

      {/* FAQ */}
      <section className="public-section home-flow-faq" id="faq">
        <div className="section-heading">
          <span className="public-eyebrow">HERE TO HELP</span>
          <h2>Frequently asked questions.</h2>
          <p>
            Quick answers to common questions about civic reporting
            and tracking your complaints.
          </p>
        </div>

        <div className="home-flow-faq-layout">
          <aside className="home-flow-faq-intro">
            <span className="home-flow-faq-icon">
              <CircleHelp size={28} />
            </span>

            <h3>Need a little help?</h3>

            <p>
              Learn how to submit a report and understand what happens
              after you share a civic issue.
            </p>

            <Link to="/how-it-works" className="public-text-link">
              Learn more <ArrowRight size={16} />
            </Link>

            <div className="home-flow-faq-note">
              <ShieldCheck size={16} />
              People review reports and make decisions.
            </div>
          </aside>

          <div className="home-flow-faq-list">
            {faqs.map(({ question, answer }, index) => {
              const isOpen = openFaq === index;

              return (
                <article
                  className={`home-flow-faq-item ${
                    isOpen ? "is-open" : ""
                  }`}
                  key={question}
                >
                  <button
                    type="button"
                    className="home-flow-faq-question"
                    aria-expanded={isOpen}
                    onClick={() => setOpenFaq(isOpen ? -1 : index)}
                  >
                    <span className="home-flow-faq-number">
                      {String(index + 1).padStart(2, "0")}
                    </span>

                    <span>{question}</span>

                    <ChevronDown
                      size={18}
                      className="home-flow-faq-chevron"
                    />
                  </button>

                  {isOpen && (
                    <div className="home-flow-faq-answer">
                      <p>{answer}</p>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        </div>
      </section>

      {/* FINAL CALL TO ACTION */}
      <section className="public-cta-section home-flow-cta">
        <div className="cta-mark">
          <ShieldCheck size={25} />
        </div>

        <div>
          <span className="public-eyebrow">
            YOUR NEIGHBORHOOD STARTS HERE
          </span>
          <h2>Noticed something? Let's get it on the record.</h2>
          <p>Share the location and a few details to get started.</p>
        </div>

        <Link
          to="/report"
          className="public-button public-button-light"
        >
          Make a report <ArrowRight size={17} />
        </Link>
      </section>

      {/* FOOTER */}
      <footer className="home-flow-footer">
        <div className="home-flow-footer-main">
          <div className="home-flow-footer-brand">
            <Link to="/" className="home-flow-logo">
              <span>
                <ShieldCheck size={24} />
              </span>
              <strong>
                CityWatch <b>AI</b>
              </strong>
            </Link>

            <p>
              A simpler way to report civic problems, follow updates,
              and help build cleaner, safer neighborhoods.
            </p>

            <span className="home-flow-tagline">
              Your city. Your voice. Real change.
            </span>
          </div>

          <div className="home-flow-footer-column">
            <h3>Explore</h3>
            <Link to="/">Home</Link>
            <Link to="/how-it-works">How it works</Link>
            <Link to="/civic-issues">Civic issues</Link>
            <Link to="/dashboard">Dashboard</Link>
          </div>

          <div className="home-flow-footer-column">
            <h3>Get started</h3>
            <Link to="/report">Report an issue</Link>
            <Link to="/track-report">Track a report</Link>
            <Link to="/login">Log in / Sign up</Link>
          </div>

          <div className="home-flow-footer-column">
            <h3>Helpful links</h3>
            <a href="#faq">Frequently asked questions</a>
            <Link to="/how-it-works">Reporting guide</Link>
            <a href="#home">Back to home</a>
          </div>
        </div>

        <div className="home-flow-footer-bottom">
          <span>
            © {new Date().getFullYear()} CityWatch AI. All rights reserved.
          </span>

          <span className="home-flow-footer-note">
            <Users size={14} />
            Built for better civic engagement.
          </span>

          <a href="#home" className="home-flow-back-top">
            Back to top ↑
          </a>
        </div>
      </footer>
    </main>
  );
}
