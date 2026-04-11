import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

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
    description: 'Your user_secret never leaves your device. On-chain: only a nullifier and identity commitment. Cross-event attendance is unlinkable.',
    accent: 'purple' as const,
    stat: '0 bytes',
    statLabel: 'of personal data on-chain',
    badgeVariant: 'purple' as const,
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="M9 12l2 2 4-4" />
      </svg>
    ),
    title: 'Three Attestation Modes',
    description: 'QR code scan at venue. GPS geohash proximity (~5km). Direct organizer signature. All three produce the same verifiable proof.',
    accent: 'cyan' as const,
    stat: '3 modes',
    statLabel: 'one unified proof format',
    badgeVariant: 'cyan' as const,
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
      </svg>
    ),
    title: 'SP1 Native, EVM Ready',
    description: 'Built on Succinct SP1 Groth16. Deploys to Base, Arbitrum, and all EVM chains. ~$0.001 gwei median verification cost.',
    accent: 'purple' as const,
    stat: '~$0.001',
    statLabel: 'median on-chain verification',
    badgeVariant: 'purple' as const,
  },
];

const accentStyles = {
  purple: { text: '#9d67ff', bg: 'rgba(124,58,237,0.1)', border: 'rgba(124,58,237,0.2)' },
  cyan: { text: '#22d3ee', bg: 'rgba(6,182,212,0.08)', border: 'rgba(6,182,212,0.2)' },
};

export default function ValueProps() {
  return (
    <section id="features" className="py-24 px-6 relative" aria-labelledby="value-props-heading">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-px h-16" aria-hidden="true" style={{ background: 'linear-gradient(to bottom, transparent, rgba(124,58,237,0.4), transparent)' }} />

      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <Badge variant="purple" className="mb-4 uppercase tracking-widest text-xs">Why zkPresence</Badge>
          <h2 id="value-props-heading" className="text-3xl md:text-5xl font-bold tracking-tight">
            Privacy isn&apos;t a feature.
            <br />
            <span className="text-white/50">It&apos;s the architecture.</span>
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {props.map((prop) => {
            const a = accentStyles[prop.accent];
            return (
              <Card key={prop.title} className="group border-white/8 bg-white/[0.02] hover:border-white/15 hover:bg-white/[0.04] transition-all duration-300 hover:-translate-y-1">
                <CardContent className="p-7">
                  {/* Icon */}
                  <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-5" style={{ background: a.bg, color: a.text }}>
                    {prop.icon}
                  </div>

                  <h3 className="text-lg font-bold mb-3">{prop.title}</h3>

                  <p className="text-sm leading-relaxed mb-6 text-white/60">{prop.description}</p>

                  {/* Stat badge using shadcn/ui Badge */}
                  <Badge variant={prop.badgeVariant} className="gap-2 text-sm font-bold font-mono">
                    {prop.stat}
                    <span className="text-xs font-normal opacity-70">{prop.statLabel}</span>
                  </Badge>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}
