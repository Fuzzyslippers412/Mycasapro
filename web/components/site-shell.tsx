"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useAuth } from "@/components/auth-context";

type WorkspaceRole = "homeowner" | "contractor";
type IconName = "overview" | "repairs" | "calendar" | "payments" | "home" | "requests" | "jobs" | "clients" | "logout";

type ShellProps = {
  role: WorkspaceRole;
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
};

const navigation: Record<WorkspaceRole, Array<{ label: string; href: string; icon: IconName }>> = {
  homeowner: [
    { label: "Overview", href: "/homeowner#overview", icon: "overview" },
    { label: "Repairs", href: "/homeowner#repairs", icon: "repairs" },
    { label: "Calendar", href: "/homeowner#calendar", icon: "calendar" },
    { label: "Payments", href: "/homeowner#payments", icon: "payments" },
    { label: "Home record", href: "/homeowner#home-record", icon: "home" },
  ],
  contractor: [
    { label: "Today", href: "/contractor#today", icon: "overview" },
    { label: "Requests", href: "/contractor#requests", icon: "requests" },
    { label: "Jobs", href: "/contractor#jobs", icon: "jobs" },
  ],
};

export function SiteShell({ role, title, description, action, children }: ShellProps) {
  const { user, logout } = useAuth();
  const navItems = navigation[role];
  const initials = user.display_name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  return (
    <div className="app-frame">
      <aside className="app-sidebar">
        <Link className="sidebar-brand" href={role === "homeowner" ? "/homeowner" : "/contractor"}>
          <span className="brand-name">MyCasa</span>
          <span className="brand-pro">Pro</span>
        </Link>

        <div className="workspace-label">{role === "homeowner" ? "My home" : "Contractor desk"}</div>
        <nav className="sidebar-nav" aria-label={`${role} navigation`}>
          {navItems.map((item, index) => (
            <Link className={index === 0 ? "nav-item is-current" : "nav-item"} href={item.href} key={item.label}>
              <NavIcon name={item.icon} />
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        <div className="sidebar-account">
          <span className="account-copy">
            <strong>{user.display_name}</strong>
            <small>{user.email}</small>
          </span>
          <button className="signout-button" type="button" onClick={() => void logout()} aria-label="Sign out">
            <NavIcon name="logout" />
          </button>
        </div>
      </aside>

      <div className="app-main">
        <header className="mobile-header">
          <Link className="sidebar-brand" href={role === "homeowner" ? "/homeowner" : "/contractor"}>
            <span className="brand-name">MyCasa</span>
            <span className="brand-pro">Pro</span>
          </Link>
          <button className="account-avatar mobile-account-button" type="button" onClick={() => void logout()} aria-label="Sign out">{initials || "U"}</button>
        </header>

        <main className="workspace-content">
          <header className="page-heading">
            <div>
              <p className="kicker">{role === "homeowner" ? "Private home record" : "Professional work desk"}</p>
              <h1>{title}</h1>
              {description ? <p>{description}</p> : null}
            </div>
            {action ? <div className="page-action">{action}</div> : null}
          </header>
          {children}
        </main>

        <nav className="mobile-nav" aria-label={`${role} mobile navigation`}>
          {navItems.slice(0, 4).map((item, index) => (
            <Link className={index === 0 ? "mobile-nav-item is-current" : "mobile-nav-item"} href={item.href} key={item.label}>
              <NavIcon name={item.icon} />
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>
      </div>
    </div>
  );
}

function NavIcon({ name }: { name: IconName }) {
  const paths: Record<IconName, ReactNode> = {
    overview: <><path d="M4 5h6v6H4zM14 5h6v4h-6zM14 13h6v6h-6zM4 15h6v4H4z" /></>,
    repairs: <><path d="m14.5 5.5 4 4M13 7l4 4M5 19l3.3-.8L18 7.5 14.5 4 4.8 13.7 4 17z" /></>,
    calendar: <><path d="M5 4v3M19 4v3M4 9h16M5 6h14a1 1 0 0 1 1 1v12H4V7a1 1 0 0 1 1-1z" /></>,
    payments: <><path d="M4 7h16v11H4zM4 10h16M7 15h4" /></>,
    home: <><path d="m3 11 9-7 9 7M5 10v10h14V10M9 20v-6h6v6" /></>,
    requests: <><path d="M6 4h12v16H6zM9 8h6M9 12h6M9 16h4" /></>,
    jobs: <><path d="M4 8h16v11H4zM9 8V5h6v3M4 12h16M10 12v2h4v-2" /></>,
    clients: <><path d="M8 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM2 20c0-4 2.5-6 6-6s6 2 6 6M16 11a3 3 0 1 0 0-6M15 15c4 0 6 1.7 6 5" /></>,
    logout: <><path d="M10 5H5v14h5M14 8l4 4-4 4M18 12H9" /></>,
  };
  return <svg className="nav-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}
