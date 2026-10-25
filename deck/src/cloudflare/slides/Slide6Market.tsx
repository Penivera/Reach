import React from 'react';
import { SlideLayout } from '../SlideLayout';
import { Card } from '../Card';
import { CountUp } from '../CountUp';

export const Slide6Market: React.FC<{ slideNumber: number; totalSlides: number }> = ({
  slideNumber,
  totalSlides,
}) => {
  const stats = [
    { value: '200M+', label: 'Population', hint: 'Fastest-growing urban market in Africa' },
    { value: '70%', label: 'Under 30', hint: 'Mobile-first, digital native workforce' },
    { value: '#1', label: 'Crypto Adoption', hint: 'Chainalysis Global Adoption Index (Africa)' },
    { value: '₦4T+', label: 'Informal Services', hint: 'Unorganized, cash-heavy addressable TAM' },
  ];

  return (
    <SlideLayout
      variant="light"
      slideNumber={slideNumber}
      totalSlides={totalSlides}
      kicker="MARKET OPPORTUNITY"
      headline="Nigeria's Service Economy Is Massive and Underserved."
      summary="Mobile-first, young, and crypto-fluent. High inflation drives everyday demand for stablecoin earnings."
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* 4 Big Stat Cards */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '16px',
          }}
        >
          {stats.map((s, idx) => (
            <Card key={idx} variant="light" index={idx}>
              <div
                style={{
                  fontSize: 'clamp(32px, 3.8vw, 44px)',
                  fontWeight: 800,
                  letterSpacing: '-0.03em',
                  color: '#ea580c',
                  lineHeight: 1.1,
                  marginBottom: '6px',
                }}
              >
                <CountUp value={s.value} />
              </div>
              <div
                style={{
                  fontSize: '14px',
                  fontWeight: 700,
                  color: '#0f172a',
                  marginBottom: '4px',
                }}
              >
                {s.label}
              </div>
              <div style={{ fontSize: '12px', color: '#64748b', lineHeight: 1.4 }}>
                {s.hint}
              </div>
            </Card>
          ))}
        </div>

        {/* Expansion Strategy Cards */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '16px',
          }}
        >
          <Card
            variant="light"
            badge="PHASE 1 LAUNCH"
            badgeVariant="orange"
            title="Akwa Ibom & Uyo Launchpad"
            description="Emerging digital hub with high artisan density, strong smartphone penetration, and an active, tight-knit service economy."
            index={4}
          />
          <Card
            variant="light"
            badge="EXPANSION PATH"
            badgeVariant="slate"
            title="Regional & National Rollout"
            description="Scale along the South-South corridor (Port Harcourt, Calabar) to Lagos and Abuja, followed by regional West Africa."
            index={5}
          />
        </div>
      </div>
    </SlideLayout>
  );
};
