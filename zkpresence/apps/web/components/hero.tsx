'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export default function Hero() {
  return (
    <section
      className="relative min-h-screen flex flex-col items-center justify-center px-6 pt-24 pb-20 overflow-hidden grid-bg hero-spotlight"
      aria-label="Hero"
    >
      <div
        className="absolute inset-0 pointer-events-none"
        aria-hidden="true"
        style={{ background: 'radial-gradient(ellipse 70% 40% at 50% 0%, rgba(124,58,237,0.12) 0%, transparent 65%)' }}
      />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full pointer-events-none" aria-hidden="true" style={{ background: 'radial-gradient(circle, rgba(124,58,237,0.06) 0%, transparent 70%)', filter: 'blur(40px)' }} />
      <div className="absolute bottom-1/3 right-1/4 w-72 h-72 rounded-full pointer-events-none" aria-hidden="true" style={{ background: 'radial-gradient(circle, rgba(6,182,212,0.05) 0%, transparent 70%)', filter: 'blur(40px)' }} />

      <div className="relative max-w-5xl mx-auto w-full flex flex-col items-center text-center">

        {/* shadcn/ui Badge */}
        <div className="mb-8 animate-fade-in">
          <Badge variant="purple" className="gap-2 px-3 py-1.5 text-xs rounded-full">
            <span className="w-1.5 h-1.5 rounded-full animate-flow-node bg-purple-400" />
            SP1 Groth16 · MIT Open Source · Base L2
          </Badge>
        </div>

        <h1 className="text-5xl md:text-7xl lg:text-8xl font-extrabold tracking-tight mb-6 animate-fade-in-up" style={{ lineHeight: '1.05' }}>
          <span className="gradient-text-main">Prove you were there.</span>
          <br />
          <span className="text-white/40">Reveal nothing else.</span>
        </h1>

        <p className="text-lg md:text-xl max-w-2xl mb-10 animate-fade-in-up delay-200 text-white/60" style={{ lineHeight: '1.7' }}>
          The first SP1-native zero-knowledge attendance protocol.{' '}
          <span className="text-white/80">Open source. On-chain. Unfarmable.</span>
        </p>

        {/* shadcn/ui Buttons */}
        <div className="flex flex-col sm:flex-row items-center gap-4 mb-16 animate-fade-in-up delay-300">
          <Button variant="purple" size="xl" asChild>
            <a href="#pricing">Get Started — Free</a>
          </Button>
          <Button variant="outline" size="xl" asChild className="border-white/20 text-white/80 hover:text-white hover:bg-white/5">
            <a href="https://github.com/my3ye/zkpresence" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2.5">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.484 17.522 2 12 2z" />
              </svg>
              ★ Star on GitHub
            </a>
          </Button>
        </div>

        {/* Flow diagram */}
        <div className="w-full max-w-3xl animate-fade-in-up delay-500" role="img" aria-label="ZK proof flow: user_secret → SP1 Prover → ZK Proof → Base L2 → Verified">
          <div className="relative rounded-2xl p-8 md:p-10 overflow-hidden border border-white/5 bg-white/[0.02]">
            <div className="absolute inset-0 pointer-events-none rounded-2xl" aria-hidden="true" style={{ background: 'radial-gradient(ellipse 60% 50% at 50% 50%, rgba(124,58,237,0.05) 0%, transparent 70%)' }} />
            <div className="relative flex flex-col md:flex-row items-center justify-between gap-4 md:gap-2">
              <FlowNode label="user_secret" sublabel="Never leaves device" color="purple" delay={0} icon={<LockIcon />} />
              <FlowArrow delay={1} />
              <FlowNode label="SP1 Prover" sublabel="Groth16 circuit" color="purple" delay={2} icon={<BoltIcon />} />
              <FlowArrow delay={3} />
              <FlowNode label="ZK Proof" sublabel="~200 bytes" color="cyan" delay={4} icon={<ShieldIcon />} />
              <FlowArrow delay={5} />
              <FlowNode label="Base L2" sublabel="~$0.001 gwei" color="cyan" delay={6} icon={<DbIcon />} />
              <FlowArrow delay={7} />
              <FlowNode label="✓ Verified" sublabel="On-chain proof" color="green" delay={8} icon={<CheckIcon />} />
            </div>
            <p className="text-center text-xs mt-6 text-white/30 tracking-widest uppercase">
              Zero-knowledge proof pipeline — identity never exposed
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function FlowNode({ label, sublabel, color, delay, icon }: { label: string; sublabel: string; color: 'purple' | 'cyan' | 'green'; delay: number; icon: React.ReactNode }) {
  const styles = {
    purple: { bg: 'rgba(124,58,237,0.2)', border: 'rgba(124,58,237,0.35)', text: '#9d67ff', anim: 'animate-flow-node' },
    cyan: { bg: 'rgba(6,182,212,0.15)', border: 'rgba(6,182,212,0.3)', text: '#22d3ee', anim: 'animate-flow-node-cyan' },
    green: { bg: 'rgba(34,197,94,0.15)', border: 'rgba(34,197,94,0.3)', text: '#4ade80', anim: 'animate-flow-node' },
  }[color];

  return (
    <div className="flex flex-col items-center gap-2.5 animate-fade-in" style={{ animationDelay: `${delay * 0.15 + 0.5}s` }}>
      <div className={`w-14 h-14 rounded-xl flex items-center justify-center ${styles.anim}`} style={{ background: styles.bg, border: `1px solid ${styles.border}`, color: styles.text, animationDelay: `${delay * 0.3}s` }}>
        {icon}
      </div>
      <div className="text-center">
        <div className="text-sm font-semibold font-mono" style={{ color: styles.text }}>{label}</div>
        <div className="text-xs mt-0.5 text-white/35">{sublabel}</div>
      </div>
    </div>
  );
}

function FlowArrow({ delay }: { delay: number }) {
  return (
    <div className="flex items-center justify-center animate-fade-in" style={{ animationDelay: `${delay * 0.15 + 0.6}s` }} aria-hidden="true">
      <div className="md:hidden flex flex-col items-center gap-1 py-1">
        <div className="w-px h-4 bg-white/10" />
        <svg width="10" height="6" viewBox="0 0 10 6" fill="none"><path d="M0 0l5 6 5-6" fill="rgba(255,255,255,0.2)" /></svg>
      </div>
      <div className="hidden md:flex items-center gap-1">
        <div className="h-px w-6 bg-white/10" />
        <svg width="8" height="12" viewBox="0 0 8 12" fill="none" className="animate-arrow" style={{ animationDelay: `${delay * 0.3 + 0.2}s` }}>
          <path d="M0 6h6M3 3l3 3-3 3" stroke="rgba(124,58,237,0.6)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <div className="h-px w-6 bg-white/10" />
      </div>
    </div>
  );
}

function LockIcon() { return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /><circle cx="12" cy="16" r="1" fill="currentColor" /></svg>; }
function BoltIcon() { return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>; }
function ShieldIcon() { return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><path d="m9 12 2 2 4-4" /></svg>; }
function DbIcon() { return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5" /><path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3" /></svg>; }
function CheckIcon() { return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><path d="m9 11 3 3L22 4" /></svg>; }
