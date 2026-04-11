export default function CommunityCta() {
  return (
    <section
      className="py-24 px-6 relative"
      aria-labelledby="community-heading"
    >
      {/* Top separator */}
      <div
        className="absolute top-0 left-0 right-0 h-px"
        aria-hidden="true"
        style={{ background: 'linear-gradient(to right, transparent, rgba(6,182,212,0.2), transparent)' }}
      />

      <div className="max-w-4xl mx-auto">
        {/* Main card */}
        <div
          className="relative rounded-3xl overflow-hidden p-12 md:p-16 text-center"
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          {/* Background glow */}
          <div
            className="absolute inset-0 pointer-events-none"
            aria-hidden="true"
            style={{
              background: `
                radial-gradient(ellipse 80% 60% at 50% -20%, rgba(124,58,237,0.12) 0%, transparent 70%),
                radial-gradient(ellipse 40% 40% at 80% 80%, rgba(6,182,212,0.06) 0%, transparent 60%)
              `,
            }}
          />

          {/* Decorative grid pattern */}
          <div
            className="absolute inset-0 pointer-events-none opacity-30"
            aria-hidden="true"
            style={{
              backgroundImage:
                'linear-gradient(rgba(124,58,237,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(124,58,237,0.04) 1px, transparent 1px)',
              backgroundSize: '40px 40px',
            }}
          />

          {/* Content */}
          <div className="relative">
            {/* Icon */}
            <div
              className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-8"
              style={{
                background: 'linear-gradient(135deg, rgba(124,58,237,0.2), rgba(6,182,212,0.1))',
                border: '1px solid rgba(124,58,237,0.3)',
              }}
            >
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ color: 'var(--accent-purple-light)' }}
                aria-hidden="true"
              >
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </div>

            <h2
              id="community-heading"
              className="text-3xl md:text-4xl font-bold mb-4 tracking-tight"
              style={{ fontFamily: 'Syne, sans-serif' }}
            >
              Join the community building
              <br />
              <span className="gradient-text-main">private attendance infrastructure</span>
            </h2>

            <p className="text-base mb-10 max-w-xl mx-auto" style={{ color: 'var(--text-secondary)' }}>
              OSS contributors welcome.{' '}
              <span style={{ color: 'rgba(255,255,255,0.7)' }}>Good first issues tagged.</span>{' '}
              SP1 + Rust + Solidity.
            </p>

            {/* CTA buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
              <a
                href="https://github.com/my3ye/zkpresence"
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-center gap-2.5 px-8 py-4 rounded-xl font-semibold text-base transition-all duration-200"
                style={{
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid var(--border-medium)',
                  color: 'white',
                }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.1)';
                  (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.25)';
                  (e.currentTarget as HTMLElement).style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.06)';
                  (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-medium)';
                  (e.currentTarget as HTMLElement).style.transform = 'none';
                }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.555 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.484 17.522 2 12 2z" />
                </svg>
                ★ Star on GitHub
              </a>

              <a
                href="#"
                className="flex items-center gap-2.5 px-8 py-4 rounded-xl font-semibold text-base transition-all duration-200"
                style={{
                  background: 'rgba(88,101,242,0.15)',
                  border: '1px solid rgba(88,101,242,0.3)',
                  color: '#9fa8ff',
                }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLElement).style.background = 'rgba(88,101,242,0.25)';
                  (e.currentTarget as HTMLElement).style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLElement).style.background = 'rgba(88,101,242,0.15)';
                  (e.currentTarget as HTMLElement).style.transform = 'none';
                }}
              >
                {/* Discord icon */}
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.083.083 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
                </svg>
                Join Discord
              </a>
            </div>

            {/* Stats row */}
            <div
              className="flex flex-col sm:flex-row items-center justify-center gap-8 pt-8"
              style={{ borderTop: '1px solid var(--border-subtle)' }}
            >
              <Stat value="MIT" label="Licensed" accent="purple" />
              <div className="hidden sm:block w-px h-8" style={{ background: 'var(--border-subtle)' }} />
              <Stat value="SP1" label="Groth16 Native" accent="cyan" />
              <div className="hidden sm:block w-px h-8" style={{ background: 'var(--border-subtle)' }} />
              <Stat value="Base" label="L2 Deployed" accent="purple" />
              <div className="hidden sm:block w-px h-8" style={{ background: 'var(--border-subtle)' }} />
              <Stat value="3" label="Attestation Modes" accent="cyan" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Stat({ value, label, accent }: { value: string; label: string; accent: 'purple' | 'cyan' }) {
  return (
    <div className="text-center">
      <div
        className="text-2xl font-extrabold mb-0.5"
        style={{
          fontFamily: 'Syne, sans-serif',
          color: accent === 'purple' ? 'var(--accent-purple-light)' : 'var(--accent-cyan)',
        }}
      >
        {value}
      </div>
      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
        {label}
      </div>
    </div>
  );
}
