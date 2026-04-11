import Nav from '@/components/nav';
import Hero from '@/components/hero';
import ValueProps from '@/components/value-props';
import CodeSnippet from '@/components/code-snippet';
import Pricing from '@/components/pricing';
import CommunityCta from '@/components/community-cta';
import Footer from '@/components/footer';

export default function HomePage() {
  return (
    <>
      <Nav />
      <main id="main-content">
        <Hero />
        <ValueProps />
        <CodeSnippet />
        <Pricing />
        <CommunityCta />
      </main>
      <Footer />
    </>
  );
}
