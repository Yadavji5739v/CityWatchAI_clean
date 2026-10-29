
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  Clock3,
  FileText,
  Filter,
  LayoutDashboard,
  MapPin,
  Search,
  ShieldCheck,
  Users,
  Eye,
  Construction,
  Trash2,
  Waves,
  Lightbulb,
  HelpCircle,
} from "lucide-react";
import { Link } from "react-router-dom";
import "./CityDashboardImpact.css";

const reports = [
  {
    id: "CW-2026-00123",
    title: "Pothole near main gate",
    category: "Potholes",
    status: "Pending",
    place: "BFCET, Bathinda",
    days: 2,
    x: 24,
    y: 30,
  },
  {
    id: "CW-2026-00118",
    title: "Overflowing garbage bin",
    category: "Garbage",
    status: "In Progress",
    place: "Handiaya Road",
    days: 6,
    x: 61,
    y: 43,
  },
  {
    id: "CW-2026-00115",
    title: "Broken streetlight",
    category: "Streetlights",
    status: "Resolved",
    place: "College Road",
    days: 12,
    x: 48,
    y: 71,
  },
  {
    id: "CW-2026-00109",
    title: "Open manhole",
    category: "Drainage",
    status: "Under Review",
    place: "Model Town",
    days: 18,
    x: 79,
    y: 25,
  },
  {
    id: "CW-2026-00105",
    title: "Road crack at bus stand",
    category: "Road Cracks",
    status: "Resolved",
    place: "Bus Stand Road",
    days: 26,
    x: 16,
    y: 61,
  },
  {
    id: "CW-2026-00098",
    title: "Fallen roadside tree",
    category: "Environment",
    status: "Resolved",
    place: "Green Park",
    days: 29,
    x: 70,
    y: 77,
  },
];

const colors = {
  Potholes: "#3678ed",
  Garbage: "#20b883",
  Drainage: "#e9a822",
  Streetlights: "#9657dc",
  "Road Cracks": "#e85b65",
  Environment: "#25ad7d",
};

const categoryIcons = {
  Potholes: Construction,
  Garbage: Trash2,
  Drainage: Waves,
  Streetlights: Lightbulb,
  "Road Cracks": Construction,
  Environment: Waves,
};

const navItems = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "reports", label: "All Reports", icon: FileText },
  { id: "map", label: "Map View", icon: MapPin },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "my-reports", label: "My Reports", icon: Users },
];

const pageTitles = {
  overview: "City Dashboard",
  reports: "All Reports",
  map: "Report Map",
  analytics: "Analytics & Insights",
  "my-reports": "My Reports",
};

const pageDescriptions = {
  overview:
    "A quick overview of civic reports and their current status.",
  reports:
    "Search, filter, and review reported civic issues.",
  map:
    "Explore report locations and select a marker to track an issue.",
  analytics:
    "Understand report categories and their distribution.",
  "my-reports":
    "Review reports associated with your account.",
};

function StatusBadge({ status }) {
  const className = status.toLowerCase().replaceAll(" ", "-");

  return (
    <span className={`cw-status-badge ${className}`}>
      <i />
      {status}
    </span>
  );
}

function PanelHeading({ title, description, icon: Icon, tone = "" }) {
  return (
    <div className="cw-panel-heading">
      <div>
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>

      {Icon && (
        <span className={`cw-panel-icon ${tone}`}>
          <Icon size={19} />
        </span>
      )}
    </div>
  );
}

function EmptyState({ title, description }) {
  return (
    <div className="cw-empty-table">
      <Search size={25} />
      <strong>{title}</strong>
      <span>{description}</span>
    </div>
  );
}

function AnimatedNumber({ value, duration = 5000, decimals = 0, suffix = "" }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let frameId;
    let startTime;

    const animate = (timestamp) => {
      if (startTime === undefined) startTime = timestamp;

      const progress = Math.min((timestamp - startTime) / duration, 1);
      const easedProgress = 1 - Math.pow(1 - progress, 3);

      setCount(value * easedProgress);

      if (progress < 1) {
        frameId = requestAnimationFrame(animate);
      } else {
        setCount(value);
      }
    };

    frameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameId);
  }, [value, duration]);

  return (
    <span>
      {count.toLocaleString("en-IN", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}
      {suffix}
    </span>
  );
}

