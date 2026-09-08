import { Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

// Backend runs via `uvicorn app.main:app --reload` on port 8000 by default (see README).
const API_BASE = 'http://localhost:8000';

type Strategy = 'current' | 'structure-aware';

interface SearchFilters {
  dietary_tags?: string[];
}

interface Citation {
  chunk_id: string;
}

interface ChatResponse {
  answer: string;
  refused: boolean;
  citations: Citation[];
  retrieved_chunk_ids: string[];
}

interface SearchResultItem {
  chunk_id: string;
  score: number;
  recipe_id: string;
  section: string;
  source_file: string;
  text: string;
}

interface SearchResponse {
  results: SearchResultItem[];
}

const DIETARY_TAG_OPTIONS = ['', 'vegan', 'vegetarian', 'contains-dairy', 'contains-eggs', 'contains-nuts'];

@Component({
  selector: 'app-root',
  imports: [FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  private readonly http = inject(HttpClient);

  protected readonly dietaryTagOptions = DIETARY_TAG_OPTIONS;

  question = signal('What vessel is used to bake the Sourdough Country Loaf?');
  strategy = signal<Strategy>('structure-aware');
  dietaryTag = signal('');

  loading = signal(false);
  error = signal('');
  chatResponse = signal<ChatResponse | null>(null);
  retrievedChunks = signal<SearchResultItem[]>([]);
  showChunks = signal(false);

  private buildFilters(): SearchFilters {
    return this.dietaryTag() ? { dietary_tags: [this.dietaryTag()] } : {};
  }

  ask(): void {
    if (!this.question().trim()) {
      return;
    }
    this.loading.set(true);
    this.error.set('');
    this.chatResponse.set(null);
    this.retrievedChunks.set([]);

    const body = {
      question: this.question(),
      strategy: this.strategy(),
      filters: this.buildFilters(),
    };

    this.http.post<ChatResponse>(`${API_BASE}/api/chat`, body).subscribe({
      next: (response) => {
        this.chatResponse.set(response);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(`Request failed: ${err.status ?? ''} ${err.message ?? err}`);
        this.loading.set(false);
      },
    });
  }

  toggleChunks(): void {
    this.showChunks.set(!this.showChunks());
    if (this.showChunks() && this.retrievedChunks().length === 0) {
      const body = {
        question: this.question(),
        top_k: 5,
        strategy: this.strategy(),
        filters: this.buildFilters(),
      };
      this.http.post<SearchResponse>(`${API_BASE}/api/search`, body).subscribe({
        next: (response) => this.retrievedChunks.set(response.results),
        error: (err) => this.error.set(`Search failed: ${err.status ?? ''} ${err.message ?? err}`),
      });
    }
  }
}
