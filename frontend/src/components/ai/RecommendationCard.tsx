"use client";

/* ─────────────────────────────────────────────────────────
 * RECOMMENDATION CARD (article variant)
 * Featured news item with a freshness confidence meter and
 * two actions: read in-app, or open the source article.
 * Adapted from the beautifului.dev RecommendationCard.
 * ───────────────────────────────────────────────────────── */

function Meter({ signal, tone }: { signal: number; tone: string }) {
  return (
    <span className="flex items-end gap-0.5">
      {[0, 1, 2].map((bar) => (
        <span
          key={bar}
          className="w-1 rounded-full transition-colors duration-300"
          style={{ height: 10, background: bar < signal ? tone : "var(--line-strong)" }}
        />
      ))}
    </span>
  );
}

export interface ArticleRecommendation {
  title: string;
  category: string;
  body: string;
  link: string;
  published: string | null;
}

function freshness(published: string | null): number {
  if (!published) return 0;
  const hours = (Date.now() - new Date(published).getTime()) / 3_600_000;
  if (hours < 6) return 3;
  if (hours < 24) return 2;
  if (hours < 72) return 1;
  return 0;
}

const FRESH_LABELS = ["Older", "Recent", "Fresh", "Breaking"];

export default function RecommendationCard({
  article,
  onRead,
}: {
  article: ArticleRecommendation;
  onRead?: () => void;
}) {
  const signal = freshness(article.published);
  const tone = signal >= 2 ? "var(--accent)" : signal === 1 ? "var(--orange)" : "var(--ink-3)";

  return (
    <div className="w-full max-w-95 overflow-hidden rounded-card bg-surface shadow-card">
      <div className="primitive-card-pad">
        <span className="text-[13px] font-semibold text-ink">{article.category}</span>
        <h3 className="mt-1 text-[15px] font-semibold leading-snug text-ink">
          {article.title}
        </h3>
        <p className="mt-1.5 line-clamp-3 text-[13px] leading-relaxed text-ink-2">
          {article.body}
        </p>
      </div>

      <div className="primitive-card-footer flex items-center justify-between gap-3 border-t border-line bg-inset">
        <span className="flex items-center gap-2">
          <Meter signal={signal} tone={tone} />
          <span className="text-[12.5px] font-medium text-ink-2">
            {FRESH_LABELS[signal]}
          </span>
        </span>

        <span className="-mr-0.5 flex items-center gap-2">
          <a
            href={article.link}
            target="_blank"
            rel="noreferrer"
            className="h-7 rounded-control px-2.5 text-[12.5px] font-medium shadow-btn
              bg-surface text-ink transition-[background-color,transform] duration-100
              hover:bg-hover active:scale-[0.96]"
          >
            Source
          </a>
          <button
            type="button"
            onClick={onRead}
            className="h-7 rounded-control px-3 text-[12.5px] font-medium
              bg-accent text-accent-ink transition-[filter,transform] duration-150
              hover:brightness-105 active:scale-[0.96]"
          >
            Read
          </button>
        </span>
      </div>
    </div>
  );
}
