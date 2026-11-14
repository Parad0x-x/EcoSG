import { lazy, Suspense } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
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

function App() {
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
