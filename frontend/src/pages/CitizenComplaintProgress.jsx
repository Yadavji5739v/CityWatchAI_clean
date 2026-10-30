import { useEffect, useState } from "react";
import { ArrowLeft, Building2, CheckCircle2, CircleDot, ClipboardCheck, Eye, Image, MapPin, Send, UserRound } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { API_BASE_URL } from "../lib/api";



function stageState(status, stage) {
  const value = String(status || "").toLowerCase().replaceAll("_", " ");
  const order = { submitted: 1, verified: 2, assigned: 3, "in progress": 3, resolved: 4, closed: 4 };
  const current = order[value] || 1;
  return current >= stage ? "complete" : "upcoming";
}

export default function CitizenComplaintProgress({ complaints = [] }) {
  const { id } = useParams();
  const [complaint, setComplaint] = useState(() => complaints.find((item) => item.id === id) || null);
  const [error, setError] = useState("");
  const [previews, setPreviews] = useState([]);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE_URL}/complaints/${encodeURIComponent(id)}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("citywatch_token")}` }, signal: controller.signal,
    })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Could not load complaint progress.");
        setComplaint(data);
      })
      .catch((loadError) => !controller.signal.aborted && setError(loadError.message));
    return () => controller.abort();
  }, [id]);

  useEffect(() => {
    const files = complaint?.evidence_files?.filter((file) => file.file_type === "image") || [];
    if (!files.length) return undefined;
    const controller = new AbortController();
    const objectUrls = [];
    Promise.all(files.map(async (file) => {
      const response = await fetch(new URL(file.url, API_BASE_URL), {
        headers: { Authorization: `Bearer ${localStorage.getItem("citywatch_token")}` }, signal: controller.signal,
      });
      if (!response.ok) throw new Error("One or more submitted images could not be loaded.");
      const url = URL.createObjectURL(await response.blob());
      objectUrls.push(url);
      return { ...file, url };
    })).then(setPreviews).catch(() => {});
    return () => { controller.abort(); objectUrls.forEach(URL.revokeObjectURL); };
  }, [complaint?.id, complaint?.evidence_files]);

  if (!complaint && !error) return <main className="page-stack"><div className="empty-state"><CircleDot size={28} /><strong>Loading complaint progress…</strong></div></main>;
  if (error || !complaint) return <main className="page-stack"><div className="form-error">{error || "Complaint not found."}</div><Link className="secondary-button" to="/my-complaints"><ArrowLeft size={16} /> Back to my complaints</Link></main>;

  const stages = [
    { number: 1, title: "Complaint submitted", detail: "Your report and supporting evidence were received.", icon: Send },
    { number: 2, title: "Officer review", detail: "A city officer reviewed and approved the complaint.", icon: ClipboardCheck },
    { number: 3, title: "Department assigned", detail: complaint.department ? `Assigned to ${complaint.department}.` : "The responsible department will be assigned next.", icon: Building2 },
    { number: 4, title: "Resolved", detail: "The assigned department completed the work and recorded the outcome.", icon: CheckCircle2 },
  ];
  const resolved = ["resolved", "closed"].includes(String(complaint.status).toLowerCase());

  return <main className="page-stack citizen-progress-page">
    <div className="page-heading"><div><div className="eyebrow">MY COMPLAINT</div><h1>{complaint.title}</h1><p>Follow each stage of your civic report from submission to resolution.</p></div><Link className="secondary-button" to="/my-complaints"><ArrowLeft size={16} /> Back to my complaints</Link></div>
    <section className="content-panel citizen-case-hero"><div><span className="eyebrow">{complaint.id}</span><h2>{complaint.category}</h2><p><MapPin size={15} /> {complaint.location || "Location not specified"}</p></div><span className={`badge ${resolved ? "green" : "blue"}`}>{complaint.status}</span></section>
    <section className="content-panel citizen-progress-card"><header><div><h2>Resolution progress</h2><p>Four clear stages keep you informed.</p></div></header><ol className="citizen-stage-list">{stages.map(({ number, title, detail, icon: Icon }) => <li className={stageState(complaint.status, number)} key={number}><span className="citizen-stage-icon"><Icon size={17} /></span><div><strong>Step {number} · {title}</strong><p>{detail}</p></div><span className="stage-state">{stageState(complaint.status, number) === "complete" ? "Complete" : "Upcoming"}</span></li>)}</ol></section>
    <section className="evidence-comparison"><article className="content-panel"><header className="comparison-heading"><Image size={18} /><div><h2>Evidence you submitted</h2><p>Original photos attached to your complaint</p></div></header>{previews.length ? <div className="citizen-evidence-grid">{previews.map((file) => <img key={file.id} src={file.url} alt={`Submitted evidence: ${file.original_name}`} />)}</div> : <div className="citizen-evidence-empty"><Eye size={20} /> No image evidence was submitted with this report.</div>}</article><article className="content-panel"><header className="comparison-heading"><UserRound size={18} /><div><h2>Resolution evidence</h2><p>Photos supplied by the assigned department</p></div></header><div className="citizen-evidence-empty">{resolved ? <><CheckCircle2 size={20} /> The department has marked this complaint resolved. Resolution photos will appear here when added.</> : <><Building2 size={20} /> Resolution photos will be available after the department completes the work.</>}</div></article></section>
  </main>;
}
