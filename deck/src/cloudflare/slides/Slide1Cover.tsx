import React from 'react';
import { SlideLayout } from '../SlideLayout';

export const Slide1Cover: React.FC<{ slideNumber: number; totalSlides: number }> = ({
  slideNumber,
  totalSlides,
}) => {
  return (
    <SlideLayout
      variant="dark"
      slideNumber={slideNumber}
      totalSlides={totalSlides}
      kicker="LOCAL SERVICES & ESCROW"
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
          justifyContent: 'center',
          height: '100%',
          paddingLeft: 'clamp(8px, 1vw, 24px)',
        }}
      >
        <h1
          style={{
            fontSize: 'clamp(56px, 8vw, 92px)',
            fontWeight: 800,
            letterSpacing: '-0.04em',
            lineHeight: 1,
            margin: '0 0 20px 0',
            color: '#ffffff',
          }}
        >
          REACH
        </h1>

        <p
          style={{
            fontSize: 'clamp(20px, 2.5vw, 28px)',
            color: '#94a3b8',
            fontWeight: 400,
            letterSpacing: '-0.015em',
            margin: '0 0 32px 0',
            maxWidth: '24ch',
          }}
        >
          Find anything, Close to home.
        </p>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            flexWrap: 'wrap',
          }}
        >
          <span className="cf-badge cf-badge-orange">SOLANA ESCROW</span>
          <span className="cf-badge cf-badge-slate">FIAT RAILS</span>
          <span className="cf-badge cf-badge-slate">POSTGIS MATCHING</span>
        </div>
      </div>
    </SlideLayout>
  );
};
