const BASE = import.meta.env.VITE_API_BASE || '';

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
  insights?: string[];
}

export interface NextFixture {
  fixture_id: number;
  opponent: string;
  venue: string;
  date: string;
  competition: string;
}

export interface TeamForm {
  team: string;
  goals_scored: number;
  goals_conceded: number;
  shots: number;
  shots_on_target: number;
  shot_distance: number;
}

export interface MatchAnalysis {
  prediction: PredictionResult;
  real_madrid_form: TeamForm;
  opponent_form: TeamForm;
  key_factors: string[];
  ai_narrative: string;
}

export interface Fixture {
  matchday: number;
  date: string;
  opponent: string;
  venue: 'Home' | 'Away';
  kickoff: string | null;
  api_source: boolean;
  status?: 'upcoming' | 'finished';
  result?: 'W' | 'D' | 'L';
  score?: string;
}

export interface SeasonInfo {
  season: string;
  competition: string;
  start_date: string | null;
  end_date: string | null;
  next_match: Fixture | null;
  fixtures: Fixture[];
}

export interface MatchResult {
  date: string;
  opponent: string;
  venue: string;
  score: string;
  result: 'W' | 'D' | 'L';
}

export interface ChatResponse {
  response: string;
  conversation_id: string;
}

export interface HistoryMessage {
  role: string;
  content: string;
  created_at: string | null;
}

export interface StandingRow {
  position: number;
  team: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
  form: string[];
}

export interface SeasonMatch {
  date: string;
  opponent: string;
  venue: string;
  result: 'W' | 'D' | 'L';
  gf: number;
  ga: number;
}

export interface H2HRecord {
  opponent: string;
  meetings: number;
  rm_wins: number;
  draws: number;
  opponent_wins: number;
  rm_goals: number;
  opponent_goals: number;
  recent: SeasonMatch[];
}

export interface ConversationSummary {
  conversation_id: string;
  last_message: string;
  message_count: number;
  updated_at: string | null;
}

export interface CallFrame {
  timestamp: number;
  file: string;
}

export interface CallReasoningStep {
  timestamp: number;
  observation: string;
  assessment: string;
}

export interface CallResult {
  verdict: 'correct_call' | 'incorrect_call' | 'unclear';
  decision_type: string;
  confidence: number;
  summary: string;
  reasoning: CallReasoningStep[];
  laws_cited?: string[];
  key_frames: { timestamp: number; caption: string }[];
  frame_count?: number;
  job_id?: string;
  competition?: string;
  frames?: CallFrame[];
}

export interface CallJob {
  job_id: string;
  status: 'queued' | 'extracting' | 'analyzing' | 'done' | 'error';
  progress: number;
  error: string | null;
  result: CallResult | null;
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
  chat: (prompt: string, conversationId?: string, userId?: string) =>
    request<ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify({ message: prompt, conversation_id: conversationId, user_id: userId }),
    }),

  getConversation: (conversationId: string) =>
    request<{ conversation_id: string; messages: HistoryMessage[] }>(
      `/conversations/${conversationId}`
    ),

  getConversations: (userId: string) =>
    request<{ user_id: string; conversations: ConversationSummary[] }>(
      `/conversations?user_id=${encodeURIComponent(userId)}`
    ),

  streamChat: async (
    message: string,
    conversationId: string | undefined,
    userId: string | undefined,
    handlers: {
      onDelta: (text: string) => void;
      onTool: (name: string) => void;
      onDone: (conversationId: string) => void;
      onError: (message: string) => void;
    },
    signal?: AbortSignal,
  ) => {
    const res = await fetch(`${BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, conversation_id: conversationId, user_id: userId }),
      signal,
    });
    if (!res.ok || !res.body) {
      throw new Error(`API Error: ${res.status} ${res.statusText}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split('\n\n');
      buffer = chunks.pop() ?? '';
      for (const chunk of chunks) {
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data: ')) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === 'delta') handlers.onDelta(event.content);
            else if (event.type === 'tool') handlers.onTool(event.name);
            else if (event.type === 'done') handlers.onDone(event.conversation_id);
            else if (event.type === 'error') handlers.onError(event.message);
          } catch {
            // skip malformed/partial frames
          }
        }
      }
    }
  },

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

  predictWithAnalysis: (opponent: string, venue: string, date: string) =>
    request<MatchAnalysis>('/predict/analysis', {
      method: 'POST',
      body: JSON.stringify({ opponent, venue, date }),
    }),

  getSeason: () => request<SeasonInfo>('/season'),

  getResults: (limit: number = 5) =>
    request<{ results: MatchResult[] }>(`/results?limit=${limit}`),

  getStandings: (season?: number) =>
    request<{ season: number | null; available_seasons: number[]; standings: StandingRow[] }>(
      `/standings${season ? `?season=${season}` : ''}`
    ),

  getForm: (team: string, season?: number, limit: number = 5) => {
    const params = new URLSearchParams({ team });
    if (season) params.set('season', String(season));
    params.set('limit', String(limit));
    return request<{ team: string; form: string[] }>(`/form?${params.toString()}`);
  },

  getHistory: (season?: number) =>
    request<{ season: number | null; available_seasons: number[]; matches: SeasonMatch[] }>(
      `/history${season ? `?season=${season}` : ''}`
    ),

  getH2H: (opponent: string) =>
    request<H2HRecord>(`/h2h?opponent=${encodeURIComponent(opponent)}`),

  analyzeCall: (
    youtubeUrl?: string,
    note?: string,
    file?: File,
    competition: string = 'La Liga',
    decisionType: string = 'auto'
  ) => {
    const form = new FormData();
    if (youtubeUrl) form.append('youtube_url', youtubeUrl);
    if (note) form.append('note', note);
    if (file) form.append('video', file);
    form.append('competition', competition);
    form.append('decision_type', decisionType);
    return fetch(`${BASE}/calls/analyze`, { method: 'POST', body: form }).then((res) => {
      if (!res.ok) return res.json().then((e) => Promise.reject(new Error(e.detail ?? 'Upload failed')));
      return res.json() as Promise<CallJob>;
    });
  },

  getCall: (jobId: string) => request<CallJob>(`/calls/${jobId}`),

  callFrameUrl: (jobId: string, filename: string) => `${BASE}/calls/${jobId}/frames/${filename}`,
};
