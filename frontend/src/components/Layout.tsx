import { Snowflake } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { SpectrumRule } from "./Decor";

const LINKS = [
  ["/", "Story"], ["/overview", "Overview"], ["/design", "Designer"], ["/optimize", "Optimizer"], ["/materials", "Materials"],
  ["/runs", "Lab runs"], ["/benchmark", "Benchmark"], ["/methods", "Methods"],
] as const;

export function Layout({ children }: { children: ReactNode }) {
  const story = useLocation().pathname === "/";
  return (
    <>
      <nav className={story ? "topnav over" : "topnav"} aria-label="Main">
        <NavLink to="/" className="brand"><span className="logo small"><Snowflake size={15} strokeWidth={1.5} /></span>Phys<i>.io</i></NavLink>
        <div className="links">
          {LINKS.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : undefined)}>{label}</NavLink>
          ))}
        </div>
      </nav>
      {story ? children : <main className="app">{children}</main>}
    </>
  );
}

export function PageHead({ title, sub, right, kicker, rule = true }: { title: string; sub?: ReactNode; right?: ReactNode; kicker?: string; rule?: boolean }) {
  return (
    <header className="page-head">
      <div className="ph-text">
        {kicker && <p className="kicker">{kicker}</p>}
        <h1 className="title">{title}</h1>
        {sub && <p className="subtitle">{sub}</p>}
      </div>
      {right && <div className="meta">{right}</div>}
      {rule && <SpectrumRule />}
    </header>
  );
}

export function Notice({ kind = "info", children }: { kind?: "info" | "error" | "warn"; children: ReactNode }) {
  return <div className={`notice ${kind}`} role={kind === "error" ? "alert" : "status"}>{children}</div>;
}
