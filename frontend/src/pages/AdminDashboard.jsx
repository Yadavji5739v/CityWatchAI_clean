import { useState } from "react";
import { AlertTriangle, ArrowUpRight, ChartColumn, ClipboardList, Users } from "lucide-react";
import { Link } from "react-router-dom";
import AssignOfficerModal from "../components/AssignOfficerModal";

export default function AdminDashboard({ complaints = [], stats, loading = false, onComplaintUpdated }) {
  const [assignmentComplaint, setAssignmentComplaint] = useState(null);
  const cards = [
    { label: "Total complaints", value: stats?.total_complaints ?? complaints.length, icon: ClipboardList, color: "blue" },
    { label: "Pending verification", value: stats?.pending_verification ?? 0, icon: AlertTriangle, color: "amber" },
    { label: "Unassigned verified", value: stats?.unassigned_complaints ?? 0, icon: ChartColumn, color: "purple" },
    { label: "Active assignments", value: stats?.active_assignments ?? 0, icon: Users, color: "green" },
  ];

  return (
    <main className="page-stack">
      <div className="page-heading">
        <div>
          <div className="eyebrow">ADMIN CONTROL</div>
          <h1>Operations dashboard</h1>
          <p>Review reports, assign verified complaints, and monitor officer workload.</p>
        </div>
        <Link to="/admin/complaints" className="secondary-button">All complaints <ArrowUpRight size={15} /></Link>
      </div>

      <section className="stats-grid">
        {cards.map(({ label, value, icon: Icon, color }) => (
          <article className="stat-card" key={label}>
            <div className={`stat-icon ${color}`}><Icon size={20} /></div>
            <div className="stat-label">{label}</div>
            <div className="stat-value">{loading && !stats ? "…" : value}</div>
          </article>
        ))}
      </section>

      <section className="content-panel">
        <div className="panel-heading">
          <div>
            <h2>Complaint review and assignment</h2>
            <p>Verify reports before assigning them to an active officer.</p>
          </div>
        </div>
        <div className="table-scroll">
          <table className="complaint-table admin-complaint-table">
            <thead>
              <tr><th>Complaint</th><th>Department</th><th>Priority</th><th>Status</th><th>Action</th></tr>
            </thead>
            <tbody>
              {complaints.slice(0, 8).map((item) => {
                const normalizedStatus = String(item.status).toLowerCase();
                const assignable = ["verified", "assigned", "in progress"].includes(normalizedStatus);
                return (
                  <tr key={item.id}>
                    <td><strong>{item.title}</strong><small>{item.id} · {item.category}</small></td>
                    <td>{item.department || "Unassigned"}</td>
                    <td>{item.priority}</td>
                    <td><span className={`badge ${normalizedStatus === "resolved" || normalizedStatus === "closed" ? "green" : normalizedStatus === "in progress" ? "purple" : "amber"}`}>{item.status}</span></td>
                    <td>
                      <div className="admin-row-actions">
                        {assignable ? (
                          <button className="primary-button small" type="button" onClick={() => setAssignmentComplaint(item)}>
                            {item.assigned_officer_id ? "Reassign Officer" : "Assign Officer"}
                          </button>
                        ) : (
                          <Link className="officer-open-link" to={`/details/${item.id}`} state={{ from: "/admin" }}>
                            Review <ArrowUpRight size={14} />
                          </Link>
                        )}
                        <Link className="text-link" to={`/details/${item.id}`} state={{ from: "/admin"}} aria-label={`View details for ${item.title}`}>Details</Link>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {complaints.length === 0 && (
                <tr><td colSpan="5">No complaints are available for review.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="admin-workload-grid">
        <article className="content-panel">
          <div className="panel-heading"><div><h2>Assignments by department</h2><p>Active cases assigned to each department.</p></div></div>
          <div className="admin-workload-list">
            {(stats?.department_workload || []).map((department) => (
              <div className="admin-workload-row" key={department.id}>
                <span>{department.name}</span><strong>{department.active_assignments}</strong>
              </div>
            ))}
            {!stats?.department_workload?.length && <p className="admin-empty-note">No department assignments yet.</p>}
          </div>
        </article>
        <article className="content-panel">
          <div className="panel-heading"><div><h2>Officer workload</h2><p>Current active assignments per officer.</p></div></div>
          <div className="admin-workload-list">
            {(stats?.officer_workload || []).map((officer) => (
              <div className="admin-workload-row" key={officer.officer_id}>
                <span><strong>{officer.full_name}</strong><small>{officer.department_name || "No department"}</small></span>
                <strong>{officer.active_assignments}</strong>
              </div>
            ))}
            {!stats?.officer_workload?.length && <p className="admin-empty-note">No active officers available.</p>}
          </div>
        </article>
      </section>

      {assignmentComplaint && (
        <AssignOfficerModal
          complaint={assignmentComplaint}
          onClose={() => setAssignmentComplaint(null)}
          onAssigned={(updatedComplaint) => {
            onComplaintUpdated?.(updatedComplaint);
            setAssignmentComplaint(null);
          }}
        />
      )}
    </main>
  );
}
