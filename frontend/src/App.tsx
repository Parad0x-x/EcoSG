import { lazy, Suspense } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import "./index.css";

// Each page is its own chunk, so Recharts only loads on the pages that chart.
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Lookup = lazy(() => import("./pages/Lookup"));
const Portfolio = lazy(() => import("./pages/Portfolio"));
const QuantFactors = lazy(() => import("./pages/QuantFactors"));

function App() {
  return (
    <>
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">ecosg</span>
          <span className="brand-tag">sustainable investing, made legible</span>
        </div>
        <nav className="nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Dashboard
          </NavLink>
          <NavLink to="/lookup" className={({ isActive }) => (isActive ? "active" : "")}>
            Stock Lookup
          </NavLink>
          <NavLink to="/quant" className={({ isActive }) => (isActive ? "active" : "")}>
            Quant Factors
          </NavLink>
          <NavLink to="/portfolio" className={({ isActive }) => (isActive ? "active" : "")}>
            Portfolio Screener
          </NavLink>
        </nav>
      </header>
      <main>
        <Suspense fallback={<p className="subtitle">Loading…</p>}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/lookup" element={<Lookup />} />
            <Route path="/lookup/:ticker" element={<Lookup />} />
            <Route path="/quant" element={<QuantFactors />} />
            <Route path="/portfolio" element={<Portfolio />} />
          </Routes>
        </Suspense>
        <p className="disclaimer">
          ECOSG is a demo MVP. All financial and ESG data shown is mock/illustrative and is not
          sourced from a real data provider. Nothing here is investment advice.
        </p>
      </main>
    </>
  );
}

export default App;
