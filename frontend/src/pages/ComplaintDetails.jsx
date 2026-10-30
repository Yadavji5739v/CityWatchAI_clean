import { useEffect, useState } from "react";
import {
  ArrowLeft,
  CalendarDays,
  ClipboardCheck,
  Clock3,
  FileText,
  MapPin,
  Navigation,
  ShieldCheck,
  Tag,
  UserRound,
  Video,
} from "lucide-react";
import { Link, useLocation, useParams } from "react-router-dom";
import AssignOfficerModal from "../components/AssignOfficerModal";
import { API_BASE_URL } from "../lib/api";



function formatDate(value) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit",
  }).format(date);
}

function badgeTone(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("resolved") || text.includes("verified")) return "green";
  if (text.includes("progress") || text.includes("assigned")) return "blue";
  if (text.includes("high") || text.includes("critical")) return "purple";
  return "amber";
}

export default function ComplaintDetails({ complaints = [], user, onComplaintUpdated, onRefresh }) {
  const { id } = useParams();
  const locationState = useLocation();
  const backTo = locationState.state?.from || "/complaints";
  const cachedComplaint = complaints.find((item) => item.id === id);
  const [serverComplaint, setServerComplaint] = useState(null);
  const [detailLoadError, setDetailLoadError] = useState("");
  const complaint = serverComplaint?.id === id
    ? serverComplaint
    : cachedComplaint || locationState.state?.submittedComplaint;
  const [assignmentOpen, setAssignmentOpen] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [departments, setDepartments] = useState([]);
  const [departmentsLoading, setDepartmentsLoading] = useState(false);
  const [selectedDepartmentId, setSelectedDepartmentId] = useState(null);
  const [actionError, setActionError] = useState("");
  const [actionNotice, setActionNotice] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [videoLoading, setVideoLoading] = useState(false);
  const [videoError, setVideoError] = useState("");
  const [imageError, setImageError] = useState("");
  const [videoUrlPath, setVideoUrlPath] = useState("");
  const [videoErrorPath, setVideoErrorPath] = useState("");
  const [videoLoadingPath, setVideoLoadingPath] = useState("");
  const [imageEvidence, setImageEvidence] = useState({ complaintId: null, files: [] });

  useEffect(() => {
    const controller = new AbortController();
    async function loadComplaintDetails() {
      try {
        const response = await fetch(`${API_BASE_URL}/complaints/${encodeURIComponent(id)}`, {
          headers: { Authorization: `Bearer ${localStorage.getItem("citywatch_token")}` },
          signal: controller.signal,
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Complaint details could not be loaded.");
        setServerComplaint(result);
        setDetailLoadError("");
      } catch (error) {
        if (!controller.signal.aborted) {
          setDetailLoadError(error instanceof Error ? error.message : "Complaint details could not be loaded.");
        }
      }
    }
    loadComplaintDetails();
    return () => controller.abort();
  }, [id]);

  useEffect(() => {
    if (!["admin", "officer"].includes(user?.role)) return undefined;

    const controller = new AbortController();
    async function loadDepartments() {
      setDepartmentsLoading(true);
      try {
        const response = await fetch(`${API_BASE_URL}/departments`, {
          headers: { Authorization: `Bearer ${localStorage.getItem("citywatch_token")}` },
          signal: controller.signal,
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Departments could not be loaded.");
        setDepartments(result);
      } catch (error) {
        if (!controller.signal.aborted) {
          setActionError(error instanceof Error ? error.message : "Departments could not be loaded.");
        }
      } finally {
        if (!controller.signal.aborted) setDepartmentsLoading(false);
      }
    }
    loadDepartments();
    return () => controller.abort();
  }, [user?.role]);

  useEffect(() => {
    if (!complaint?.video_url) {
      return undefined;
    }
    const controller = new AbortController();
    let objectUrl = "";
    async function loadVideo() {
      setVideoLoadingPath(complaint.video_url);
      setVideoLoading(true);
      try {
        const response = await fetch(new URL(complaint.video_url, API_BASE_URL), {
          headers: { Authorization: `Bearer ${localStorage.getItem("citywatch_token")}` },
          signal: controller.signal,
        });
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(body.detail || "Video evidence could not be loaded.");
        }
        objectUrl = URL.createObjectURL(await response.blob());
        setVideoUrl(objectUrl);
        setVideoUrlPath(complaint.video_url);
      } catch (error) {
        if (!controller.signal.aborted) {
          setVideoError(error instanceof Error ? error.message : "Video evidence could not be loaded.");
          setVideoErrorPath(complaint.video_url);
        }
      } finally {
        if (!controller.signal.aborted) setVideoLoading(false);
      }
    }
    loadVideo();
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [complaint?.video_url]);

  useEffect(() => {
    const imageFiles = complaint?.evidence_files?.filter((file) => file.file_type === "image") || [];
    if (!imageFiles.length) {
      return undefined;
    }

    const controller = new AbortController();
    const objectUrls = [];
    async function loadImages() {
      try {
        const loadedImages = await Promise.all(imageFiles.map(async (file) => {
          const response = await fetch(new URL(file.url, API_BASE_URL), {
            headers: { Authorization: `Bearer ${localStorage.getItem("citywatch_token")}` },
            signal: controller.signal,
          });
          if (!response.ok) {
            const body = await response.json().catch(() => ({}));
            throw new Error(body.detail || `Could not load ${file.original_name}.`);
          }
          const url = URL.createObjectURL(await response.blob());
          objectUrls.push(url);
          return { ...file, preview_url: url };
        }));
        setImageEvidence({ complaintId: complaint.id, files: loadedImages });
      } catch (error) {
        if (!controller.signal.aborted) {
          setImageError(error instanceof Error ? error.message : "Image evidence could not be loaded.");
        }
      }
    }
    loadImages();
    return () => {
      controller.abort();
      objectUrls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [complaint?.id, complaint?.evidence_files]);

  async function verifyComplaint() {
    if (!departmentId) {
      setActionError("Choose a department before approving this complaint.");
      return;
    }
    setVerifying(true);
    setActionError("");
    setActionNotice("");
    try {
      const response = await fetch(`${API_BASE_URL}/complaints/${encodeURIComponent(complaint.id)}/verify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("citywatch_token")}`,
        },
        body: JSON.stringify({
          reason: "Approved and routed after officer review.",
          department_id: departmentId,
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Complaint verification failed.");
      const updatedComplaint = { ...complaint, ...result, status: "Verified" };
      setServerComplaint(updatedComplaint);
      onComplaintUpdated?.(updatedComplaint);
      // Refresh the global complaint list so this complaint moves from New → Pending
      onRefresh?.();
      const departmentName = departments.find((department) => department.id === departmentId)?.name;
      setActionNotice(
        `✓ Complaint approved and routed to ${departmentName || "the selected department"}. It will now appear in the Pending Complaints section.`,
      );
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Complaint verification failed.");
    } finally {
      setVerifying(false);
    }
  }

  const isAdmin = user?.role === "admin";
  const status = String(complaint?.status || "").toLowerCase();
  const departmentId = selectedDepartmentId ?? complaint?.assigned_department_id ?? "";
  const currentVideoUrl = complaint?.video_url === videoUrlPath ? videoUrl : "";
  const currentVideoError = complaint?.video_url === videoErrorPath ? videoError : "";
  const currentVideoLoading = complaint?.video_url === videoLoadingPath && videoLoading;
  const currentImageEvidence = imageEvidence.complaintId === complaint?.id
    ? imageEvidence.files
    : [];
  const canAssign = isAdmin && ["verified", "assigned", "in progress"].includes(status);
  const canReview = ["admin", "officer"].includes(user?.role)
    && ["pending review", "pending_review", "submitted"].includes(status);
  const hasCoordinates = complaint?.latitude != null && complaint?.longitude != null;
  const mapsUrl = hasCoordinates
    ? `https://www.google.com/maps?q=${encodeURIComponent(`${complaint.latitude},${complaint.longitude}`)}`
    : "";

  if (!complaint) {
    return (
      <main className="page-stack">
        <div className="page-heading">
          <div>
            <div className="eyebrow">CASE DETAILS</div>
            <h1>Complaint unavailable</h1>
            <p>This complaint could not be found in your authorized complaint list.</p>
          </div>
          <Link to={backTo} className="secondary-button"><ArrowLeft size={17} /> Back to complaints</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="page-stack">
      <div className="page-heading">
        <div>
          <div className="eyebrow">CASE DETAILS</div>
          <h1>{complaint.title}</h1>
          <p>Case {complaint.id} · Review the report, evidence, and next action.</p>
        </div>
        <div className="detail-heading-actions">
          {canAssign && (
            <button className="primary-button" type="button" onClick={() => setAssignmentOpen(true)}>
              <ClipboardCheck size={16} /> {complaint.assigned_officer_id ? "Reassign Officer" : "Assign Officer"}
            </button>
          )}
          <Link to={backTo} className="secondary-button">
            <ArrowLeft size={17} /> Back to complaints
          </Link>
        </div>
      </div>

      {detailLoadError && <div className="form-error" role="alert">{detailLoadError}</div>}
      {actionError && <div className="form-error detail-action-error" role="alert">{actionError}</div>}
      {actionNotice && <p className="review-assignment-note" role="status">{actionNotice}</p>}
      {canReview && (
        <section className="content-panel review-department-panel">
          <div>
            <h2>Review and route complaint</h2>
            <p>Confirm the report, choose the responsible department, then approve it for assignment.</p>
          </div>
          <label>
            Department
            <select
              value={departmentId}
              onChange={(event) => setSelectedDepartmentId(event.target.value)}
              disabled={departmentsLoading || verifying}
              required
            >
              <option value="">
                {departmentsLoading ? "Loading departments..." : "Select a department"}
              </option>
              {departments.map((department) => (
                <option key={department.id} value={department.id}>{department.name}</option>
              ))}
            </select>
          </label>
          <button
            className="primary-button"
            type="button"
            onClick={verifyComplaint}
            disabled={verifying || departmentsLoading || !departmentId}
          >
            <ClipboardCheck size={16} /> {verifying ? "Approving..." : "Approve & assign department"}
          </button>
          <p className="review-assignment-note">Approval routes the complaint to the selected department. An administrator can then assign an officer.</p>
        </section>
      )}
      <section className="content-panel case-overview">
        <header className="case-overview-header">
          <div>
            <span className="eyebrow">COMPLAINT SUMMARY</span>
            <h2>What needs attention</h2>
          </div>
          <div className="case-badges">
            <span className={`badge ${badgeTone(complaint.status)}`}>{complaint.status}</span>
            <span className={`badge ${badgeTone(complaint.priority)}`}>{complaint.priority}</span>
          </div>
        </header>
        <p className="case-description">{complaint.description || "No description was supplied with this complaint."}</p>
        <dl className="case-facts-grid">
          <div><dt><FileText size={15} /> Case ID</dt><dd>{complaint.id}</dd></div>
          <div><dt><Tag size={15} /> Category</dt><dd>{complaint.category || "Not specified"}</dd></div>
          <div><dt><CalendarDays size={15} /> Submitted</dt><dd>{formatDate(complaint.submittedAt || complaint.date)}</dd></div>
          <div><dt><UserRound size={15} /> Assigned to</dt><dd>{complaint.officer_name || complaint.department || "Awaiting assignment"}</dd></div>
          {complaint.due_date && <div><dt><Clock3 size={15} /> Due date</dt><dd>{formatDate(complaint.due_date)}</dd></div>}
        </dl>
      </section>

      <div className="case-detail-layout">
        <div className="case-detail-main">
          <section className="content-panel case-section">
            <header className="case-section-heading">
              <div><span className="section-icon"><MapPin size={17} /></span><div><h2>Location</h2><p>Reported place and coordinates</p></div></div>
              {mapsUrl && <a className="text-action" href={mapsUrl} target="_blank" rel="noreferrer"><Navigation size={14} /> Open map</a>}
            </header>
            <div className="location-summary">
              <MapPin size={20} />
              <div><strong>{complaint.location || "Location not provided"}</strong>{hasCoordinates && <span>{Number(complaint.latitude).toFixed(6)}, {Number(complaint.longitude).toFixed(6)}</span>}</div>
            </div>
          </section>

          <section className="content-panel case-section">
            <header className="case-section-heading">
              <div><span className="section-icon"><Video size={17} /></span><div><h2>Evidence</h2><p>Photos and video submitted with this case</p></div></div>
              <span className="evidence-count">{(complaint.evidence_files?.length || 0) + (complaint.video_url ? 1 : 0)} file(s)</span>
            </header>
            <div className="evidence-content">
          {currentVideoLoading && <div className="video-evidence-state"><Video size={18} /> Loading video evidence...</div>}
          {currentVideoUrl && <div className="video-preview-card detail-video"><video src={currentVideoUrl} controls preload="metadata" /></div>}
          {currentVideoError && <div className="form-error" role="alert">{currentVideoError}</div>}
          {!complaint.video_url && !complaint.evidence_files?.length && (
            <div className="video-evidence-state"><Video size={18} />{complaint.videoName || complaint.video || "No video evidence attached"}</div>
          )}
          {complaint.videoName && currentVideoUrl && <p className="detail-video-name">{complaint.videoName}</p>}
          {currentImageEvidence.map((file) => (
            <div className="video-preview-card detail-video" key={file.id}>
              <img src={file.preview_url} alt={`Evidence: ${file.original_name}`} />
              <p className="detail-video-name">{file.original_name}</p>
            </div>
          ))}
          {imageError && <div className="form-error" role="alert">{imageError}</div>}
            </div>
          </section>

          {complaint.ai_analysis && (
            <section className="content-panel case-section">
              <header className="case-section-heading"><div><span className="section-icon"><ShieldCheck size={17} /></span><div><h2>AI assessment</h2><p>Decision support only — review before acting</p></div></div></header>
              <div className="ai-assessment">
          <p>
            {complaint.ai_analysis.predicted_category
              ? `Detected ${complaint.ai_analysis.predicted_category}${complaint.ai_analysis.confidence != null
                ? ` with ${(Number(complaint.ai_analysis.confidence) * 100).toFixed(1)}% confidence.`
                : "."
              }`
              : complaint.ai_analysis.summary}
          </p>
          {complaint.ai_analysis.summary && complaint.ai_analysis.predicted_category && (
            <p>{complaint.ai_analysis.summary}</p>
          )}
          <span className={`badge ${complaint.ai_analysis.predicted_category ? "green" : "amber"}`}>
            {String(complaint.ai_analysis.analysis_status || "not analyzed").replaceAll("_", " ")}
          </span>
              </div>
            </section>
          )}
        </div>

        <aside className="case-detail-aside">
          <section className="content-panel case-section case-assignment-card">
            <header className="case-section-heading"><div><span className="section-icon"><ClipboardCheck size={17} /></span><div><h2>Case ownership</h2><p>Routing and assignment</p></div></div></header>
            <dl className="assignment-facts">
              <div><dt>Department</dt><dd>{complaint.department || (status.includes("pending review") || status === "submitted" ? "Awaiting review" : "Not assigned")}</dd></div>
              <div><dt>Officer</dt><dd>{complaint.officer_name || "Not assigned"}</dd></div>
              <div><dt>Current status</dt><dd><span className={`badge ${badgeTone(complaint.status)}`}>{complaint.status}</span></dd></div>
            </dl>
          </section>

          <section className="content-panel case-section timeline-card">
            <header className="case-section-heading"><div><span className="section-icon"><Clock3 size={17} /></span><div><h2>Case timeline</h2><p>Recent case activity</p></div></div></header>
            <ol className="timeline">
          {complaint.timeline?.map((item) => (
            <li key={item.label}>
              <strong>{item.label}</strong>
              <span>{item.detail}</span>
            </li>
          )) || (
              <li>
                <strong>Submitted</strong>
                <span>Complaint recorded and queued for review.</span>
              </li>
            )}
            </ol>
          </section>
        </aside>
      </div>

      <div className="disclaimer">
        <ShieldCheck size={17} />
        <span>AI confidence and suggested priority are decision support tools, not proof of validity.</span>
      </div>
      {assignmentOpen && (
        <AssignOfficerModal
          complaint={complaint}
          onClose={() => setAssignmentOpen(false)}
          onAssigned={(updatedComplaint) => {
            onComplaintUpdated?.(updatedComplaint);
            setAssignmentOpen(false);
          }}
        />
      )}
    </main>
  );
}
