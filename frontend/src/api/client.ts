const BASE = '';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API Error: ${res.status} ${res.statusText}`);
  return res.json();
}

export interface PredictionResult {
  win: number;
  draw: number;
  loss: number;
}

export interface NextFixture {
  fixture_id: number;
  opponent: string;
  venue: string;
  date: string;
  competition: string;
}

export interface ChatResponse {
  response: string;
}

export interface CommentaryItem {
  minute: number | string;
  type: string;
  text: string;
}

export interface FixtureInfo {
  fixture_id: number;
  home: string;
  away: string;
  score_home: number | null;
  score_away: number | null;
  status: string;
  elapsed: number | null;
}

export interface CommentaryResponse {
  fixture: FixtureInfo | null;
  commentary: CommentaryItem[];
  event_count: number;
}

// Adapted shape for LiveMatch page consumption
export interface LiveMatchData {
  match_status?: string;
  home_team?: string;
  away_team?: string;
  score?: string;
  events?: MatchEvent[];
  message?: string;
}

export interface MatchEvent {
  minute: number | string;
  type: string;
  player: string;
  commentary: string;
}

export interface Article {
  article_id: string;
  title: string;
  category: string;
  author: string | null;
  published: string | null;
  content: string | null;
  image_url: string | null;
  link: string;
}

function transformCommentary(raw: CommentaryResponse): LiveMatchData {
  if (!raw.fixture) {
    return { message: 'No live match right now' };
  }
  return {
    match_status: raw.fixture.status,
    home_team: raw.fixture.home,
    away_team: raw.fixture.away,
    score: `${raw.fixture.score_home ?? 0} - ${raw.fixture.score_away ?? 0}`,
    events: raw.commentary.map((c) => ({
      minute: c.minute,
      type: c.type,
      player: '',
      commentary: c.text,
    })),
  };
}

export const api = {
  chat: (prompt: string) =>
    request<ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify({ message: prompt }),
    }),

  predict: (opponent: string, venue: string, date: string) =>
    request<PredictionResult>('/predict', {
      method: 'POST',
      body: JSON.stringify({ opponent, venue, date }),
    }),

  getCommentary: async (teamId: number = 541): Promise<LiveMatchData> => {
    const raw = await request<CommentaryResponse>(`/commentary?team_id=${teamId}`);
    return transformCommentary(raw);
  },

  getArticles: (params?: { category?: string; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.category && params.category !== 'All') searchParams.set('category', params.category);
    if (params?.limit) searchParams.set('limit', String(params.limit));
    const qs = searchParams.toString();
    return request<Article[]>(`/articles${qs ? `?${qs}` : ''}`);
  },

  getHealth: () => request<{ status: string; db: string; ollama: string }>('/health'),

  getNextFixture: () => request<NextFixture | null>('/next-fixture'),
};
