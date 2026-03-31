import React, { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { registerSW } from 'virtual:pwa-register'

// Register the service worker for PWA support (auto-updates silently in background)
registerSW({ immediate: true })


class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ error, errorInfo });
    console.error("Uncaught error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', color: 'red' }}>
          <h1>Something went wrong.</h1>
          <details style={{ whiteSpace: 'pre-wrap' }}>
            {this.state.error && this.state.error.toString()}
            <br />
            {this.state.errorInfo && this.state.errorInfo.componentStack}
          </details>
        </div>
      );
    }

    return this.props.children;
  }
}

import { LexPlayProvider } from './features/lexplay'
import { ClerkProvider } from '@clerk/clerk-react'
import { SubscriptionProvider } from './context/SubscriptionContext'

// Import your publishable key
const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

if (!PUBLISHABLE_KEY) {
  console.error("CRITICAL: Missing VITE_CLERK_PUBLISHABLE_KEY.");
  // Render a user-friendly error instead of a white screen
  createRoot(document.getElementById('root')).render(
    <div style={{ padding: '40px', textAlign: 'center', fontFamily: 'sans-serif' }}>
      <h1 style={{ color: '#e11d48' }}>Configuration Error</h1>
      <p>The application is missing a required security key (Clerk Publishable Key).</p>
      <p style={{ fontSize: '0.9rem', color: '#666' }}>Please check your environment variables or GitHub Secrets.</p>
    </div>
  );
  throw new Error("Missing Publishable Key");
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <ClerkProvider publishableKey={PUBLISHABLE_KEY} afterSignOutUrl="/">
        <SubscriptionProvider>
          <LexPlayProvider>
            <App />
          </LexPlayProvider>
        </SubscriptionProvider>
      </ClerkProvider>
    </ErrorBoundary>
  </StrictMode>,
)
