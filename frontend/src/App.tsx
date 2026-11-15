import { lazy, Suspense, useEffect, useState } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import CompanySearch from "./CompanySearch";
import "./index.css";

// Each page is its own chunk, so Recharts only loads on the pages that chart.
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Lookup = lazy(() => import("./pages/Lookup"));
const Portfolio = lazy(() => import("./pages/Portfolio"));
const QuantFactors = lazy(() => import("./pages/QuantFactors"));
const Learn = lazy(() => import("./pages/Learn"));

const NAV = [
  { to: "/", label: "Explore", end: true },
  { to: "/lookup", label: "Company" },
  { to: "/quant", label: "Factors" },
  { to: "/portfolio", label: "Portfolio" },
  { to: "/learn", label: "Learn" },
];

const THEME_KEY = "ecosg-theme";

function currentTheme(): "light" | "dark" {
  const set = document.documentElement.dataset.theme;
  if (set === "light" || set === "dark") return set;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function App() {
  // index.html applies a saved choice before first paint; with none saved, the system setting wins.
  const [theme, setTheme] = useState(currentTheme);

  // Until the user picks a theme, follow the system if it changes while the page is open.
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const follow = () => setTheme(currentTheme());
    media.addEventListener("change", follow);
    return () => media.removeEventListener("change", follow);
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      /* private mode: the choice just lasts for this visit */
    }
    setTheme(next);
  }

  return (
    <>
      <header className="app-header">
        <Link to="/" className="brand" aria-label="ecosg home">
          <span className="brand-dot" aria-hidden="true" />
          <span className="brand-mark">ecosg</span>
        </Link>
        <nav className="nav" aria-label="Main">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => (isActive ? "active" : "")}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="header-tools">
          <CompanySearch />
          <button
            type="button"
            className="icon-btn"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
            title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
              <circle cx="8" cy="8" r="6.25" fill="none" stroke="currentColor" strokeWidth="1.5" />
              <path d="M8 1.75a6.25 6.25 0 0 1 0 12.5z" fill="currentColor" />
            </svg>
          </button>
        </div>
      </header>
      <main>
        <Suspense fallback={<p className="muted">Loading…</p>}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/lookup" element={<Lookup />} />
            <Route path="/lookup/:ticker" element={<Lookup />} />
            <Route path="/quant" element={<QuantFactors />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/learn" element={<Learn />} />
          </Routes>
        </Suspense>
        <p className="disclaimer">
          ecosg is a learning tool. Every company number here is mock data, not from a real provider,
          and nothing on this site is investment advice.
        </p>
      </main>
    </>
  );
}

export default App;