export default function CityDashboard() {
  const [activeTab, setActiveTab] = useState("overview");
  const [period, setPeriod] = useState(30);
  const [category, setCategory] = useState("All");
  const [search, setSearch] = useState("");

  // Filter reports using the selected date range, category, and search text.
  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();

    return reports.filter((report) => {
      const matchesPeriod = report.days <= period;

      const matchesCategory =
        category === "All" || report.category === category;

      const matchesSearch =
        !query ||
        report.title.toLowerCase().includes(query) ||
        report.id.toLowerCase().includes(query) ||
        report.place.toLowerCase().includes(query) ||
        report.category.toLowerCase().includes(query) ||
        report.status.toLowerCase().includes(query);

      return matchesPeriod && matchesCategory && matchesSearch;
    });
  }, [period, category, search]);

  const totals = useMemo(
    () => ({
      total: filtered.length,
      pending: filtered.filter((report) =>
        ["Pending", "Under Review"].includes(report.status)
      ).length,
      inProgress: filtered.filter(
        (report) => report.status === "In Progress"
      ).length,
      resolved: filtered.filter(
        (report) => report.status === "Resolved"
      ).length,
    }),
    [filtered]
  );

  const breakdown = useMemo(() => {
    const counts = Object.keys(colors).map((name) => ({
      name,
      count: filtered.filter((report) => report.category === name).length,
    }));

    return counts.filter((item) => item.count > 0);
  }, [filtered]);

  const donutGradient = useMemo(() => {
    if (filtered.length === 0) return "#edf1f7";

    let current = 0;

    const segments = breakdown.map(({ name, count }) => {
      const start = current;
      current += (count / filtered.length) * 100;

      return `${colors[name]} ${start}% ${current}%`;
    });

    return `conic-gradient(${segments.join(", ")})`;
  }, [breakdown, filtered.length]);

  const averageResolution = useMemo(() => {
    const resolved = filtered.filter(
      (report) => report.status === "Resolved"
    );

    if (!resolved.length) return null;

    const average =
      resolved.reduce((sum, report) => sum + report.days, 0) /
      resolved.length;

    return `${average.toFixed(1)} days`;
  }, [filtered]);

  function changeTab(tab) {
    setActiveTab(tab);
    setSearch("");
    setCategory("All");

    // Reset to the top without navigating to a page anchor.
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <main className="public-main cw-dashboard-page">
      <section className="cw-dashboard-shell">
        {/* Sidebar */}
        <aside className="cw-sidebar">
          <Link
            to="/"
            className="cw-sidebar-brand"
            aria-label="CityWatch AI home"
          >
            <span className="cw-brand-mark">
              <ShieldCheck size={23} />
            </span>

            <span>
              CityWatch <b>AI</b>
              <small>CIVIC MANAGEMENT</small>
            </span>
          </Link>

          <p className="cw-nav-label">WORKSPACE</p>

            
<nav className="cw-sidebar-nav" aria-label="Dashboard navigation">
  {navItems.map((item) => {
    const Icon = item.icon;
    const isActive = activeTab === item.id;

    return (
      <button
        key={item.id}
        type="button"
        className={isActive ? "active" : ""}
        aria-current={isActive ? "page" : undefined}
        onClick={() => setActiveTab(item.id)}
      >
        <Icon size={19} />
        <span>{item.label}</span>

        {item.id === "reports" && (
          <span className="cw-nav-count">{reports.length}</span>
        )}
      </button>
    );
  })}
</nav>


          <div className="cw-sidebar-bottom">
            <div className="cw-help-card">
              <span className="cw-help-icon">
                <HelpCircle size={19} />
              </span>

              <strong>Need assistance?</strong>

              <p>
                Find out how to submit an issue and follow its progress.
              </p>

              <Link to="/how-it-works">
                How it works <ArrowRight size={13} />
              </Link>
            </div>

            <Link to="/" className="cw-sidebar-home">
              <ChevronRight size={15} />
              Back to homepage
            </Link>
          </div>
        </aside>

        {/* Dashboard content */}
        <section className="cw-dashboard-main">
          <header className="cw-topbar">
            <div className="cw-breadcrumb">
              <span>Workspace</span>
              <ChevronRight size={13} />
              <strong>{pageTitles[activeTab]}</strong>
            </div>

            <div className="cw-topbar-right">
              <span className="cw-live-indicator">
                <i />
                Sample data
              </span>

              <span className="cw-profile-avatar">CW</span>
            </div>
          </header>

          <div className="cw-dashboard-body">
            {/* Page title and date filter */}
            <div className="cw-page-heading">
              <div>
                <span className="cw-overline">
                  CIVIC INTELLIGENCE WORKSPACE
                </span>

                <h1>{pageTitles[activeTab]}</h1>
                <p>{pageDescriptions[activeTab]}</p>
              </div>

              <label className="cw-period-control">
                <CalendarDays size={16} />

                <select
                  aria-label="Filter by date range"
                  value={period}
                  onChange={(event) =>
                    setPeriod(Number(event.target.value))
                  }
                >
                  <option value={7}>Last 7 days</option>
                  <option value={30}>Last 30 days</option>
                  <option value={90}>Last 90 days</option>
                </select>
              </label>
            </div>
            {/* OVERVIEW — ANIMATED CIVIC IMPACT */}
            {activeTab === "overview" && (
              <section className="cw-impact-overview">
                <div className="cw-impact-heading">
                  <span className="cw-impact-eyebrow">
                    <Activity size={16} />
                    CITYWATCH AI · CIVIC IMPACT
                  </span>

                  <h2>
                    Real Results.
                    <br />
                    <span>Measurable Change.</span>
                  </h2>

                  <p>
                    See how citizen participation is helping build cleaner,
                    safer, and more responsive cities.
                  </p>
                </div>

                <div className="cw-impact-primary-grid">
                  <article className="cw-impact-card">
                    <AnimatedNumber value={125000} suffix="+" />
                    <p>Issues Reported</p>
                  </article>
                  <article className="cw-impact-card">
                    <AnimatedNumber value={98000} suffix="+" />
                    <p>Issues Resolved</p>
                  </article>
                  <article className="cw-impact-card">
                    <AnimatedNumber value={250000} suffix="+" />
                    <p>Active Citizens</p>
                  </article>
                  <article className="cw-impact-card">
                    <AnimatedNumber value={150} suffix="+" />
                    <p>Partner Cities</p>
                  </article>
                </div>

                <div className="cw-impact-secondary-grid">
                  <article className="cw-impact-secondary-card">
                    <AnimatedNumber value={92} suffix="%" />
                    <p>Resolution Rate</p>
                  </article>
                  <article className="cw-impact-secondary-card">
                    <AnimatedNumber value={48} suffix="h" />
                    <p>Avg. Resolution Time</p>
                  </article>
                  <article className="cw-impact-secondary-card">
                    <AnimatedNumber value={4.8} decimals={1} suffix="/5" />
                    <p>User Satisfaction</p>
                  </article>
                </div>

                <div className="cw-impact-footnote">
                  <ShieldCheck size={15} />
                  Illustrative platform statistics for demonstration purposes.
                </div>
              </section>
            )}

            {/* ALL REPORTS */}
            {activeTab === "reports" && (
              <>
                <FilterBar
                  search={search}
                  setSearch={setSearch}
                  category={category}
                  setCategory={setCategory}
                  resultCount={filtered.length}
                />

                <RecentReports
                  filtered={filtered}
                  total={filtered.length}
                  onViewAll={() => {
                    setSearch("");
                    setCategory("All");
                  }}
                />
              </>
            )}

            {/* MAP VIEW */}
            {activeTab === "map" && (
              <article className="cw-panel cw-map-panel cw-large-map-panel">
                <PanelHeading
                  title="Explore civic reports"
                  description="Choose a marker to open its tracking page."
                  icon={MapPin}
                />

                <FilterBar
                  search={search}
                  setSearch={setSearch}
                  category={category}
                  setCategory={setCategory}
                  resultCount={filtered.length}
                />

                <MapCanvas filtered={filtered} large />

                <div className="cw-panel-footer">
                  <span>
                    Showing {filtered.length} matching locations
                  </span>
                  <button
                    type="button"
                    className="cw-inline-button"
                    onClick={() => {
                      setSearch("");
                      setCategory("All");
                    }}
                  >
                    Reset filters
                  </button>
                </div>
              </article>
            )}

            {/* ANALYTICS */}
            {activeTab === "analytics" && (
              <>
                <div className="cw-kpi-grid">
                  <article className="cw-kpi-card">
                    <span className="cw-kpi-label">TOTAL REPORTS</span>
                    <strong className="cw-kpi-value">
                      {totals.total}
                    </strong>
                  </article>

                  <article className="cw-kpi-card">
                    <span className="cw-kpi-label">CATEGORIES</span>
                    <strong className="cw-kpi-value">
                      {breakdown.length}
                    </strong>
                  </article>

                  <article className="cw-kpi-card">
                    <span className="cw-kpi-label">RESOLVED</span>
                    <strong className="cw-kpi-value">
                      {totals.resolved}
                    </strong>
                  </article>

                  <article className="cw-kpi-card">
                    <span className="cw-kpi-label">
                      AVG. RESOLUTION
                    </span>
                    <strong className="cw-kpi-value">
                      {averageResolution || "—"}
                    </strong>
                  </article>
                </div>

                <div className="cw-insights-grid">
                  <article className="cw-panel cw-category-panel">
                    <PanelHeading
                      title="Reports by category"
                      description="Share of reports in each category"
                      icon={BarChart3}
                      tone="purple"
                    />

                    <DonutChart
                      filtered={filtered}
                      breakdown={breakdown}
                      donutGradient={donutGradient}
                    />
                  </article>

                  <article className="cw-panel">
                    <PanelHeading
                      title="Category breakdown"
                      description="Counts for the selected period"
                      icon={Activity}
                    />

                    <div className="cw-analytics-list">
                      {breakdown.length === 0 ? (
                        <EmptyState
                          title="No data to analyse"
                          description="Try a different date range or category."
                        />
                      ) : (
                        breakdown.map(({ name, count }) => (
                          <div className="cw-analytics-row" key={name}>
                            <div className="cw-analytics-row-top">
                              <span className="cw-category-chip">
                                <i
                                  style={{
                                    background: colors[name],
                                  }}
                                />
                                {name}
                              </span>

                              <strong>{count}</strong>
                            </div>

                            <div className="cw-progress-track">
                              <span
                                style={{
                                  width: `${
                                    totals.total
                                      ? (count / totals.total) * 100
                                      : 0
                                  }%`,
                                  background: colors[name],
                                }}
                              />
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </article>
                </div>
              </>
            )}

            {/* MY REPORTS */}
            {activeTab === "my-reports" && (
              <>
                <div className="cw-notice">
                  <Users size={17} />

                  <span>
                    This view currently uses sample reports. Connect your
                    authenticated citizen account to show only your own
                    submissions.
                  </span>
                </div>

                <FilterBar
                  search={search}
                  setSearch={setSearch}
                  category={category}
                  setCategory={setCategory}
                  resultCount={filtered.length}
                />

                <RecentReports
                  filtered={filtered}
                  total={filtered.length}
                  onViewAll={() => {
                    setSearch("");
                    setCategory("All");
                  }}
                />
              </>
            )}

            <footer className="cw-dashboard-footer">
              <span>CityWatch AI · Civic reporting workspace</span>
              <span>
                <ShieldCheck size={13} />
                Human-reviewed civic reporting
              </span>
            </footer>
          </div>
        </section>
      </section>
    </main>
  );
}

/* Reusable category/search filters */

function FilterBar({
  search,
  setSearch,
  category,
  setCategory,
  resultCount,
}) {
  return (
    <section className="cw-filter-bar">
      <div className="cw-filter-title">
        <Filter size={17} />
        <strong>Find reports</strong>
      </div>

      <div className="cw-filter-controls">
        <label className="cw-search-control">
          <Search size={16} />

          <input
            type="search"
            placeholder="Search reports..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>

        <label className="cw-category-control">
          <span>Category</span>

          <select
            value={category}
            onChange={(event) => setCategory(event.target.value)}
          >
            <option value="All">All categories</option>

            {Object.keys(colors).map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <span className="cw-report-count">
        {resultCount} {resultCount === 1 ? "report" : "reports"}
      </span>
    </section>
  );
}

/* Illustrative map with working report links */

function MapCanvas({ filtered, large = false }) {
  return (
    <div
      className={`cw-map-canvas ${large ? "large" : ""}`}
      aria-label="Illustrative map of report locations"
    >
      <div className="cw-map-streets" />
      <div className="cw-map-park park-one" />
      <div className="cw-map-park park-two" />
      <div className="cw-map-water" />

      {filtered.length === 0 ? (
        <div className="cw-map-empty">
          <MapPin size={25} />
          <strong>No matching locations</strong>
          <span>Try changing your search or filters.</span>
        </div>
      ) : (
        filtered.map((report) => (
          <Link
            to={`/track-report?id=${encodeURIComponent(report.id)}`}
            key={report.id}
            title={`${report.title} — ${report.status}`}
            aria-label={`Track ${report.title}`}
            className="cw-map-marker"
            style={{
              left: `${report.x}%`,
              top: `${report.y}%`,
              "--marker-color": colors[report.category],
            }}
          >
            <MapPin size={29} fill="currentColor" />
          </Link>
        ))
      )}

      <div className="cw-map-legend">
        <i />
        Illustrative report map
      </div>
    </div>
  );
}

/* Donut chart */

function DonutChart({ filtered, breakdown, donutGradient }) {
  return (
    <div className="cw-donut-section">
      <div
        className="cw-donut"
        style={{ background: donutGradient }}
        role="img"
        aria-label={`Distribution of ${filtered.length} reports by category`}
      >
        <div className="cw-donut-hole">
          <strong>{filtered.length}</strong>
          <span>Reports</span>
        </div>
      </div>

      <ul className="cw-category-legend">
        {breakdown.length === 0 ? (
          <li className="cw-no-category">No category data available.</li>
        ) : (
          breakdown.map(({ name, count }) => (
            <li key={name}>
              <i
                className="cw-legend-dot"
                style={{ background: colors[name] }}
              />

              <span className="cw-legend-name">{name}</span>

              <strong>
                {filtered.length
                  ? Math.round((count / filtered.length) * 100)
                  : 0}
                %
              </strong>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}

/* Reports table */

function RecentReports({
  filtered,
  total,
  compact = false,
  onViewAll,
}) {
  return (
    <section className="cw-panel cw-recent-panel">
      <div className="cw-panel-heading cw-recent-heading">
        <div>
          <h2>{compact ? "Recent Reports" : "Civic Reports"}</h2>
          <p>
            {compact
              ? "The latest reports in the selected period."
              : "Review issue details, status, and location."}
          </p>
        </div>

        <span className="cw-report-count">
          {compact
            ? `${filtered.length} of ${total}`
            : `${filtered.length} reports`}
        </span>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title="No reports found"
          description="Try another search term, category, or date range."
        />
      ) : (
        <div className="cw-table-wrap">
          <table className="cw-reports-table">
            <thead>
              <tr>
                <th>Report</th>
                <th>Category</th>
                <th>Location</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>
              {filtered.map((report) => {
                const Icon = categoryIcons[report.category] || FileText;

                return (
                  <tr key={report.id}>
                    <td>
                      <div className="cw-report-cell">
                        <span
                          className="cw-report-symbol"
                          style={{
                            background: `${colors[report.category]}18`,
                            color: colors[report.category],
                          }}
                        >
                          <Icon size={18} />
                        </span>

                        <span>
                          <strong>{report.title}</strong>
                          <small>{report.id}</small>
                        </span>
                      </div>
                    </td>

                    <td>
                      <span className="cw-category-chip">
                        <i
                          style={{
                            background: colors[report.category],
                          }}
                        />
                        {report.category}
                      </span>
                    </td>

                    <td>
                      <span className="cw-location-cell">
                        <MapPin size={13} />
                        {report.place}
                      </span>
                    </td>

                    <td>
                      <StatusBadge status={report.status} />
                    </td>

                    <td>
                      <Link
                        className="cw-view-report"
                        to={`/track-report?id=${encodeURIComponent(report.id)}`}
                        aria-label={`View ${report.id}`}
                        title="Track this report"
                      >
                        <Eye size={16} />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="cw-table-footer">
        <span>
          {compact
            ? `Showing ${filtered.length} recent reports`
            : `Showing ${filtered.length} matching reports`}
        </span>

        <button
          type="button"
          className="cw-inline-button"
          onClick={onViewAll}
        >
          {compact ? "View all reports" : "Clear filters"}
          <ArrowRight size={14} />
        </button>
      </div>
    </section>
  );
}
