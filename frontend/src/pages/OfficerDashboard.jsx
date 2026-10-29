import { AlertTriangle, ArrowRight, CheckCheck, Clock3, Inbox, MapPin } from "lucide-react";
import { Link } from "react-router-dom";

const demoTasks = [
  { id: "CW-1010", title: "Broken drain near school", priority: "High", status: "Assigned" },
  { id: "CW-1011", title: "Illegal vehicle parking", priority: "Medium", status: "In Progress" },
  { id: "CW-1012", title: "Streetlight outage", priority: "High", status: "Waiting for evidence" },
];

export default function OfficerDashboard({ complaints = demoTasks }) {
  const newComplaints = complaints.filter((item) =>
    ["Submitted", "Pending Review"].includes(item.status)
  );
  const pendingComplaints = complaints.filter((item) =>
    ["Verified", "Assigned", "In Progress", "Pending"].includes(item.status)
  );
  const solvedComplaints = complaints.filter((item) => ["Resolved", "Closed"].includes(item.status));

  return (
    <main className="page-stack">
      <div className="page-heading">
        <div>
          <div className="eyebrow">OFFICER WORKSPACE</div>
          <h1>Officer dashboard</h1>
          <p>Review new reports, monitor assigned work, and track solved complaints.</p>
        </div>
      </div>

      <section className="stats-grid">
        <article className="stat-card">
          <div className="stat-icon blue"><Inbox size={20} /></div>
          <div className="stat-label">New complaints</div>
          <div className="stat-value">{newComplaints.length}</div>
          <Link to="/officer/new" className="officer-stat-link">Review queue <ArrowRight size={14} /></Link>
        </article>
        <article className="stat-card">
          <div className="stat-icon amber"><Clock3 size={20} /></div>
          <div className="stat-label">Pending complaints</div>
          <div className="stat-value">{pendingComplaints.length}</div>
          <Link to="/officer/pending" className="officer-stat-link">View assigned work <ArrowRight size={14} /></Link>
        </article>
        <article className="stat-card">
          <div className="stat-icon green"><CheckCheck size={20} /></div>
          <div className="stat-label">Solved complaints</div>
          <div className="stat-value">{solvedComplaints.length}</div>
          <Link to="/officer/solved" className="officer-stat-link">View completed <ArrowRight size={14} /></Link>
        </article>
        <article className="stat-card">
          <div className="stat-icon purple"><AlertTriangle size={20} /></div>
          <div className="stat-label">High priority</div>
          <div className="stat-value">{complaints.filter((item) => item.priority === "High").length}</div>
          <div className="stat-note">Across available complaints</div>
        </article>
      </section>

      <section className="content-panel">
        <div className="panel-heading">
          <div>
            <h2>Pending complaints</h2>
            <p>Assigned cases and the department responsible for each one</p>
          </div>
          <Link to="/officer/pending" className="text-link">View all <ArrowRight size={14} /></Link>
        </div>

        <div className="table-scroll">
          <table className="complaint-table">
            <thead>
              <tr>
                <th>Complaint</th>
                <th>Department</th>
                <th>Status</th>
                <th>Location</th>
              </tr>
            </thead>
            <tbody>
              {pendingComplaints.slice(0, 5).map((item) => (
                <tr key={item.id || item.title}>
                  <td>
                    <strong>{item.title}</strong>
                    <small>{item.id}</small>
                  </td>
                  <td>{item.department || "Awaiting assignment"}</td>
                  <td>{item.status}</td>
                  <td><span className="location-cell"><MapPin size={14} /> {item.location || "Ward 4"}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          {pendingComplaints.length === 0 && (
            <div className="empty-state">
              <Clock3 size={30} />
              <strong>No pending complaints</strong>
              <p>Assigned cases that need work will appear here.</p>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
