
import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  NavLink,
  Link,
  Navigate,
  useNavigate,
  useLocation,
} from "react-router-dom";
import Login from "./pages/Login";
import { DEMO_ACCOUNTS } from "./lib/demoAccounts";
import Home from "./pages/Home";
import CityDashboard from "./pages/CityDashboard";
import PublicReportWizard from "./pages/PublicReportWizard";
import TrackReport from "./pages/TrackReport";
import HowItWorks from "./pages/HowItWorks";
import SubmitComplaint from "./pages/SubmitComplaint";
import MyComplaints from "./pages/MyComplaints";
import CitizenComplaintProgress from "./pages/CitizenComplaintProgress";
import ComplaintDetails from "./pages/ComplaintDetails";
import OfficerDashboard from "./pages/OfficerDashboard";
import OfficerComplaints from "./pages/OfficerComplaints";
import AssignedComplaints from "./pages/AssignedComplaints";
import AdminDashboard from "./pages/AdminDashboard";
import {
  LayoutDashboard,
  FilePlus2,
  ClipboardList,
  MapPin,
  ArrowUpRight,
  Clock3,
  CheckCircle2,
  AlertTriangle,
  Search,
  Bell,
  ShieldCheck,
  Menu,
  X,
  Inbox,
  CheckCheck,
  Award,
  BadgeCheck,
  Users,
} from "lucide-react";
import "./index.css";
import "./public-site.css";
import Track from "./pages/Track";
import TrackResult from "./pages/TrackResult";
// import {Route } from "react-router-dom";
// import Login from "./pages/Login";
import Signup from "./pages/Signup";
import { API_BASE_URL } from "./lib/api";




function normalizeComplaint(item) {
  const statusValue = item?.status || "Submitted";
  const withdrawnIds = readWithdrawnComplaintIds();
  const complaintId = item?.id || item?.complaint_id || `CW-${Date.now().toString().slice(-6)}`;
  const statusKey = String(statusValue).trim().toLowerCase().replaceAll("_", " ");
  const canonicalStatuses = {
    submitted: "Pending Review",
    "pending review": "Pending Review",
    verified: "Verified",
    assigned: "Assigned",
    pending: "Pending",
    "in progress": "In Progress",
    resolved: "Resolved",
    closed: "Closed",
  };
  const normalizedStatus = withdrawnIds.includes(complaintId)
    ? "Withdrawn"
    : canonicalStatuses[statusKey] || statusValue;

  return {
    ...item,
    id: complaintId,
    title: item?.title || "Untitled complaint",
    category: item?.category || "Other Civic Issue",
    location: item?.location || item?.location_text || "Location not provided",
    videoName: item?.videoName || item?.video_name || "",
    department: item?.department || item?.department_name || item?.assigned_department || "",
    priority: item?.priority || "Needs Review",
    status: normalizedStatus,
    date: item?.date || item?.created_at || "Recently",
    submittedAt: item?.submittedAt || item?.date || item?.created_at || "Recently",
  };
}

function readWithdrawnComplaintIds() {
  try {
    const savedIds = JSON.parse(localStorage.getItem("citywatch_withdrawn_complaints") || "[]");
    return Array.isArray(savedIds) ? savedIds.filter((id) => typeof id === "string") : [];
  } catch (error) {
    console.error("Could not restore withdrawn complaint statuses:", error);
    localStorage.removeItem("citywatch_withdrawn_complaints");
    return [];
  }
}

async function fetchComplaintsFromBackend(token, signal) {
  try {
    const response = await fetch(`${API_BASE_URL}/complaints`, {
      headers: { Authorization: `Bearer ${token}` },
      signal,
    });
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const data = await response.json();
    if (!Array.isArray(data)) {
      return [];
    }

    return data.map(normalizeComplaint);
  } catch (error) {
    console.warn("Could not load complaints from backend:", error);
    return [];
  }
}

