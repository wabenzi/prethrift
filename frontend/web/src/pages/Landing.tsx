import { useEffect, useState } from 'react';

const LOGO_SRC = '/logo.svg';
const GEO_API = 'https://ipapi.co/json/';

const countries = [
  { code: 'US', name: 'United States' },
  { code: 'GB', name: 'United Kingdom' },
  { code: 'IN', name: 'India' },
  { code: 'DE', name: 'Germany' },
  { code: 'FR', name: 'France' },
  // ...add more as needed
];

export default function Landing() {
  const [country, setCountry] = useState('US');
  const [query, setQuery] = useState('');

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch(GEO_API, { method: 'GET' });
        if (!res.ok) return; // ignore silently
        interface GeoResponse {
          country_code?: string;
        }
        const data = (await res.json()) as GeoResponse | null;
        const code = data?.country_code;
        // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition -- cancellation flag can change before async resolves
        if (!cancelled && typeof code === 'string') {
          setCountry(code);
        }
      } catch {
        // ignore network errors for now
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div style={{ minHeight: '100vh', background: '#f5f1eb' }}>
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '24px 48px 12px 48px',
          background: '#fff',
          boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}
      >
        <img src={LOGO_SRC} alt="Prethrift Logo" style={{ height: 48 }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <select
            value={country}
            onChange={(e) => {
              setCountry(e.target.value);
            }}
            style={{
              fontSize: 16,
              padding: '6px 12px',
              borderRadius: 8,
              border: '1px solid #d4af37',
            }}
          >
            {countries.map((c) => {
              return (
                <option key={c.code} value={c.code}>
                  {c.name}
                </option>
              );
            })}
          </select>
          <button
            style={{
              background: '#d4af37',
              color: '#fff',
              fontWeight: 600,
              border: 'none',
              borderRadius: 8,
              padding: '10px 24px',
              fontSize: 16,
              cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(212,175,55,0.08)',
            }}
          >
            Sign Up
          </button>
        </div>
      </header>
      <main
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '70vh',
        }}
      >
        <h1
          style={{
            fontFamily: 'Georgia,serif',
            fontWeight: 700,
            fontSize: '2.5rem',
            color: '#2c1810',
            margin: '60px 0 24px 0',
            textAlign: 'center',
          }}
        >
          Prethrift
          <div style={{ fontSize: '1.25rem', fontWeight: 400, marginTop: 12 }}>
            Shop the source.
          </div>
        </h1>
        <form
          style={{ width: '100%', maxWidth: 520, margin: '0 auto' }}
          onSubmit={(e) => {
            e.preventDefault(); /* handle search */
          }}
        >
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
            }}
            placeholder="Search for vintage bags, watches, stories..."
            style={{
              width: '100%',
              fontSize: 22,
              padding: '22px 28px',
              borderRadius: 32,
              border: '2px solid #d4af37',
              boxShadow: '0 4px 24px rgba(44,24,16,0.06)',
              outline: 'none',
              marginBottom: 16,
            }}
          />
        </form>
        <div style={{ color: '#6d4423', fontStyle: 'italic', fontSize: 16, marginBottom: 40 }}>
          Try: "Chanel 90s bag", "Rolex story", "Paris flea market"
        </div>
        {/* Placeholder for visual language: slideshow, carousel, etc. */}
        <section style={{ width: '100%', maxWidth: 900, margin: '0 auto', marginTop: 40 }}>
          {/* Option 1: Slideshow of Curated Finds */}
          <div style={{ display: 'flex', gap: 32, overflowX: 'auto', padding: 8 }}>
            {[1, 2, 3].map((i) => {
              return (
                <div
                  key={i}
                  style={{
                    minWidth: 240,
                    background: '#fff',
                    borderRadius: 18,
                    boxShadow: '0 2px 12px rgba(44,24,16,0.07)',
                    padding: 18,
                    textAlign: 'center',
                  }}
                >
                  <div
                    style={{
                      height: 160,
                      background: '#e8ddd4',
                      borderRadius: 12,
                      marginBottom: 12,
                    }}
                  />
                  <div style={{ fontWeight: 600, color: '#2c1810', fontSize: 18 }}>
                    Curated Find #{i}
                  </div>
                  <div style={{ color: '#6d4423', fontSize: 14, marginTop: 4 }}>
                    Brand, year, story...
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </main>
    </div>
  );
}
