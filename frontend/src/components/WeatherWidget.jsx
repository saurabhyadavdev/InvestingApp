import React, { useEffect, useState } from 'react';

const CITIES = [
  { name: 'Berlin', lat: 52.52, lon: 13.41, tz: 'Europe/Berlin' },
  { name: 'Itarsi', lat: 22.61, lon: 77.77, tz: 'Asia/Kolkata' },
];

const WMO_LABELS = {
  0: 'Clear', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
  45: 'Fog', 48: 'Fog',
  51: 'Drizzle', 53: 'Drizzle', 55: 'Drizzle',
  61: 'Rain', 63: 'Rain', 65: 'Heavy rain',
  71: 'Snow', 73: 'Snow', 75: 'Heavy snow',
  80: 'Showers', 81: 'Showers', 82: 'Heavy showers',
  95: 'Thunderstorm', 96: 'Thunderstorm', 99: 'Thunderstorm',
};

const WMO_ICONS = {
  0: '☀️', 1: '🌤️', 2: '⛅', 3: '☁️',
  45: '🌫️', 48: '🌫️',
  51: '🌦️', 53: '🌦️', 55: '🌧️',
  61: '🌧️', 63: '🌧️', 65: '🌧️',
  71: '🌨️', 73: '🌨️', 75: '❄️',
  80: '🌦️', 81: '🌧️', 82: '⛈️',
  95: '⛈️', 96: '⛈️', 99: '⛈️',
};

function wmoLabel(code) {
  return WMO_LABELS[code] ?? 'Unknown';
}

function wmoIcon(code) {
  return WMO_ICONS[code] ?? '🌡️';
}

function shortDay(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
}

async function fetchWeather(city) {
  const url =
    `https://api.open-meteo.com/v1/forecast` +
    `?latitude=${city.lat}&longitude=${city.lon}` +
    `&daily=weathercode,temperature_2m_max,temperature_2m_min` +
    `&current_weather=true&timezone=${encodeURIComponent(city.tz)}&forecast_days=7`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Weather fetch failed for ${city.name}`);
  return res.json();
}

function CityWeather({ city }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchWeather(city)
      .then(setData)
      .catch(e => setError(e.message));
  }, [city.name]);

  if (error) {
    return (
      <div style={styles.card}>
        <div style={styles.cityName}>{city.name}</div>
        <div style={{ fontSize: 12, color: '#999' }}>Unavailable</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div style={styles.card}>
        <div style={styles.cityName}>{city.name}</div>
        <div style={{ fontSize: 12, color: '#999' }}>Loading…</div>
      </div>
    );
  }

  const cw = data.current_weather;
  const daily = data.daily;
  const todayMax = Math.round(daily.temperature_2m_max[0]);
  const todayMin = Math.round(daily.temperature_2m_min[0]);
  const todayCode = daily.weathercode[0];

  return (
    <div style={styles.card}>
      {/* Today */}
      <div style={styles.todayRow}>
        <span style={styles.cityName}>{city.name}</span>
        <span style={styles.bigIcon}>{wmoIcon(todayCode)}</span>
        <div>
          <div style={styles.tempBig}>{Math.round(cw.temperature)}°C</div>
          <div style={styles.condition}>{wmoLabel(todayCode)}</div>
          <div style={styles.hiLo}>↑{todayMax}° ↓{todayMin}°</div>
        </div>
      </div>

      {/* 7-day strip */}
      <div style={styles.forecastStrip}>
        {daily.time.map((date, i) => (
          <div key={date} style={styles.forecastDay}>
            <div style={styles.dayLabel}>{i === 0 ? 'Today' : shortDay(date)}</div>
            <div style={styles.dayIcon}>{wmoIcon(daily.weathercode[i])}</div>
            <div style={styles.dayTemps}>
              <span style={{ color: '#E76F51' }}>{Math.round(daily.temperature_2m_max[i])}°</span>
              <span style={{ color: 'var(--color-text-secondary)', marginLeft: 4 }}>{Math.round(daily.temperature_2m_min[i])}°</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function WeatherWidget() {
  return (
    <div style={styles.wrapper}>
      {CITIES.map(city => (
        <CityWeather key={city.name} city={city} />
      ))}
    </div>
  );
}

const styles = {
  wrapper: {
    display: 'flex',
    gap: 16,
    padding: '12px 32px',
    flexWrap: 'wrap',
    borderBottom: '1px solid var(--color-border)',
    background: 'var(--color-bg-card)',
  },
  card: {
    flex: 1,
    minWidth: 320,
    background: 'var(--color-bg-card)',
    borderRadius: 8,
    border: '1px solid var(--color-border)',
    padding: '12px 16px',
  },
  todayRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    marginBottom: 10,
  },
  cityName: {
    fontWeight: 700,
    fontSize: 15,
    color: 'var(--color-text-primary)',
    minWidth: 56,
  },
  bigIcon: {
    fontSize: 36,
    lineHeight: 1,
  },
  tempBig: {
    fontSize: 22,
    fontWeight: 700,
    color: 'var(--color-text-primary)',
    lineHeight: 1.1,
  },
  condition: {
    fontSize: 12,
    color: 'var(--color-text-secondary)',
  },
  hiLo: {
    fontSize: 11,
    color: 'var(--color-text-secondary)',
  },
  forecastStrip: {
    display: 'flex',
    gap: 4,
    overflowX: 'auto',
  },
  forecastDay: {
    flex: '0 0 auto',
    minWidth: 58,
    textAlign: 'center',
    padding: '4px 2px',
    borderRadius: 6,
    background: 'var(--color-bg-card)',
  },
  dayLabel: {
    fontSize: 10,
    color: 'var(--color-text-secondary)',
    marginBottom: 2,
    whiteSpace: 'nowrap',
  },
  dayIcon: {
    fontSize: 18,
    lineHeight: 1.2,
  },
  dayTemps: {
    fontSize: 11,
    marginTop: 2,
  },
};
