// File: frontend/src/components/ArticleCard.tsx
import { Article } from '@/api/client';
import { CategoryBadge } from './CategoryBadge';
import { cn } from '@/lib/utils';

function timeAgo(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

interface ArticleCardProps {
  article: Article;
  onClick?: () => void;
  className?: string;
}

export function ArticleCard({ article, onClick, className }: ArticleCardProps) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
      className={cn(
        'glass-card block overflow-hidden group transition-transform hover:scale-[1.01] cursor-pointer',
        className
      )}
    >
      {/* Hero image */}
      {article.image_url && (
        <div className="relative w-full h-48 overflow-hidden">
          <img
            src={article.image_url}
            alt={article.title}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            loading="lazy"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-background/90 via-background/20 to-transparent" />
          <div className="absolute bottom-3 left-3">
            <CategoryBadge category={article.category} />
          </div>
        </div>
      )}

      <div className="p-5 space-y-2">
        {!article.image_url && (
          <div className="flex items-center gap-2">
            <CategoryBadge category={article.category} />
            {article.published && (
              <span className="text-xs text-muted-foreground">{timeAgo(article.published)}</span>
            )}
          </div>
        )}

        {article.image_url && article.published && (
          <span className="text-xs text-muted-foreground">{timeAgo(article.published)}</span>
        )}

        <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors leading-snug">
          {article.title}
        </h3>

        {article.content && (
          <p className="text-sm text-muted-foreground line-clamp-2">{article.content}</p>
        )}

        {article.author && (
          <p className="text-xs text-muted-foreground pt-1">By {article.author}</p>
        )}
      </div>
    </div>
  );
}
