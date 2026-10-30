import { ArrowUpRight, CheckCheck, Clock3, Inbox, MapPin, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";

const views = {
  new: {
    eyebrow: "OFFICER REVIEW QUEUE",
    title: "New Complaints",
    description: "Complaints awaiting officer review and approval. Approve to route them to Pending.",
    icon: Inbox,
    matches: (complaint) =>
      ["Submitted", "Pending Review"].includes(complaint.status),
  },
  pending: {
    eyebrow: "ACTIVE CASES",
    title: "Pending Complaints",
    description: "Approved complaints routed to a department, awaiting assignment or resolution.",
    icon: Clock3,
    matches: (complaint) => ["Verified", "Assigned", "In Progress", "Pending"].includes(complaint.status),
  },
  solved: {
    eyebrow: "COMPLETED CASES",
    title: "Solved Complaints",
    description: "Complaints marked resolved or closed.",
    icon: CheckCheck,
    matches: (complaint) => ["Resolved", "Closed"].includes(complaint.status),
  },
};

export default function OfficerComplaints({ complaints = [], view = "new", loading = false, onRefresh }) {
  const config = views[view] || views.new;
  const Icon = config.icon;
  const filteredComplaints = complaints.filter(config.matches);

  return (
    <main className="page-stack">
      <div className="page-heading">
        <div>
          <div className="eyebrow">{config.eyebrow}</div>
          <h1>{config.title}</h1>
          <p>{config.description}</p>
        </div>
        <span className={`officer-queue-count ${view}`}>
          <Icon size={16} /> {filteredComplaints.length} {filteredComplaints.length === 1 ? "case" : "cases"}
        </span>
        <button className="secondary-button" type="button" onClick={onRefresh} disabled={loading}>
          <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh
        </button>
      </div>

      <section className="content-panel">
        <div className="table-scroll">
          <table className="complaint-table officer-complaint-table">
            <thead>
              <tr>
                <th>Complaint</th>
                <th>Category</th>
                <th>Location</th>
                <th>Department</th>
                <th>Status</th>
                <th>Priority</th>
                <th aria-label="Open complaint" />
              </tr>
            </thead>
            <tbody>
              {filteredComplaints.map((complaint) => (
                <tr key={complaint.id}>
                  <td>
                    <strong>{complaint.title}</strong>
                    <small>{complaint.id} · {complaint.date || complaint.submittedAt || "Recently"}</small>
                  </td>
                  <td>{complaint.category}</td>
                  <td><span className="location-cell"><MapPin size={14} />{complaint.location}</span></td>
                  <td>{complaint.department || (complaint.status === "Pending Review" ? "Awaiting review" : "Awaiting assignment")}</td>
                  <td><span className={`badge ${complaint.status === "Resolved" || complaint.status === "Closed" ? "green" : complaint.status === "In Progress" ? "purple" : "amber"}`}>{complaint.status}</span></td>
                  <td>{complaint.priority}</td>
                  <td>
                    <Link
                      className="officer-open-link"
                      to={`/details/${complaint.id}`}
                      state={{ from: view === "new" ? "/officer/new" : `/officer/${view}` }}
                      aria-label={`View ${complaint.title}`}
                    >
                      View <ArrowUpRight size={14} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {loading ? (
            <div className="empty-state" role="status"><strong>Loading complaints…</strong></div>
          ) : filteredComplaints.length === 0 && (
            <div className="empty-state">
              <Icon size={32} />
              <strong>No {view === "new" ? "new" : view === "pending" ? "pending" : "solved"} complaints</strong>
              <p>Cases matching this queue will appear here.</p>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
