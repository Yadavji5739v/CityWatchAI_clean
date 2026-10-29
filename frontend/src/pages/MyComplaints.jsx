import { CircleX, Eye, FilePlus2, MapPin } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

const demoComplaints = [
  { id: "CW-1001", title: "Pothole near the bus stop", category: "Road Damage", status: "Pending Review", priority: "High", location: "Main Road, Ward 4", date: "Today" },
  { id: "CW-1002", title: "Overflowing garbage bin", category: "Sanitation", status: "Assigned", priority: "Medium", location: "Market Street", date: "Yesterday" },
  { id: "CW-1003", title: "Streetlight not working", category: "Streetlight", status: "In Progress", priority: "Medium", location: "Hill Avenue", date: "2 days ago" },
];

function isWithdrawable(status) {
  return ["submitted", "pending", "pending review", "pending_review"].includes(
    String(status).toLowerCase(),
  );
}

export default function MyComplaints({ complaints = demoComplaints, onWithdraw }) {
  const [error, setError] = useState("");

  function handleWithdraw(complaint) {
    if (!window.confirm(`Withdraw complaint ${complaint.id}? This will mark it as withdrawn.`)) {
      return;
    }

    setError("");
    if (!onWithdraw?.(complaint.id)) {
      setError("Could not save this withdrawal in the browser. Please check storage settings and try again.");
    }
  }

  return (
    <main className="page-stack">
      <div className="page-heading">
        <div>
          <div className="eyebrow">MY REPORTS</div>
          <h1>Complaint tracker</h1>
          <p>Review your citizen submissions and their current resolution status.</p>
        </div>
        <Link to="/report" className="primary-button">
          <FilePlus2 size={17} /> New Complaint
        </Link>
      </div>

      <section className="content-panel">
        <div className="table-scroll">
          <table className="complaint-table">
            <thead>
              <tr>
                <th>Complaint</th>
                <th>Category</th>
                <th>Location</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Date</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {complaints.map((item) => (
                <tr key={item.id}>
                  <td>
                    <strong>{item.title}</strong>
                    <small>{item.id}</small>
                  </td>
                  <td>{item.category}</td>
                  <td>
                    <span className="location-cell">
                      <MapPin size={14} /> {item.location || "Location not specified"}
                    </span>
                  </td>
                  <td>{item.priority}</td>
                  <td>
                    <span className={`badge ${item.status === "Withdrawn" ? "neutral" : item.status === "Resolved" ? "green" : "amber"}`}>
                      {item.status}
                    </span>
                  </td>
                  <td>{item.date || item.submittedAt || "Recently"}</td>
                  <td>
                    {isWithdrawable(item.status) ? <button
                      type="button"
                      className="withdraw-button"
                      onClick={() => handleWithdraw(item)}
                      disabled={!isWithdrawable(item.status)}
                      title={isWithdrawable(item.status) ? "Withdraw this complaint" : "Complaints can only be withdrawn before they are assigned"}
                    >
                      <CircleX size={15} />
                      {item.status === "Withdrawn" ? "Withdrawn" : "Withdraw"}
                    </button> : <Link className="progress-view-button" to={`/my-complaints/${item.id}`}><Eye size={15} /> View progress</Link>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {complaints.length === 0 && (
            <div className="empty-state">
              <strong>No complaints yet</strong>
              <p>Your submitted reports will appear here.</p>
            </div>
          )}
        </div>
        {error && <div className="form-error withdraw-error" role="alert">{error}</div>}
        <p className="withdraw-note">You can withdraw a complaint before it is assigned. Withdrawn complaints remain in your history.</p>
      </section>
    </main>
  );
}
