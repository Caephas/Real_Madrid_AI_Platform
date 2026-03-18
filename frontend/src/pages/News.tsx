// File: frontend/src/pages/News.tsx
import { useState } from 'react';
import { api, Article } from '@/api/client';
import { useApi } from '@/hooks/useApi';
import { ArticleCard } from '@/components/ArticleCard';
import { ArticleReader } from '@/components/ArticleReader';
import { CardSkeleton } from '@/components/LoadingSkeleton';
import { ErrorBanner } from '@/components/ErrorBanner';
import { cn } from '@/lib/utils';

const CATEGORIES = [
  'All', 'Match Reports', 'Match Previews', 'Transfers',
  'Tactical Analysis', 'Player News', 'Player Interviews', 'Breaking News',
];

export default function News() {
  const [category, setCategory] = useState('All');
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const { data, loading, error, refetch } = useApi(
    () => api.getArticles(category !== 'All' ? { category } : {}),
    [category]
  );

  return (
    <div className="space-y-6 animate-fade-in-up">
      <h1 className="text-3xl font-bold tracking-tight">News Feed</h1>

      {/* Category tabs */}
      <div className="flex gap-2 overflow-x-auto pb-2 custom-scrollbar">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className={cn(
              'px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors border',
              category === cat
                ? 'bg-primary text-primary-foreground border-primary'
                : 'bg-transparent text-muted-foreground border-border hover:border-muted-foreground'
            )}
          >
            {cat}
          </button>
        ))}
      </div>

      {error && <ErrorBanner message="Could not load articles" onRetry={refetch} />}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : data?.length ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.map((article) => (
            <ArticleCard
              key={article.article_id}
              article={article}
              onClick={() => setSelectedArticle(article)}
            />
          ))}
        </div>
      ) : (
        <div className="glass-card p-10 text-center">
          <p className="text-muted-foreground">No articles found in this category</p>
        </div>
      )}

      {/* In-app article reader modal */}
      {selectedArticle && (
        <ArticleReader
          article={selectedArticle}
          onClose={() => setSelectedArticle(null)}
        />
      )}
    </div>
  );
}
