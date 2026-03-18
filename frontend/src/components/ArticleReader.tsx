// File: frontend/src/components/ArticleReader.tsx
import { Article } from '@/api/client';
import { CategoryBadge } from './CategoryBadge';
import { X, ExternalLink } from 'lucide-react';

interface ArticleReaderProps {
  article: Article;
  onClose: () => void;
}

export function ArticleReader({ article, onClose }: ArticleReaderProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-8 pb-8 animate-fade-in-up"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" />

      {/* Modal */}
      <div
        className="relative w-full max-w-2xl max-h-[85vh] mx-4 glass-card overflow-y-auto custom-scrollbar"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 p-2 rounded-full bg-background/60 backdrop-blur-sm hover:bg-background/80 transition-colors z-10"
          aria-label="Close"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Compact header with inline image */}
        <div className="p-6 pb-0 space-y-3">
          <div className="flex items-center gap-2 flex-wrap">
            <CategoryBadge category={article.category} />
            {article.published && (
              <span className="text-xs text-muted-foreground">
                {new Date(article.published).toLocaleDateString('en-US', {
                  year: 'numeric', month: 'long', day: 'numeric',
                })}
              </span>
            )}
          </div>

          <h2 className="text-xl font-bold leading-tight">{article.title}</h2>

          {article.author && (
            <p className="text-sm text-muted-foreground">By {article.author}</p>
          )}
        </div>

        {/* Image between header and content — smaller, rounded */}
        {article.image_url && (
          <div className="px-6 pt-4">
            <img
              src={article.image_url}
              alt={article.title}
              className="w-full h-40 object-cover rounded-lg"
            />
          </div>
        )}

        {/* Article body */}
        <div className="p-6 pt-4 space-y-4">
          {article.content && (
            <div className="text-sm text-foreground/90 leading-relaxed whitespace-pre-line">
              {article.content}
            </div>
          )}

          <a
            href={article.link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
          >
            Read on Managing Madrid <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
}
