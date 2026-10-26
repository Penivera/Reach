import React from 'react';
import { SlideLayout } from '../SlideLayout';
import { Card } from '../Card';
import { CountUp } from '../CountUp';

export const Slide7Revenue: React.FC<{ slideNumber: number; totalSlides: number }> = ({
  slideNumber,
  totalSlides,
}) => {
  const streams = [
    {
      pct: '2.5%',
      title: 'Task Creation Fee',
      desc: 'Charged upfront when escrow PDA is funded. Diverts directly into the on-chain protocol fee vault.',
      badge: 'BPS: 250',
    },
    {
      pct: '5.0%',
      title: 'Platform Commission',
      desc: 'Deducted from the approved provider payout upon successful completion of the assignment.',
      badge: 'BPS: 500',
    },
    {
      pct: '10.0%',
      title: 'Cancellation Fee',
      desc: 'Charged if creator cancels an active task after provider assignment to protect worker time.',
      badge: 'BPS: 1000',
    },
  ];

  return (
    <SlideLayout
      variant="light"
      slideNumber={slideNumber}
      totalSlides={totalSlides}
      kicker="REVENUE MODEL"
      headline="Transparent, On-Chain Revenue."
      summary="Protocol revenue is enforced by smart contract logic and accumulates in a publicly auditable fee vault."
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: '16px',
          }}
        >
          {streams.map((s, idx) => (
            <Card
              key={idx}
              variant="light"
              badge={s.badge}
              badgeVariant="orange"
              index={idx}
            >
              <div
                style={{
                  fontSize: 'clamp(36px, 4vw, 48px)',
                  fontWeight: 800,
                  letterSpacing: '-0.03em',
                  color: '#ea580c',
                  lineHeight: 1.1,
                  margin: '8px 0',
                }}
              >
                <CountUp value={s.pct} />
              </div>
              <h3
                style={{
                  fontSize: '17px',
                  fontWeight: 700,
                  color: '#0f172a',
                  margin: '0 0 6px 0',
                }}
              >
                {s.title}
              </h3>
              <p
                style={{
                  fontSize: '13.5px',
                  color: '#64748b',
                  lineHeight: 1.5,
                  margin: 0,
                }}
              >
                {s.desc}
              </p>
            </Card>
          ))}
        </div>

        {/* On-Chain Vault Guarantee Card */}
        <Card
          variant="light"
          style={{
            background: '#0f172a',
            borderColor: '#334155',
            color: '#ffffff',
          }}
          index={3}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            <div>
              <div
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '11px',
                  fontWeight: 700,
                  color: '#ea580c',
                  letterSpacing: '0.15em',
                  textTransform: 'uppercase',
                  marginBottom: '4px',
                }}
              >
                VERIFIABLE BALANCE SHEET
              </div>
              <div style={{ fontSize: '15px', fontWeight: 600, color: '#f8fafc' }}>
                All protocol fees collect directly into the Anchor Fee Vault PDA.
              </div>
            </div>
            <span className="cf-badge cf-badge-orange">SOLANA MAINNET PDA</span>
          </div>
        </Card>
      </div>
    </SlideLayout>
  );
};
