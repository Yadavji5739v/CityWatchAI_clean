import { useEffect, useState } from "react";
import { AlertCircle, LoaderCircle, X } from "lucide-react";
import { API_BASE_URL } from "../lib/api";


const TODAY = new Date().toISOString().slice(0, 10);

function suggestedDepartment(category, departments) {
  const normalized = String(category || "").toLowerCase();
  let keywords = [];
  if (normalized.includes("pothole") || normalized.includes("road damage")) {
    keywords = ["roads & public works"];
  } else if (normalized.includes("garbage") || normalized.includes("waste")) {
    keywords = ["sanitation"];
  } else if (normalized.includes("drainage") || normalized.includes("waterlogging") || normalized.includes("water logging")) {
    keywords = ["drainage"];
  } else if (normalized.includes("streetlight") || normalized.includes("street light")) {
    keywords = ["electrical"];
  } else if (normalized.includes("water supply")) {
    keywords = ["water supply"];
  } else if (normalized.includes("obstruction") || normalized.includes("parking")) {
    keywords = ["traffic", "roads & public works"];
  } else {
    keywords = ["roads & public works"];
  }

  return departments.find((department) =>
    keywords.some((keyword) => department.name.toLowerCase().includes(keyword)),
  )?.id || "";
}

export default function AssignOfficerModal({ complaint, onClose, onAssigned }) {
  const [departments, setDepartments] = useState([]);
  const [departmentId, setDepartmentId] = useState("");
  const [officers, setOfficers] = useState([]);
  const [officerId, setOfficerId] = useState("");
  const [priority, setPriority] = useState(complaint.priority?.toLowerCase() === "needs review" ? "medium" : complaint.priority?.toLowerCase() || "medium");
  const [dueDate, setDueDate] = useState("");
  const [instructions, setInstructions] = useState("");
  const [reassignmentReason, setReassignmentReason] = useState("");
  const [loadingDepartments, setLoadingDepartments] = useState(true);
  const [loadingOfficers, setLoadingOfficers] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    async function loadDepartments() {
      try {
        const response = await fetch(`${API_BASE_URL}/departments`, {
          headers: { Authorization: `Bearer ${localStorage.getItem("citywatch_token")}` },
          signal: controller.signal,
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Could not load departments.");
        setDepartments(data);
        const classifiedDepartment = data.find((department) => department.id === complaint.assigned_department_id);
        const suggested = classifiedDepartment?.id || suggestedDepartment(complaint.category, data);
        setDepartmentId(suggested);
        setLoadingOfficers(Boolean(suggested));
      } catch (loadError) {
        if (!controller.signal.aborted) {
          setError(loadError instanceof Error ? loadError.message : "Could not load departments.");
        }
      } finally {
        if (!controller.signal.aborted) setLoadingDepartments(false);
      }
    }
    loadDepartments();
    return () => controller.abort();
  }, [complaint.category, complaint.assigned_department_id]);

  useEffect(() => {
    if (!departmentId) {
      return undefined;
    }
    const controller = new AbortController();
    async function loadOfficers() {
      try {
        const response = await fetch(
          `${API_BASE_URL}/officers?department_id=${encodeURIComponent(departmentId)}`,
          {
            headers: { Authorization: `Bearer ${localStorage.getItem("citywatch_token")}` },
            signal: controller.signal,
          },
        );
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Could not load eligible officers.");
        setOfficers(data);
      } catch (loadError) {
        if (!controller.signal.aborted) {
          setError(loadError instanceof Error ? loadError.message : "Could not load eligible officers.");
        }
      } finally {
        if (!controller.signal.aborted) setLoadingOfficers(false);
      }
    }
    loadOfficers();
    return () => controller.abort();
  }, [departmentId]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (!departmentId || !officerId) {
      setError("Select a department and an eligible officer.");
      return;
    }
    if (complaint.assigned_officer_id && !reassignmentReason.trim()) {
      setError("A reason is required to reassign this complaint.");
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch(`${API_BASE_URL}/complaints/${encodeURIComponent(complaint.id)}/assign`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("citywatch_token")}`,
        },
        body: JSON.stringify({
          department_id: departmentId,
          officer_id: officerId,
          priority,
          due_date: dueDate || null,
          instructions: instructions.trim() || null,
          reassignment_reason: reassignmentReason.trim() || null,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Assignment could not be saved.");

      const department = departments.find((item) => item.id === departmentId);
      const officer = officers.find((item) => item.id === officerId);
      onAssigned({
        ...complaint,
        status: "Assigned",
        priority: priority[0].toUpperCase() + priority.slice(1),
        assigned_department_id: departmentId,
        assigned_officer_id: officerId,
        department: department?.name || data.department_name,
        officer_name: officer?.full_name || data.officer_name,
        due_date: dueDate || null,
      });
    } catch (assignmentError) {
      setError(assignmentError instanceof Error ? assignmentError.message : "Assignment could not be saved.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="assignment-modal-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !submitting) onClose();
    }}>
      <section className="assignment-modal" role="dialog" aria-modal="true" aria-labelledby="assignment-modal-title">
        <header className="assignment-modal-header">
          <div>
            <span className="eyebrow">COMPLAINT ASSIGNMENT</span>
            <h2 id="assignment-modal-title">{complaint.assigned_officer_id ? "Reassign officer" : "Assign officer"}</h2>
            <p>{complaint.id} · {complaint.title}</p>
          </div>
          <button className="icon-button" type="button" onClick={onClose} disabled={submitting} aria-label="Close assignment dialog"><X size={18} /></button>
        </header>

        <div className="assignment-complaint-summary">
          <span><strong>Category</strong>{complaint.category}</span>
          <span><strong>Location</strong>{complaint.location || "Not provided"}</span>
          <span><strong>Status</strong>{complaint.status}</span>
        </div>
        {complaint.description && (
          <p className="assignment-complaint-description">
            <strong>Complaint description</strong>{complaint.description}
          </p>
        )}

        <form className="assignment-form" onSubmit={handleSubmit}>
          <div className="assignment-form-grid">
            <label>
              Department <span className="required">*</span>
              <select
                value={departmentId}
                onChange={(event) => {
                  setDepartmentId(event.target.value);
                  setOfficers([]);
                  setOfficerId("");
                  setLoadingOfficers(Boolean(event.target.value));
                  setError("");
                }}
                disabled={loadingDepartments}
                required
              >
                <option value="">{loadingDepartments ? "Loading departments..." : "Select department"}</option>
                {departments.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}
              </select>
              {!loadingDepartments && departmentId === suggestedDepartment(complaint.category, departments) && (
                <small className="assignment-suggestion">Suggested from the complaint category</small>
              )}
            </label>
            <label>
              Eligible officer <span className="required">*</span>
              <select value={officerId} onChange={(event) => setOfficerId(event.target.value)} disabled={!departmentId || loadingOfficers || officers.length === 0} required>
                <option value="">{loadingOfficers ? "Loading officers..." : officers.length ? "Select officer" : "No active officer in this department"}</option>
                {officers.map((officer) => <option key={officer.id} value={officer.id}>{officer.full_name} · {officer.id}</option>)}
              </select>
            </label>
            <label>
              Priority
              <select value={priority} onChange={(event) => setPriority(event.target.value)}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </label>
            <label>
              Optional due date
              <input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} min={TODAY} />
            </label>
          </div>
          <label>
            Assignment instructions
            <textarea value={instructions} onChange={(event) => setInstructions(event.target.value)} rows={3} maxLength={2000} placeholder="Add context or work instructions for the assigned officer." />
          </label>
          {complaint.assigned_officer_id && (
            <label>
              Reason for reassignment <span className="required">*</span>
              <textarea value={reassignmentReason} onChange={(event) => setReassignmentReason(event.target.value)} rows={2} maxLength={1000} required placeholder="Explain why this assignment is changing." />
            </label>
          )}
          {error && <div className="form-error assignment-error" role="alert"><AlertCircle size={16} />{error}</div>}
          <footer className="assignment-modal-actions">
            <button className="secondary-button" type="button" onClick={onClose} disabled={submitting}>Cancel</button>
            <button className="primary-button" type="submit" disabled={submitting || loadingDepartments || loadingOfficers || !officers.length}>
              {submitting && <LoaderCircle className="spin" size={15} />}
              {submitting ? "Saving assignment..." : "Confirm assignment"}
            </button>
          </footer>
        </form>
      </section>
    </div>
  );
}
