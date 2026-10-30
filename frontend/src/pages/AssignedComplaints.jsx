import { useEffect, useState } from "react";
import { ArrowUpRight, CheckCheck, Clock3, LoaderCircle, MapPin } from "lucide-react";
import { Link } from "react-router-dom";
import { API_BASE_URL } from "../lib/api";



async function fetchAssignments(signal) {
  const response = await fetch(`${API_BASE_URL}/assignments`, {
    headers: { Authorization: `Bearer ${localStorage.getItem("citywatch_token")}` },
    signal,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Assigned complaints could not be loaded.");
  return data;
}

export default function AssignedComplaints() {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatingId, setUpdatingId] = useState("");

  async function loadAssignments() {
    setLoading(true);
    setError("");
    try {
      setAssignments(await fetchAssignments());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Assigned complaints could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    fetchAssignments(controller.signal)
      .then((data) => setAssignments(data))
      .catch((loadError) => {
        if (!controller.signal.aborted) {
          setError(loadError instanceof Error ? loadError.message : "Assigned complaints could not be loaded.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  async function updateProgress(assignment, nextStatus) {
    setUpdatingId(assignment.complaint_id);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/complaints/${encodeURIComponent(assignment.complaint_id)}/progress`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("citywatch_token")}`,
        },
        body: JSON.stringify({ status: nextStatus }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Complaint progress could not be updated.");
      setAssignments((previous) => previous.map((item) =>
        item.complaint_id === assignment.complaint_id ? { ...item, status: data.status } : item,
      ));
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "Complaint progress could not be updated.");
    } finally {
      setUpdatingId("");
    }
  }

  return (
    <main className="page-stack">
      <div className="page-heading">
        <div>
          <div className="eyebrow">OFFICER WORKSPACE</div>
          <h1>Assigned Complaints</h1>
          <p>Cases routed to your department and awaiting approval, plus work assigned directly to you. Approved cases move to Pending Complaints.</p>
        </div>
        <button
          type="button"
          className="secondary-button"
          onClick={() => {
            loadAssignments();
          }}
        >
          Refresh assignments
        </button>
      </div>

      {error && <div className="form-error" role="alert">{error}</div>}
      <section className="content-panel">
        {loading ? (
          <div className="empty-state"><LoaderCircle className="spin" size={26} /><strong>Loading your assignments...</strong></div>
        ) : assignments.length === 0 ? (
          <div className="empty-state"><Clock3 size={30} /><strong>No assigned complaints</strong><p>AI-routed cases for your department and work assigned directly to you will appear here.</p></div>
        ) : (
          <div className="table-scroll">
            <table className="complaint-table officer-complaint-table">
              <thead>
                <tr>
                  <th>Reference</th>
                  <th>Complaint</th>
                  <th>Category</th>
                  <th>Location</th>
                  <th>Department</th>
                  <th>Priority</th>
                  <th>Assignment date</th>
                  <th>Due date</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {assignments.map((assignment) => (
                  <tr key={assignment.assignment_id}>
                    <td><strong>{assignment.complaint_id}</strong></td>
                    <td>{assignment.title}</td>
                    <td>{assignment.category}</td>
                    <td><span className="location-cell"><MapPin size={14} />{assignment.location || "Not provided"}</span></td>
                    <td>{assignment.department_name || "Awaiting review"}</td>
                    <td>{assignment.priority}</td>
                    <td>{assignment.assigned_at ? new Date(assignment.assigned_at).toLocaleDateString() : "—"}</td>
                    <td>{assignment.due_date ? new Date(`${assignment.due_date}T00:00:00`).toLocaleDateString() : "—"}</td>
                    <td>
                      <span className={`badge ${assignment.status === "Resolved" || assignment.status === "Closed" ? "green" : assignment.status === "In Progress" ? "purple" : "blue"}`}>{assignment.status}</span>
                      {assignment.department_queue === 1 && <small className="department-queue-note">AI-routed · awaiting approval</small>}
                    </td>
                    <td>
                      <div className="assignment-row-actions">
                        <Link className="officer-open-link" to={`/details/${assignment.complaint_id}`} state={{ from: "/officer/assigned" }}>
                          Details <ArrowUpRight size={14} />
                        </Link>
                        {assignment.status === "Assigned" && (
                          <button className="progress-action-button" type="button" onClick={() => updateProgress(assignment, "In Progress")} disabled={updatingId === assignment.complaint_id}>
                            {updatingId === assignment.complaint_id ? <LoaderCircle className="spin" size={14} /> : <Clock3 size={14} />} Start
                          </button>
                        )}
                        {assignment.status === "In Progress" && (
                          <button className="progress-action-button resolved" type="button" onClick={() => updateProgress(assignment, "Resolved")} disabled={updatingId === assignment.complaint_id}>
                            {updatingId === assignment.complaint_id ? <LoaderCircle className="spin" size={14} /> : <CheckCheck size={14} />} Resolve
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
