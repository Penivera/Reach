import React from 'react';
import { SlideLayout } from '../SlideLayout';

export const Slide10Closing: React.FC<{ slideNumber: number; totalSlides: number }> = ({
  slideNumber,
  totalSlides,
}) => {
  return (
    <SlideLayout
      variant="dark"
      slideNumber={slideNumber}
      totalSlides={totalSlides}
      kicker="REACH"
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          textAlign: 'center',
          marginInline: 'auto',
          maxWidth: '750px',
        }}
      >
        <div
          style={{
            fontSize: 'clamp(44px, 6.5vw, 76px)',
            fontWeight: 800,
            letterSpacing: '-0.035em',
            lineHeight: 1.05,
            color: '#ffffff',
            marginBottom: '28px',
          }}
        >
          <div>YOUR MONEY.</div>
          <div>YOUR WORK.</div>
          <div style={{ color: '#f97316' }}>SETTLED.</div>
        </div>

        <p
          style={{
            fontSize: 'clamp(16px, 1.8vw, 21px)',
            color: '#94a3b8',
            fontWeight: 400,
            lineHeight: 1.5,
            margin: '0 0 36px 0',
          }}
        >
          Trustless escrow for Africa's local service economy.
        </p>

        <div
          style={{
            width: '60px',
            height: '2px',
            background: '#334155',
            marginBottom: '32px',
          }}
        />

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            fontSize: '15px',
            fontFamily: "'JetBrains Mono', monospace",
            flexWrap: 'wrap',
            justifyContent: 'center',
          }}
        >
          <a
            href="https://reachapp.xyz"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              color: '#ffffff',
              textDecoration: 'none',
              fontWeight: 600,
              letterSpacing: '0.05em',
            }}
          >
            reachapp.xyz
          </a>
          <span style={{ color: '#475569' }}>·</span>
          <a
            href="mailto:hello@peni.dev"
            style={{
              color: '#ea580c',
              textDecoration: 'none',
              fontWeight: 600,
              letterSpacing: '0.05em',
            }}
          >
            hello@peni.dev
          </a>
        </div>
      </div>
    </SlideLayout>
  );
};
