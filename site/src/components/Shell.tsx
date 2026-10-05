import { useEffect, type ReactNode } from "react";
import { Link, usePath } from "../lib/router";
import { Footer } from "./Footer";

const LINKS = [
  { to: "/claims", label: "Claims" },
  { to: "/live", label: "Live test" },
  { to: "/method", label: "Method" },
];

export function Shell({ title, children }: { title: string; children: ReactNode }) {
  const path = usePath();
  useEffect(() => {
    document.title = `${title} · Is It Alpha Yet?`;
  }, [title]);
  return (
    <>
      <header className="nav">
        <Link to="/" className="brand">
          Is It Alpha Yet?
        </Link>
        {LINKS.map((l) => (
          <Link key={l.to} to={l.to} className={path.startsWith(l.to) ? "active" : undefined}>
            {l.label}
          </Link>
        ))}
      </header>
      <main className="page">{children}</main>
      <Footer />
    </>
  );
}

export function Verdict({ verdict }: { verdict: "alpha" | "not_alpha" }) {
  return verdict === "alpha" ? <span className="pill verdict-yes">Alpha</span> : <span className="pill verdict-no">Not alpha</span>;
}

export function Stat({ value, label }: { value: ReactNode; label: string }) {
  return (
    <div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
