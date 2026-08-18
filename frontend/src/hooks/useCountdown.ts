import { useEffect, useState } from 'react';

export interface CountdownParts {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  isPast: boolean;
}

export function useCountdown(targetIso: string | null | undefined): CountdownParts {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const target = targetIso ? new Date(targetIso).getTime() : null;
  const diff = target ? target - now : 0;
  const abs = Math.max(0, diff);

  return {
    days: Math.floor(abs / 86_400_000),
    hours: Math.floor(abs / 3_600_000) % 24,
    minutes: Math.floor(abs / 60_000) % 60,
    seconds: Math.floor(abs / 1_000) % 60,
    isPast: diff < 0,
  };
}

/** Fixture kickoff time — real kickoff when known, else 20:00 local. */
export function fixtureTargetIso(fixture: { kickoff?: string | null; date: string }): string {
  return fixture.kickoff || `${fixture.date}T20:00:00`;
}
