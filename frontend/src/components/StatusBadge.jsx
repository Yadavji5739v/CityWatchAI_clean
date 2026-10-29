import React from "react";

const statusStyles = {
  submitted: "cw-status-submitted",
  pending: "cw-status-pending",
  verified: "cw-status-verified",
  assigned: "cw-status-assigned",
  "in progress": "cw-status-progress",
  resolved: "cw-status-resolved",
  rejected: "cw-status-rejected",
};

export default function StatusBadge({ status = "Submitted" }) {
  const key = String(status).toLowerCase();

  return (
    <span
      className={`cw-status ${statusStyles[key] || "cw-status-submitted"}`}
    >
      <span className="cw-status-dot" />
      {status}
    </span>
  );
}