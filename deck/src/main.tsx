import React from 'react';
import ReactDOM from 'react-dom/client';
import { DeckApp } from './cloudflare/DeckApp';
import StudioApp from './studio/StudioApp';
import './styles/tokens.css';
import './styles/chrome-tokens.css';
import './styles/base.css';
import './styles/chrome.css';

const isStudio = new URLSearchParams(window.location.search).has('studio');

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {isStudio ? <StudioApp /> : <DeckApp />}
  </React.StrictMode>
);
