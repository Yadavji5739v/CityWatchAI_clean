import { useState } from "react";
import { Check, Search } from "lucide-react";

const stages = ["Submitted", "Under Review", "Assigned to Department", "Work in Progress", "Resolved"];
export default function TrackReport() {
  const [reportId, setReportId] = useState("CW-2026-00123");
  const [trackedId, setTrackedId] = useState("CW-2026-00123");
  return <main className="public-main track-reference-page"><section className="track-card"><h1>Track Your Report</h1><p>Enter your report ID to see the latest status.</p><form onSubmit={(event) => { event.preventDefault(); setTrackedId(reportId || "CW-2026-00123"); }}><Search size={17} /><input value={reportId} onChange={(event) => setReportId(event.target.value)} placeholder="e.g. CW-2026-00123" /><button>Track</button></form><section className="tracked-report"><header><strong>{trackedId}</strong><span>Resolved</span></header><ol>{stages.map((stage, index) => <li key={stage}><i>{index === 4 ? <Check size={13} /> : index + 1}</i><div><strong>{stage}</strong><small>Oct {12 + index}, 2026 · {index + 10}:24 AM</small><p>{index === 0 ? "Your report has been received." : index === 4 ? "The issue has been resolved." : "Your report is moving through the city response process."}</p></div></li>)}</ol><div className="before-after"><div><small>Before</small><span>Reported road issue</span></div><b>→</b><div><small>After — Fixed</small><span>Department resolution</span></div></div></section></section></main>;
}
