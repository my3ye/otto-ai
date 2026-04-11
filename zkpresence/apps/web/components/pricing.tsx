const tiers = [
  {
    name: 'Developer',
    price: 'Free',
    priceSub: 'forever',
    proofs: '100',
    proofsPeriod: 'proofs/mo',
    sla: 'Best-effort',
    bestFor: 'Hackathon builders',
    featured: false,
    cta: 'Start for Free',
    ctaNote: 'No credit card required',
    ctaStyle: 'ghost',
    features: [
      '100 ZK proofs per month',
      'SP1 Groth16 prover access',
      'TypeScript + Rust SDK',
      'Community Discord support',
      'MIT licensed core',
    ],
  },
  {
    name: 'Starter',
    price: '$49',
    priceSub: 'per month',
    proofs: '2,000',
    proofsPeriod: 'proofs/mo',
    sla: '< 3 min p95',
    bestFor: 'Early DAOs',
    featured: false,
    cta: 'Get Started',
    ctaNote: null,
    ctaStyle: 'outline',
    features: [
      '2,000 ZK proofs per month',
      '< 3 min p95 proof latency',
      'All 3 attestation modes',
      'Email support',
      'Usage dashboard',
    ],
  },
  {
    name: 'Team',
    price: '$199',
    priceSub: 'per month',
    proofs: '20,000',
    proofsPeriod: 'proofs/mo',
    sla: '< 90s p95',
    bestFor: 'Active protocols',
    featured: true,
    cta: 'Get Started',
    ctaNote: 'Most popular',
    ctaStyle: 'primary',
    features: [
      '20,000 ZK proofs per month',
      '< 90s p95 proof latency',
      'Priority prover queue',
      'Slack / Discord support',
      'Multi-chain deploy support',
      'Custom event contracts',
    ],
  },
  {
    name: 'Scale',
    price: '$599',
    priceSub: 'per month',
    proofs: '100,000',
    proofsPeriod: 'proofs/mo',
    sla: '< 60s p95',
    bestFor: 'High-volume platforms',
    featured: false,
    cta: 'Get Started',
    ctaNote: null,
    ctaStyle: 'outline',
    features: [
      '100,000 ZK proofs per month',
      '< 60s p95 proof latency',
      'Dedicated prover cluster',
      'SLA-backed uptime',
      'Advanced analytics API',
      'Priority Slack support',
    ],
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    priceSub: 'pricing',
    proofs: 'Unlimited',
    proofsPeriod: 'proofs/mo',
    sla: 'Custom SLA',
    bestFor: 'Enterprise compliance',
    featured: false,
    cta: 'Contact Us',
    ctaNote: null,
    ctaStyle: 'ghost',
    features: [
      'Unlimited ZK proofs',
      'Custom SLA & uptime',
      'On-premise deployment',
      'GDPR / SOC2 compliance',
      'Dedicated account manager',
      'White-label SDK option',
    ],
  },
];

export default function Pricing() {
  return (
    <section
      id="pricing"
      className="py-24 px-6 relative"
      aria-labelledby="pricing-heading"
    >
      {/* Top separator */}
      <div
        className="absolute top-0 left-0 right-0 h-px"
        aria-hidden="true"
        style={{ background: 'linear-gradient(to right, transparent, rgba(124,58,237,0.3), transparent)' }}
      />

      {/* Background glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        aria-hidden="true"
        style={{
          background: 'radial-gradient(ellipse 60% 40% at 50% 50%, rgba(124,58,237,0.04) 0%, transparent 70%)',
        }}
      />

      <div className="max-w-6xl mx-auto relative">
        {/* Header */}
        <div className="text-center mb-16">
          <p
            className="text-xs font-semibold tracking-widest uppercase mb-3"
            style={{ color: 'var(--accent-purple-light)' }}
          >
            Pricing
          </p>
          <h2
            id="pricing-heading"
            className="text-3xl md:text-5xl font-bold tracking-tight mb-4"
            style={{ fontFamily: 'Syne, sans-serif' }}
          >
            Start free.{' '}
            <span style={{ color: 'var(--text-secondary)' }}>Scale with proof.</span>
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: 'var(--text-secondary)' }}>
            The circuit and SDK are MIT open source. Pay only for managed proving infrastructure.
          </p>
        </div>

        {/* Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {tiers.map((tier) => (
            <PricingCard key={tier.name} tier={tier} />
          ))}
        </div>

        {/* Footer note */}
        <p className="text-center text-sm mt-10" style={{ color: 'var(--text-muted)' }}>
          All plans include access to the open-source circuit and SDK.{' '}
          <a
            href="https://github.com/my3ye/zkpresence"
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2 transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'white')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
          >
            Self-host for free on GitHub.
          </a>
        </p>
      </div>
    </section>
  );
}

