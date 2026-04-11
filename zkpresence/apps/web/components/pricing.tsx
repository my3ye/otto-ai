import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

const tiers = [
  {
    name: 'Developer',
    price: 'Free',
    priceSub: 'forever',
    proofs: '100',
    sla: 'Best-effort',
    bestFor: 'Hackathon builders',
    featured: false,
    cta: 'Start for Free',
    ctaVariant: 'secondary' as const,
    features: ['100 ZK proofs/mo', 'SP1 Groth16 access', 'TypeScript + Rust SDK', 'Community Discord', 'MIT licensed core'],
  },
  {
    name: 'Starter',
    price: '$49',
    priceSub: '/month',
    proofs: '2,000',
    sla: '< 3 min p95',
    bestFor: 'Early DAOs',
    featured: false,
    cta: 'Get Started',
    ctaVariant: 'outline' as const,
    features: ['2,000 ZK proofs/mo', '< 3 min p95 latency', 'All 3 attestation modes', 'Email support', 'Usage dashboard'],
  },
  {
    name: 'Team',
    price: '$199',
    priceSub: '/month',
    proofs: '20,000',
    sla: '< 90s p95',
    bestFor: 'Active protocols',
    featured: true,
    cta: 'Get Started',
    ctaVariant: 'purple' as const,
    features: ['20,000 ZK proofs/mo', '< 90s p95 latency', 'Priority prover queue', 'Slack support', 'Multi-chain deploy', 'Custom event contracts'],
  },
  {
    name: 'Scale',
    price: '$599',
    priceSub: '/month',
    proofs: '100,000',
    sla: '< 60s p95',
    bestFor: 'High-volume platforms',
    featured: false,
    cta: 'Get Started',
    ctaVariant: 'outline' as const,
    features: ['100,000 ZK proofs/mo', '< 60s p95 latency', 'Dedicated prover cluster', 'SLA-backed uptime', 'Analytics API', 'Priority Slack support'],
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    priceSub: 'pricing',
    proofs: 'Unlimited',
    sla: 'Custom SLA',
    bestFor: 'Enterprise compliance',
    featured: false,
    cta: 'Contact Us',
    ctaVariant: 'ghost-white' as const,
    features: ['Unlimited ZK proofs', 'Custom SLA & uptime', 'On-premise deploy', 'GDPR / SOC2', 'Dedicated CSM', 'White-label SDK'],
  },
];

export default function Pricing() {
  return (
    <section id="pricing" className="py-24 px-6 relative" aria-labelledby="pricing-heading">
      <div className="absolute top-0 left-0 right-0 h-px" aria-hidden="true" style={{ background: 'linear-gradient(to right, transparent, rgba(124,58,237,0.3), transparent)' }} />
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true" style={{ background: 'radial-gradient(ellipse 60% 40% at 50% 50%, rgba(124,58,237,0.04) 0%, transparent 70%)' }} />

      <div className="max-w-6xl mx-auto relative">
        <div className="text-center mb-16">
          <Badge variant="purple" className="mb-4 uppercase tracking-widest text-xs">Pricing</Badge>
          <h2 id="pricing-heading" className="text-3xl md:text-5xl font-bold tracking-tight mb-4">
            Start free. <span className="text-white/50">Scale with proof.</span>
          </h2>
          <p className="text-base max-w-xl mx-auto text-white/60">
            The circuit and SDK are MIT open source. Pay only for managed proving infrastructure.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {tiers.map((tier) => (
            <Card
              key={tier.name}
              className={`relative flex flex-col transition-all duration-300 ${
                tier.featured
                  ? 'border-purple-600 bg-purple-600/5 shadow-lg shadow-purple-600/10'
                  : 'border-white/8 bg-white/[0.02]'
              }`}
            >
              {tier.featured && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10">
                  <Badge variant="purple" className="whitespace-nowrap bg-purple-600 text-white border-purple-600">
                    Most Popular
                  </Badge>
                </div>
              )}

              <CardHeader className="pb-3">
                <div className="text-xs font-bold uppercase tracking-wider mb-1 font-mono" style={{ color: tier.featured ? '#9d67ff' : 'rgba(255,255,255,0.5)' }}>
                  {tier.name}
                </div>
                <div className="flex items-baseline gap-1">
                  <CardTitle className="text-2xl font-extrabold">{tier.price}</CardTitle>
                  <span className="text-xs text-white/35">{tier.priceSub}</span>
                </div>
              </CardHeader>

              <CardContent className="flex flex-col flex-1">
                <div className="rounded-lg px-3 py-3 mb-4 bg-white/[0.03] space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-white/35">Proofs</span>
                    <span className="text-sm font-bold font-mono" style={{ color: tier.featured ? '#9d67ff' : 'white' }}>{tier.proofs}</span>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-white/35">SLA</span>
                    <span className="text-xs font-mono text-white/60">{tier.sla}</span>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-white/35">Best for</span>
                    <span className="text-xs text-white/60 text-right">{tier.bestFor}</span>
                  </div>
                </div>

                <ul className="flex flex-col gap-2.5 mb-6 flex-1">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="mt-0.5 flex-shrink-0" style={{ color: tier.featured ? '#9d67ff' : '#06b6d4' }} aria-hidden="true">
                        <path d="M20 6L9 17l-5-5" />
                      </svg>
                      <span className="text-xs text-white/60 leading-relaxed">{feature}</span>
                    </li>
                  ))}
                </ul>

                <Button variant={tier.ctaVariant} className="w-full" size="sm" asChild>
                  <a href={tier.name === 'Enterprise' ? '#contact' : '#signup'}>{tier.cta}</a>
                </Button>
                {tier.name === 'Developer' && (
                  <p className="text-center text-xs mt-2 text-white/35">No credit card required</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>

        <p className="text-center text-sm mt-10 text-white/35">
          All plans include open-source circuit and SDK.{' '}
          <a href="https://github.com/my3ye/zkpresence" target="_blank" rel="noopener noreferrer" className="underline underline-offset-2 text-white/50 hover:text-white transition-colors">
            Self-host free on GitHub.
          </a>
        </p>
      </div>
    </section>
  );
}
