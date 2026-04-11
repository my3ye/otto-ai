const props = [
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <rect x="5" y="11" width="14" height="10" rx="2" />
        <path d="M8 11V7a4 4 0 0 1 8 0v4" />
        <circle cx="12" cy="16" r="1" fill="currentColor" />
      </svg>
    ),
    title: 'Zero-Knowledge by Design',
    description: (
      <>
        Your <code className="text-xs px-1.5 py-0.5 rounded font-mono" style={{ background: 'rgba(124,58,237,0.15)', color: '#9d67ff' }}>user_secret</code> never leaves your device.
        On-chain: only a nullifier and identity commitment. Different events produce different nullifiers —{' '}
        <strong className="text-white font-medium">cross-event attendance is unlinkable.</strong>
      </>
    ),
    accent: 'purple',
    stat: '0 bytes',
    statLabel: 'of personal data on-chain',
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="M9 12l2 2 4-4" />
      </svg>
    ),
    title: 'Three Attestation Modes',
    description: (
      <>
        <strong className="text-white font-medium">QR code scan</strong> at the venue.{' '}
        <strong className="text-white font-medium">GPS geohash proximity</strong> (~5km).{' '}
        <strong className="text-white font-medium">Direct organizer signature.</strong>{' '}
        All three produce the same verifiable proof.
      </>
    ),
    accent: 'cyan',
    stat: '3 modes',
    statLabel: 'one unified proof format',
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
      </svg>
    ),
    title: 'SP1 Native, EVM Ready',
    description: (
      <>
        Built on Succinct SP1&apos;s Groth16 backend. Deploys to{' '}
        <strong className="text-white font-medium">Base, Arbitrum</strong>, and all EVM chains.{' '}
        <strong className="text-white font-medium">~$0.001 gwei</strong> median verification cost.
      </>
    ),
    accent: 'purple',
    stat: '~$0.001',
    statLabel: 'median on-chain verification',
  },
];

export default function ValueProps() {
  return (
    <section
      id="features"
      className="py-24 px-6 relative"
      aria-labelledby="value-props-heading"
    >
      {/* Section separator line */}
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-px h-16"
        aria-hidden="true"
        style={{ background: 'linear-gradient(to bottom, transparent, rgba(124,58,237,0.4), transparent)' }}
      />

      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <div className="text-center mb-16">
          <p
            className="text-xs font-semibold tracking-widest uppercase mb-3"
            style={{ color: 'var(--accent-purple-light)' }}
          >
            Why zkPresence
          </p>
          <h2
            id="value-props-heading"
            className="text-3xl md:text-5xl font-bold tracking-tight"
            style={{ fontFamily: 'Syne, sans-serif' }}
          >
            Privacy isn&apos;t a feature.
            <br />
            <span style={{ color: 'var(--text-secondary)' }}>It&apos;s the architecture.</span>
          </h2>
        </div>

        {/* Cards grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {props.map((prop, i) => {
            const accentColor = prop.accent === 'cyan'
              ? { text: 'var(--accent-cyan)', bg: 'rgba(6,182,212,0.08)', border: 'rgba(6,182,212,0.2)' }
              : { text: 'var(--accent-purple-light)', bg: 'rgba(124,58,237,0.08)', border: 'rgba(124,58,237,0.2)' };

            return (
              <div
                key={prop.title}
                className="group relative rounded-2xl p-7 transition-all duration-300"
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLElement).style.borderColor = accentColor.border;
                  (e.currentTarget as HTMLElement).style.background = 'var(--bg-card-hover)';
                  (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)';
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-subtle)';
                  (e.currentTarget as HTMLElement).style.background = 'var(--bg-card)';
                  (e.currentTarget as HTMLElement).style.transform = 'none';
                }}
              >
                {/* Icon */}
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center mb-5"
                  style={{ background: accentColor.bg, color: accentColor.text }}
                >
                  {prop.icon}
                </div>

                {/* Title */}
                <h3
                  className="text-lg font-bold mb-3"
                  style={{ fontFamily: 'Syne, sans-serif' }}
                >
                  {prop.title}
                </h3>

                {/* Description */}
                <p
                  className="text-sm leading-relaxed mb-6"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  {prop.description}
                </p>

                {/* Stat pill */}
                <div
                  className="inline-flex items-baseline gap-2 px-3 py-1.5 rounded-lg"
                  style={{ background: accentColor.bg }}
                >
                  <span
                    className="text-base font-bold font-mono"
                    style={{ color: accentColor.text, fontFamily: 'DM Mono, monospace' }}
                  >
                    {prop.stat}
                  </span>
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {prop.statLabel}
                  </span>
                </div>

                {/* Index number decoration */}
                <div
                  className="absolute top-6 right-6 text-6xl font-black select-none pointer-events-none transition-opacity duration-300 opacity-0 group-hover:opacity-100"
                  aria-hidden="true"
                  style={{
                    fontFamily: 'Syne, sans-serif',
                    color: accentColor.text,
                    opacity: 0,
                    lineHeight: 1,
                  }}
                >
                  {String(i + 1).padStart(2, '0')}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