function PricingCard({ tier }: { tier: typeof tiers[0] }) {
  return (
    <div
      className={`relative rounded-2xl p-5 flex flex-col transition-all duration-300 ${tier.featured ? 'card-featured' : ''}`}
      style={{
        background: tier.featured ? 'rgba(124,58,237,0.06)' : 'var(--bg-card)',
        border: tier.featured ? '1px solid var(--accent-purple)' : '1px solid var(--border-subtle)',
      }}
    >
      {/* Featured badge */}
      {tier.featured && (
        <div
          className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-xs font-semibold text-white whitespace-nowrap"
          style={{ background: 'var(--accent-purple)' }}
        >
          Most Popular
        </div>
      )}

      {/* Tier name */}
      <div className="mb-4">
        <h3
          className="text-sm font-bold uppercase tracking-wider mb-1"
          style={{
            color: tier.featured ? 'var(--accent-purple-light)' : 'var(--text-secondary)',
            fontFamily: 'DM Mono, monospace',
          }}
        >
          {tier.name}
        </h3>
        <div className="flex items-baseline gap-1">
          <span
            className="text-2xl font-extrabold"
            style={{ fontFamily: 'Syne, sans-serif' }}
          >
            {tier.price}
          </span>
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            {tier.priceSub}
          </span>
        </div>
      </div>

      {/* Stats */}
      <div
        className="py-3 mb-4 rounded-lg px-3"
        style={{ background: 'rgba(255,255,255,0.03)' }}
      >
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Proofs</span>
          <span
            className="text-sm font-bold font-mono"
            style={{ color: tier.featured ? 'var(--accent-purple-light)' : 'white', fontFamily: 'DM Mono, monospace' }}
          >
            {tier.proofs}
          </span>
        </div>
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>SLA</span>
          <span className="text-xs font-mono" style={{ color: 'var(--text-secondary)', fontFamily: 'DM Mono, monospace' }}>
            {tier.sla}
          </span>
        </div>
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Best for</span>
          <span className="text-xs text-right" style={{ color: 'var(--text-secondary)' }}>
            {tier.bestFor}
          </span>
        </div>
      </div>

      {/* Features */}
      <ul className="flex flex-col gap-2.5 mb-6 flex-1">
        {tier.features.map((feature) => (
          <li key={feature} className="flex items-start gap-2">
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              className="mt-0.5 flex-shrink-0"
              style={{ color: tier.featured ? 'var(--accent-purple-light)' : 'var(--accent-cyan)' }}
              aria-hidden="true"
            >
              <path d="M20 6L9 17l-5-5" />
            </svg>
            <span className="text-xs" style={{ color: 'var(--text-secondary)', lineHeight: '1.5' }}>
              {feature}
            </span>
          </li>
        ))}
      </ul>

      {/* CTA */}
      <div>
        <a
          href={tier.name === 'Enterprise' ? '#contact' : '#signup'}
          className={`block w-full text-center py-2.5 rounded-xl text-sm font-semibold transition-all duration-200`}
          style={
            tier.ctaStyle === 'primary'
              ? {
                  background: 'var(--accent-purple)',
                  color: 'white',
                }
              : tier.ctaStyle === 'outline'
              ? {
                  background: 'transparent',
                  border: '1px solid var(--border-medium)',
                  color: 'rgba(255,255,255,0.8)',
                }
              : {
                  background: 'rgba(255,255,255,0.05)',
                  color: 'rgba(255,255,255,0.6)',
                }
          }
          onMouseEnter={e => {
            const el = e.currentTarget as HTMLElement;
            if (tier.ctaStyle === 'primary') {
              el.style.background = 'var(--accent-purple-light)';
              el.style.boxShadow = '0 0 20px rgba(124,58,237,0.4)';
            } else {
              el.style.background = 'rgba(255,255,255,0.08)';
              el.style.color = 'white';
            }
          }}
          onMouseLeave={e => {
            const el = e.currentTarget as HTMLElement;
            if (tier.ctaStyle === 'primary') {
              el.style.background = 'var(--accent-purple)';
              el.style.boxShadow = 'none';
            } else if (tier.ctaStyle === 'outline') {
              el.style.background = 'transparent';
              el.style.color = 'rgba(255,255,255,0.8)';
            } else {
              el.style.background = 'rgba(255,255,255,0.05)';
              el.style.color = 'rgba(255,255,255,0.6)';
            }
          }}
        >
          {tier.cta}
        </a>
        {tier.ctaNote && tier.name === 'Developer' && (
          <p className="text-center text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
            {tier.ctaNote}
          </p>
        )}
      </div>
    </div>
  );
}
