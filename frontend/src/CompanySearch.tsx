import { useId, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchCompanies, type CompanySummary } from "./api";
import { searchCompanies } from "./search";

// One shared request for every search box on the page; cleared on failure so the next focus retries.
let companiesPromise: Promise<CompanySummary[]> | null = null;
function loadCompanies(): Promise<CompanySummary[]> {
  companiesPromise ??= fetchCompanies().catch((e) => {
    companiesPromise = null;
    throw e;
  });
  return companiesPromise;
}

/** Find a company by ticker or name. Enter opens the highlighted match. */
export default function CompanySearch({ large = false }: { large?: boolean }) {
  const listId = useId();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  const matches = useMemo(() => searchCompanies(companies, query), [companies, query]);
  const showList = open && query.trim() !== "";

  function go(ticker: string) {
    setQuery("");
    setOpen(false);
    navigate(`/lookup/${encodeURIComponent(ticker)}`);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!matches.length) return;
      setOpen(true);
      setActive((i) => (i + (e.key === "ArrowDown" ? 1 : -1) + matches.length) % matches.length);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <form
      className={`search${large ? " search-lg" : ""}`}
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        // No match (or the list has not loaded): try what was typed as a ticker.
        const target = matches[active]?.ticker ?? query.trim().toUpperCase();
        if (target) go(target);
      }}
    >
      <input
        type="search"
        role="combobox"
        aria-label="Search companies by name or ticker"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={showList && matches.length ? `${listId}-${active}` : undefined}
        placeholder={large ? "Search a company, like Apple or MSFT" : "Search companies"}
        autoComplete="off"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setActive(0);
          setOpen(true);
        }}
        onFocus={() => {
          setOpen(true);
          loadCompanies().then(setCompanies, () => {});
        }}
        onBlur={() => setOpen(false)}
        onKeyDown={onKeyDown}
      />
      {showList && (
        <ul className="search-list" id={listId} role="listbox" aria-label="Matching companies">
          {matches.map((c, i) => (
            <li
              key={c.ticker}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              // mousedown, not click: it fires before the input's blur closes the list.
              onMouseDown={(e) => {
                e.preventDefault();
                go(c.ticker);
              }}
              onMouseEnter={() => setActive(i)}
            >
              <strong>{c.ticker}</strong>
              <span className="name">{c.name}</span>
              <span className="muted small hide-sm">{c.sector}</span>
            </li>
          ))}
          {matches.length === 0 && (
            <li className="search-empty" role="option" aria-selected="false" aria-disabled="true">
              {companies.length ? "No company matches. ecosg covers the S&P 500." : "Loading companies…"}
            </li>
          )}
        </ul>
      )}
    </form>
  );
}
