import React, { type ReactNode } from 'react';

export interface SlideLayoutProps {
  kicker?: string;
  headline?: ReactNode;
  summary?: string;
  variant?: 'light' | 'dark';
  children: ReactNode;
  slideNumber: number;
  totalSlides: number;
}

export const SlideLayout: React.FC<SlideLayoutProps> = ({
  kicker,
  headline,
  summary,
  variant = 'light',
  children,
  slideNumber,
  totalSlides,
}) => {
  const isDark = variant === 'dark';
  const progressPercent = ((slideNumber) / totalSlides) * 100;

  return (
    <div
      className="cf-slide-wrapper"
      style={{
        backgroundColor: isDark ? '#0f172a' : '#ffffff',
        color: isDark ? '#ffffff' : '#0f172a',
      }}
    >
      <div className="cf-slide-container">
        {/* Consistent Top Header Zone */}
        <header className="cf-slide-header">
          {kicker && <div className="cf-kicker">{kicker}</div>}
          {headline && (
            <h1
              className="cf-headline"
              style={{ color: isDark ? '#ffffff' : '#0f172a' }}
            >
              {headline}
            </h1>
          )}
        </header>

        {/* Vertically Centered Main Content Area */}
        <main className="cf-slide-body">{children}</main>

        {/* Consistent Bottom Summary Footer Zone */}
        <footer className="cf-slide-footer">
          {summary && (
            <div
              style={{
                color: isDark ? '#94a3b8' : '#64748b',
                maxWidth: '75ch',
              }}
            >
              {summary}
            </div>
          )}
        </footer>
      </div>

      {/* Slide Index Counter */}
      <div
        className="cf-counter"
        style={{ color: isDark ? '#64748b' : '#94a3b8' }}
      >
        {slideNumber} / {totalSlides}
      </div>

      {/* Progress Bar at bottom */}
      <div
        className="cf-progress-bar"
        style={{ width: `${progressPercent}%` }}
      />
    </div>
  );
};
