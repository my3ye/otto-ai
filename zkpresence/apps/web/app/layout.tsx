import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'zkPresence — Zero-Knowledge Attendance Protocol',
  description: 'Prove you attended. Reveal nothing. Open-source ZK attendance protocol built on SP1.',
  keywords: ['zero-knowledge', 'attendance', 'ZK proof', 'SP1', 'blockchain', 'privacy', 'open source'],
  authors: [{ name: 'MY3YE' }],
  openGraph: {
    title: 'zkPresence — Zero-Knowledge Attendance Protocol',
    description: 'Prove you attended. Reveal nothing. Open-source ZK attendance protocol built on SP1.',
    url: 'https://zkpresence.xyz',
    siteName: 'zkPresence',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'zkPresence — Zero-Knowledge Attendance Protocol',
    description: 'Prove you attended. Reveal nothing. Open-source ZK attendance protocol built on SP1.',
    creator: '@my3ye',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:wght@400;500&family=Syne:wght@700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <a href="#main-content" className="skip-to-content">Skip to main content</a>
        <div className="noise-overlay" aria-hidden="true" />
        {children}
      </body>
    </html>
  );
}