function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const [complaints, setComplaints] = useState([]);
  const [complaintsLoading, setComplaintsLoading] = useState(false);
  const [adminStats, setAdminStats] = useState(null);
  const [citizenStats, setCitizenStats] = useState(null);
  const [citizenStatsLoading, setCitizenStatsLoading] = useState(false);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [demoUser, setDemoUser] = useState(() => {
    try {
      const storedUser = localStorage.getItem("citywatch_demo_user");
      const token = localStorage.getItem("citywatch_token");
      return storedUser && token ? JSON.parse(storedUser) : null;
    } catch (error) {
      console.error("Could not restore the demo account:", error);
      localStorage.removeItem("citywatch_demo_user");
      return null;
    }
  });

  useEffect(() => {
    if (!demoUser?.id) {
      setComplaints([]);
      setAdminStats(null);
      setCitizenStats(null);
      setComplaintsLoading(false);
      return undefined;
    }

    let isMounted = true;
    const controller = new AbortController();

    async function loadComplaints() {
      const token = localStorage.getItem("citywatch_token");
      if (!token) return;
      setComplaintsLoading(true);
      try {
        const statsRequest = demoUser.role === "admin"
          ? fetch(`${API_BASE_URL}/dashboard/admin`, {
              headers: { Authorization: `Bearer ${token}` },
              signal: controller.signal,
            }).then(async (response) => {
              if (!response.ok) throw new Error(`Admin dashboard request failed (${response.status}).`);
              return response.json();
            }).catch((error) => {
              if (!controller.signal.aborted) console.error("Could not load administrator statistics:", error);
              return null;
            })
          : Promise.resolve(null);
        const [backendComplaints, stats] = await Promise.all([
          fetchComplaintsFromBackend(token, controller.signal),
          statsRequest,
        ]);
        if (isMounted) {
          setComplaints(backendComplaints);
          setAdminStats(stats);
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          console.error("Could not load CityWatch workspace data:", error);
        }
      } finally {
        if (isMounted) setComplaintsLoading(false);
      }
    }

    loadComplaints();
    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [demoUser?.id, demoUser?.role]);

  useEffect(() => {
    if (demoUser?.role !== "citizen" || location.pathname !== "/dashboard") {
      setCitizenStatsLoading(false);
      return undefined;
    }
    const controller = new AbortController();
    const token = localStorage.getItem("citywatch_token");
    if (!token) return undefined;
    setCitizenStatsLoading(true);
    fetch(`${API_BASE_URL}/dashboard/citizen`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Citizen dashboard data could not be loaded.");
        setCitizenStats(data);
      })
      .catch((error) => {
        if (!controller.signal.aborted) console.error("Could not load citizen dashboard data:", error);
      })
      .finally(() => {
        if (!controller.signal.aborted) setCitizenStatsLoading(false);
      });
    return () => controller.abort();
  }, [demoUser?.id, demoUser?.role, location.pathname]);

  async function refreshComplaints() {
    const token = localStorage.getItem("citywatch_token");
    if (!token) return;
    setComplaintsLoading(true);
    try {
      const backendComplaints = await fetchComplaintsFromBackend(token);
      setComplaints(backendComplaints);
    } finally {
      setComplaintsLoading(false);
    }
  }

  async function handleDemoLogin(accountId, password) {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: accountId, password }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Sign in failed. Check your ID and password.");
    }

    const user = data.user;
    localStorage.setItem("citywatch_token", data.access_token);
    localStorage.setItem("citywatch_demo_user", JSON.stringify(user));
    setDemoUser(user);
    const destination = DEMO_ACCOUNTS.find((account) => account.role === user.role)?.destination || "/";
    navigate(destination, { replace: true });
  }

  async function handleSignup(signupDetails) {
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(signupDetails),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Account creation failed. Please try again.");
    }

    localStorage.setItem("citywatch_token", data.access_token);
    localStorage.setItem("citywatch_demo_user", JSON.stringify(data.user));
    setDemoUser(data.user);
    navigate("/dashboard", { replace: true });
  }

  async function handleLogout() {
    localStorage.removeItem("citywatch_demo_user");
    localStorage.removeItem("citywatch_token");
    setDemoUser(null);
    setComplaints([]);
    navigate("/", { replace: true });
  }

  function addComplaint(complaint) {
    const nextComplaint = normalizeComplaint(complaint);
    setComplaints((previous) => [nextComplaint, ...previous]);
  }

  function updateComplaint(updatedComplaint) {
    const normalized = normalizeComplaint(updatedComplaint);
    setComplaints((previous) =>
      previous.map((complaint) => complaint.id === normalized.id ? normalized : complaint),
    );
    // Always refresh from backend so status transitions (e.g. officer approval → Verified → Pending)
    // are reflected immediately across all views.
    refreshComplaints();
    if (demoUser?.role === "admin") {
      const token = localStorage.getItem("citywatch_token");
      fetch(`${API_BASE_URL}/dashboard/admin`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then(async (response) => {
          const data = await response.json();
          if (!response.ok) throw new Error(data.detail || "Dashboard statistics refresh failed.");
          setAdminStats(data);
        })
        .catch((error) => console.error("Could not refresh administrator statistics:", error));
    }
  }

  function withdrawComplaint(complaintId) {
    const withdrawnIds = readWithdrawnComplaintIds();
    try {
      localStorage.setItem(
        "citywatch_withdrawn_complaints",
        JSON.stringify(withdrawnIds.includes(complaintId) ? withdrawnIds : [...withdrawnIds, complaintId]),
      );
    } catch (error) {
      console.error("Could not save withdrawn complaint status:", error);
      return false;
    }

    setComplaints((previous) =>
      previous.map((complaint) =>
        complaint.id === complaintId ? { ...complaint, status: "Withdrawn" } : complaint,
      ),
    );
    return true;
  }

  const newOfficerComplaints = complaints.filter((item) =>
    ["Submitted", "Pending Review"].includes(item.status)
  ).length;
  const navItems = demoUser?.role === "officer"
    ? [
        { to: "/officer", label: "Dashboard", icon: LayoutDashboard, end: true },
        { to: "/officer/new", label: "New Complaints", icon: Inbox, count: newOfficerComplaints },
        { to: "/officer/assigned", label: "Assigned Complaints", icon: ClipboardList },
        { to: "/officer/pending", label: "Pending Complaints", icon: Clock3 },
        { to: "/officer/solved", label: "Solved Complaints", icon: CheckCheck },
      ]
    : demoUser?.role === "admin"
      ? [
          { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
          { to: "/admin/complaints", label: "All Complaints", icon: ClipboardList, count: complaints.length },
        ]
      : [
          { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, end: true },
          { to: "/report", label: "Report a Problem", icon: FilePlus2 },
          { to: "/my-complaints", label: "My Complaints", icon: Search },
        ];

  if (["/", "/how-it-works", "/login", "/signup", "/city-dashboard", "/report", "/track-report"].includes(location.pathname) && !demoUser) {
    return (
      <div className="public-site">
        <PublicNavbar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="/login" element={<Login onLogin={handleDemoLogin} onSignup={() => navigate("/signup")} />} />
          <Route path="/signup" element={<Signup onSignup={handleSignup} />} />
          <Route path="/city-dashboard" element={<CityDashboard />} />
          <Route path="/report" element={<PublicReportWizard />} />
          <Route path="/track-report" element={<Track />} />
          <Route path="/track-report/result" element={<TrackResult />} />
        </Routes>
        <PublicFooter />
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileMenu ? "sidebar-open" : ""}`}>
        <Link to="/" className="brand" onClick={() => setMobileMenu(false)}>
          <span className="brand-mark">
            <ShieldCheck size={25} />
          </span>
          <span>
            <strong>CityWatch <span>AI</span></strong>
            <small>SMART CIVIC RESPONSE</small>
          </span>
        </Link>

        <div className="nav-label">{demoUser?.role ? `${demoUser.role.toUpperCase()} WORKSPACE` : "WORKSPACE"}</div>
        <nav className="sidebar-nav">
          {navItems.map(({ to, label, icon: Icon, end, count }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setMobileMenu(false)}
              className={({ isActive }) =>
                `nav-link ${isActive ? "active" : ""}`
              }
            >
              <Icon size={19} />
              <span>{label}</span>
              {count !== undefined && (
                <span className="nav-count">{count}</span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-tip">
            <ShieldCheck size={22} />
            <strong>Better cities start here.</strong>
            <p>Report civic problems and follow them through resolution.</p>
          </div>
          <div className="profile">
            <div className="avatar">CW</div>
            <div>
              <strong>{demoUser?.name || "Demo visitor"}</strong>
              <small>{demoUser?.role ? `${demoUser.role} demo` : "Demo workspace"}</small>
            </div>
            <span className="online-dot" />
          </div>
        </div>
      </aside>

      {mobileMenu && (
        <button
          className="mobile-overlay"
          onClick={() => setMobileMenu(false)}
          aria-label="Close menu"
        />
      )}

      <main className="main-area">
        <header className="topbar">
          <button
            className="icon-button mobile-toggle"
            onClick={() => setMobileMenu(!mobileMenu)}
            aria-label="Toggle navigation"
          >
            {mobileMenu ? <X size={21} /> : <Menu size={21} />}
          </button>
          <div className="breadcrumb">
            <span>CityWatch AI</span>
            <span className="breadcrumb-divider">/</span>
            <strong>Civic Intelligence</strong>
          </div>
          <div className="topbar-right">
            {demoUser ? (
              <div className="demo-session-controls">
                <span className="demo-session-label">{demoUser.name}</span>
                <button type="button" className="secondary-button small" onClick={handleLogout}>
                  Sign out
                </button>
              </div>
            ) : (
              <Link to="/login" className="primary-button small">Log in</Link>
            )}
            <span className="system-status">
              <span className="status-dot" /> Demo Environment
            </span>
            <button className="icon-button" aria-label="Notifications">
              <Bell size={19} />
            </button>
          </div>
        </header>

        <div className="page-content">
          <Routes>
            <Route path="/dashboard" element={
              <DemoRoleRoute user={demoUser} allow={["citizen"]}>
                <Dashboard complaints={complaints} loading={complaintsLoading} points={citizenStats?.points} pointsLoading={citizenStatsLoading} />
              </DemoRoleRoute>
            } />
            <Route path="/report" element={
              <DemoRoleRoute user={demoUser} allow={["citizen"]}>
                <SubmitComplaint onSubmit={addComplaint} />
              </DemoRoleRoute>
            } />
            <Route path="/complaints" element={
              <DemoRoleRoute user={demoUser} allow={["citizen"]}>
                <ComplaintsPage complaints={complaints} loading={complaintsLoading} />
              </DemoRoleRoute>
            } />
            <Route path="/my-complaints" element={
              <DemoRoleRoute user={demoUser} allow={["citizen"]}>
                <MyComplaints complaints={complaints} loading={complaintsLoading} onWithdraw={withdrawComplaint} />
              </DemoRoleRoute>
            } />
            <Route path="/my-complaints/:id" element={
              <DemoRoleRoute user={demoUser} allow={["citizen"]}>
                <CitizenComplaintProgress complaints={complaints} />
              </DemoRoleRoute>
            } />
            <Route path="/details/:id" element={
              <DemoRoleRoute user={demoUser} allow={["citizen", "officer", "admin"]}>
                <ComplaintDetails complaints={complaints} user={demoUser} onComplaintUpdated={updateComplaint} onRefresh={refreshComplaints} />
              </DemoRoleRoute>
            } />
            <Route
              path="/officer"
              element={
                <DemoRoleRoute user={demoUser} allow={["officer"]}>
                  <OfficerDashboard complaints={complaints} loading={complaintsLoading} />
                </DemoRoleRoute>
              }
            />
            <Route path="/officer/new" element={
              <DemoRoleRoute user={demoUser} allow={["officer"]}>
                <OfficerComplaints complaints={complaints} view="new" loading={complaintsLoading} onRefresh={refreshComplaints} />
              </DemoRoleRoute>
            } />
            <Route path="/officer/assigned" element={
              <DemoRoleRoute user={demoUser} allow={["officer"]}>
                <AssignedComplaints />
              </DemoRoleRoute>
            } />
            <Route path="/officer/pending" element={
              <DemoRoleRoute user={demoUser} allow={["officer"]}>
                <OfficerComplaints complaints={complaints} view="pending" loading={complaintsLoading} onRefresh={refreshComplaints} />
              </DemoRoleRoute>
            } />
            <Route path="/officer/solved" element={
              <DemoRoleRoute user={demoUser} allow={["officer"]}>
                <OfficerComplaints complaints={complaints} view="solved" loading={complaintsLoading} onRefresh={refreshComplaints} />
              </DemoRoleRoute>
            } />
            <Route
              path="/admin"
              element={
                <DemoRoleRoute user={demoUser} allow={["admin"]}>
                  <AdminDashboard
                    complaints={complaints}
                    stats={adminStats}
                    loading={complaintsLoading}
                    onComplaintUpdated={updateComplaint}
                  />
                </DemoRoleRoute>
              }
            />
            <Route path="/admin/complaints" element={
              <DemoRoleRoute user={demoUser} allow={["admin"]}>
                <ComplaintsPage complaints={complaints} isAdmin loading={complaintsLoading} />
              </DemoRoleRoute>
            } />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

function PageHeading({ eyebrow, title, description, action }) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}

function Dashboard({ complaints, loading = false, points, pointsLoading = false }) {
  const pending = complaints.filter(
    (item) => item.status === "Pending Review"
  ).length;
  const active = complaints.filter(
    (item) => ["Assigned", "In Progress"].includes(item.status)
  ).length;
  const resolved = complaints.filter(
    (item) => item.status === "Resolved"
  ).length;

  const stats = [
    {
      label: "Total Complaints",
      value: complaints.length,
      icon: ClipboardList,
      color: "blue",
      note: "All submitted reports",
    },
    {
      label: "Pending Review",
      value: pending,
      icon: Clock3,
      color: "amber",
      note: "Awaiting verification",
    },
    {
      label: "In Progress",
      value: active,
      icon: AlertTriangle,
      color: "purple",
      note: "Assigned to departments",
    },
    {
      label: "Resolved",
      value: resolved,
      icon: CheckCircle2,
      color: "green",
      note: "Successfully closed",
    },
  ];

  return (
    <>
      <PageHeading
        eyebrow="OVERVIEW"
        title="Civic Intelligence Dashboard"
        description="Monitor reported issues and follow complaints through resolution."
        action={
          <Link className="primary-button" to="/report">
            <FilePlus2 size={17} /> Report a Problem
          </Link>
        }
      />

      <section className="welcome-banner">
        <div className="welcome-copy">
          <span className="welcome-tag">
            <ShieldCheck size={14} /> CITIZEN-POWERED GOVERNANCE
          </span>
          <h2>Let's make our city better.</h2>
          <p>
            Report a civic problem with video evidence. CityWatch AI helps
            organize, analyze and track your complaint.
          </p>
          <Link to="/report" className="banner-button">
            Submit a complaint <ArrowUpRight size={17} />
          </Link>
        </div>
        <div className="banner-art" aria-hidden="true">
          <div className="art-circle">
            <MapPin size={46} />
          </div>
          <div className="art-card">
            <span className="status-dot" /> Civic issues, organized
          </div>
        </div>
      </section>

      <section className="stats-grid">
        {stats.map(({ label, value, icon: Icon, color, note }) => (
          <article className="stat-card" key={label}>
            <div className={`stat-icon ${color}`}>
              <Icon size={21} />
            </div>
            <div className="stat-label">{label}</div>
            <div className="stat-value">{loading ? "…" : value}</div>
            <div className="stat-note">{note}</div>
          </article>
        ))}
      </section>

      <section className="content-panel contribution-points-panel" aria-labelledby="contribution-points-title">
        <div className="points-score-block">
          <span className="points-award-icon"><Award size={22} /></span>
          <div>
            <div className="eyebrow">CITIZEN CONTRIBUTION</div>
            <h2 id="contribution-points-title">Your impact points</h2>
            <p>Points recognize reports that staff verify and citizens who support an existing issue.</p>
          </div>
          <div className="points-total" aria-live="polite">
            <strong>{pointsLoading ? "…" : points?.total ?? 0}</strong><span>points</span>
          </div>
        </div>
        <div className="points-breakdown">
          <div><BadgeCheck size={17} /><span><strong>{pointsLoading ? "…" : points?.verified_reports ?? 0}</strong> verified reports <small>20 points each</small></span></div>
          <div><Users size={17} /><span><strong>{pointsLoading ? "…" : points?.supported_reports ?? 0}</strong> reports supporting an existing issue <small>5 points each</small></span></div>
        </div>
        <p className="points-rule-note">Reports earn points after verification. Reports awaiting review do not earn points yet.</p>
      </section>

      <section className="content-panel">
        <div className="panel-heading">
          <div>
            <h2>Recent Complaints</h2>
            <p>Latest reports submitted to CityWatch AI</p>
          </div>
          <Link to="/complaints" className="text-link">
            View all <ArrowUpRight size={15} />
          </Link>
        </div>
        <ComplaintTable complaints={complaints.slice(0, 5)} loading={loading} />
      </section>

      <div className="disclaimer">
        <ShieldCheck size={17} />
        <span>
          Your reports are saved to CityWatch. AI analysis supports human review and does not replace it.
        </span>
      </div>
    </>
  );
}

function ComplaintsPage({ complaints, isAdmin = false, loading = false }) {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("All");

  const filtered = complaints.filter((item) => {
    const query = search.toLowerCase();
    const matchesSearch =
      item.id.toLowerCase().includes(query) ||
      item.title.toLowerCase().includes(query) ||
      item.location.toLowerCase().includes(query);
    const matchesStatus = status === "All" || item.status === status;
    return matchesSearch && matchesStatus;
  });

  return (
    <>
      <PageHeading
        eyebrow={isAdmin ? "ADMINISTRATION" : "CASE MANAGEMENT"}
        title={isAdmin ? "All Complaints" : "Complaints"}
        description={isAdmin ? "Review all submitted civic reports." : "Review reports and follow their current status."}
        action={!isAdmin && (
          <Link className="primary-button" to="/report">
            <FilePlus2 size={17} /> New Complaint
          </Link>
        )}
      />

      <section className="content-panel">
        <div className="filter-bar">
          <div className="search-box">
            <Search size={18} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search complaints..."
            />
          </div>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option>All</option>
            <option>Pending Review</option>
            <option>Assigned</option>
            <option>In Progress</option>
            <option>Resolved</option>
          </select>
        </div>
        <ComplaintTable complaints={filtered} loading={loading} />
        {!loading && filtered.length === 0 && (
          <div className="empty-state">
            <ClipboardList size={32} />
            <strong>No complaints found</strong>
            <p>Try changing your search or status filter.</p>
          </div>
        )}
      </section>
    </>
  );
}

function ComplaintTable({ complaints, loading = false }) {
  if (loading && complaints.length === 0) {
    return <div className="empty-state" role="status"><strong>Loading complaints…</strong></div>;
  }
  if (complaints.length === 0) {
    return (
      <div className="empty-state">
        <ClipboardList size={32} />
        <strong>No complaints submitted yet</strong>
        <p>New reports will appear here.</p>
      </div>
    );
  }

  return (
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
              <td><span className="location-cell"><MapPin size={14} />{item.location}</span></td>
              <td><StatusBadge value={item.priority} /></td>
              <td><StatusBadge value={item.status} /></td>
              <td>{item.date}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusBadge({ value }) {
  let style = "neutral";
  if (["High", "Pending Review"].includes(value)) style = "amber";
  if (["Medium", "Assigned"].includes(value)) style = "blue";
  if (["Low", "Resolved"].includes(value)) style = "green";
  if (value === "In Progress") style = "purple";

  return <span className={`badge ${style}`}>{value}</span>;
}

function NotFound() {
  return (
    <div className="empty-state">
      <h2>Page not found</h2>
      <Link to="/dashboard" className="text-link">Return to dashboard</Link>
    </div>
  );
}

function PublicNavbar() {
  const [menuOpen, setMenuOpen] = useState(false);

  function closeMenu() {
    setMenuOpen(false);
  }

  return (
    <header className="public-header">
      <div className="public-header-inner">
        <Link className="public-brand" to="/" onClick={closeMenu} aria-label="CityWatch AI home">
          <span className="public-brand-icon"><ShieldCheck size={22} /></span>
          <span className="public-brand-name">CityWatch <b>AI</b></span>
        </Link>
        <button
          type="button"
          className="public-menu-toggle"
          onClick={() => setMenuOpen((open) => !open)}
          aria-expanded={menuOpen}
          aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
        >
          {menuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
        <nav className={`public-nav ${menuOpen ? "public-nav-open" : ""}`} aria-label="Main navigation">
          <Link to="/" onClick={closeMenu}>Home</Link>
          <Link to="/how-it-works" onClick={closeMenu}>How it works</Link>
          <Link to="/track-report">Track Report</Link>
          <Link to="/city-dashboard" className="public-nav-dashboard" onClick={closeMenu}>Dashboard</Link>
          <Link to="/login" className="public-nav-cta" onClick={closeMenu}>
            Log in / Sign up <ArrowUpRight size={16} />
          </Link>
        </nav>
      </div>
    </header>
  );
}

function DemoRoleRoute({ user, allow, children }) {
  const location = useLocation();

  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location }}
      />
    );
  }
  if (!allow.includes(user.role)) {
    const destination =
      DEMO_ACCOUNTS.find((account) => account.role === user.role)?.destination || "/";
    return <Navigate to={destination} replace />;
  }

  return children;
}

function PublicFooter() {
  return (
    <footer className="public-footer">
      <div className="public-footer-inner">
        <Link className="public-brand" to="/">
          <span className="public-brand-icon"><ShieldCheck size={20} /></span>
          <span className="public-brand-name">CityWatch <b>AI</b></span>
        </Link>
        <p>Smarter Cities. Faster Solutions.</p>
        <span>Built for clearer civic reporting and follow-through.</span>
      </div>
    </footer>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}
