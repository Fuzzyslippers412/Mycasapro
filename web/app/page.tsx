import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="landing-page">
      <nav className="landing-nav" aria-label="Primary">
        <Link className="auth-brand" href="/"><span className="brand-name">MyCasa</span><span className="brand-pro">Pro</span></Link>
        <div><Link className="text-link" href="/contractor">For contractors</Link><Link className="small-primary-button" href="/homeowner">Open your home</Link></div>
      </nav>

      <section className="landing-hero">
        <div className="landing-copy">
          <p className="kicker">A private record for the life of your home</p>
          <h1>Your home,<br /><span>properly cared for.</span></h1>
          <p>Repairs, trusted professionals, approvals, visits, and receipts—kept together for the place they belong to.</p>
          <div className="landing-actions"><Link className="primary-button" href="/homeowner">Set up my home</Link><Link className="secondary-button" href="/contractor">I’m a contractor</Link></div>
        </div>
        <aside className="landing-register" aria-label="What MyCasaPro keeps organized">
          <p className="register-label">The home register</p>
          <ol>
            <li><span>01</span><div><strong>Care</strong><p>Repairs and preventive maintenance, organized by room and system.</p></div></li>
            <li><span>02</span><div><strong>People</strong><p>The professionals you trust, with every visit and conversation intact.</p></div></li>
            <li><span>03</span><div><strong>Record</strong><p>Estimates, approvals, invoices, receipts, manuals, and warranties.</p></div></li>
          </ol>
          <p className="register-note">No sample jobs. No invented home. Your record begins when you do.</p>
        </aside>
      </section>

      <section className="landing-trust"><span>Private by default</span><span>One record per home</span><span>Clear from request to receipt</span></section>
    </main>
  );
}
