import React from 'react';
import { SlideLayout } from '../SlideLayout';

export const Slide8Architecture: React.FC<{ slideNumber: number; totalSlides: number }> = ({
  slideNumber,
  totalSlides,
}) => {
  const layers = [
    {
      num: '01',
      layer: 'FRONTEND',
      tech: 'Next.js 16 + React 19 + TypeScript + Tailwind v4',
      detail: 'PWA-enabled, responsive mobile interface with end-to-end type safety.',
    },
    {
      num: '02',
      layer: 'BACKEND',
      tech: 'FastAPI (async) + SQLAlchemy 2.0 + asyncpg + Pydantic v2',
      detail: 'High-throughput async Python service with custodial transaction engine.',
    },
    {
      num: '03',
      layer: 'DATA PLANE',
      tech: 'PostgreSQL + PostGIS + Redis Cache',
      detail: 'Spatial indexing for millisecond-level nearby matching and query acceleration.',
    },
    {
      num: '04',
      layer: 'ESCROW CONTRACT',
      tech: 'Solana Anchor Program (Rust, 2,300+ LOC)',
      detail: 'Canonical escrow, provider collateral, debt tracking, and dispute splits.',
    },
    {
      num: '05',
      layer: 'INTEGRATIONS',
      tech: 'Obiex API + FossaPay + Firebase Push + Cloudinary',
      detail: 'Naira checkout, bank payouts, biometric KYC, and instant dispatch notifications.',
    },
  ];

  return (
    <SlideLayout
      variant="dark"
      slideNumber={slideNumber}
      totalSlides={totalSlides}
      kicker="TECHNICAL ARCHITECTURE"
      headline="Built for Scale and Trust."
      summary="158 backend tests passing. Dual-custody treasury management. Production-ready codebase."
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {layers.map((l, idx) => (
          <div
            key={idx}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 18px',
              borderRadius: '8px',
              background: '#1e293b',
              border: '1px solid #334155',
              gap: '16px',
              flexWrap: 'wrap',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              <span
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '11px',
                  fontWeight: 700,
                  color: '#ea580c',
                  letterSpacing: '0.1em',
                }}
              >
                {l.num} · {l.layer}
              </span>
              <span
                style={{
                  fontSize: '14.5px',
                  fontWeight: 600,
                  color: '#f8fafc',
                }}
              >
                {l.tech}
              </span>
            </div>
            <span style={{ fontSize: '12.5px', color: '#94a3b8' }}>
              {l.detail}
            </span>
          </div>
        ))}
      </div>
    </SlideLayout>
  );
};
