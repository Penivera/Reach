import React from 'react';
import { SlideLayout } from '../SlideLayout';
import { Card } from '../Card';

export const Slide2Problem: React.FC<{ slideNumber: number; totalSlides: number }> = ({
  slideNumber,
  totalSlides,
}) => {
  const painPoints = [
    {
      num: '01',
      title: 'No Discovery Hub',
      desc: 'No single platform to find nearby specialists, dispatch errands, or rent an extra set of hands.',
    },
    {
      num: '02',
      title: 'No Payment Guarantee',
      desc: 'Providers complete physical work with zero contractual assurance of getting paid.',
    },
    {
      num: '03',
      title: 'Upfront Client Risk',
      desc: 'Clients pay before seeing results, with zero recourse or protection if work fails.',
    },
    {
      num: '04',
      title: 'Word-of-Mouth Pricing',
      desc: 'Arbitrary prices with no reliable benchmark or transparent market rates.',
    },
  ];

  const gapPoints = [
    'No verified nearby specialist directory or location radius.',
    'No escrow contracts, no collateral deposits, no legal recourse.',
    'Trust is fragmented across WhatsApp groups and unrecorded phone calls.',
    'A ₦4T+ informal economy operating entirely on hope and social friction.',
  ];

  return (
    <SlideLayout
      variant="light"
      slideNumber={slideNumber}
      totalSlides={totalSlides}
      kicker="THE TRUST GAP"
      headline="Money Moves on Hope. Not Guarantees."
      summary="A ₦4T+ informal services market running entirely on social trust and informal referrals."
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
          gap: '20px',
          alignItems: 'stretch',
        }}
      >
        {/* Left: Status Quo */}
        <Card
          variant="light"
          badge="STATUS QUO"
          badgeVariant="red"
          title={<span style={{ color: '#991b1b' }}>Local Services Today</span>}
          description="How everyday gigs and trade services operate today across urban Nigeria:"
          index={0}
        >
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              marginTop: '16px',
            }}
          >
            {painPoints.map((pt, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  fontSize: '13.5px',
                  lineHeight: '1.45',
                }}
              >
                <span
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    color: '#ea580c',
                    fontWeight: 700,
                    fontSize: '12px',
                    flexShrink: 0,
                    marginTop: '1px',
                  }}
                >
                  {pt.num}
                </span>
                <div>
                  <strong style={{ color: '#0f172a' }}>{pt.title}</strong> —{' '}
                  <span style={{ color: '#64748b' }}>{pt.desc}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Right: The Gap */}
        <Card
          variant="light"
          badge="THE STRUCTURAL GAP"
          badgeVariant="slate"
          title="Why Existing Solutions Fail"
          description="Without programmatic escrow, participants bear unmanageable default risk:"
          index={1}
        >
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
              marginTop: '16px',
            }}
          >
            {gapPoints.map((pt, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  fontSize: '13.5px',
                  lineHeight: '1.5',
                  color: '#64748b',
                }}
              >
                <span style={{ color: '#ea580c', fontWeight: 700 }}>→</span>
                <span>{pt}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </SlideLayout>
  );
};
