import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

// Backend runs via `uvicorn app.main:app --reload` on port 8000 by default (see README).
const API_BASE = 'http://localhost:8000';

type Strategy = 'current' | 'structure-aware';
type View = 'query' | 'documents';

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

interface DocumentInfo {
  doc_id: string;
  source_file: string;
  chunk_count: number;
  uploaded_at: string;
}

interface DocumentListResponse {
  documents: DocumentInfo[];
}

const DIETARY_TAG_OPTIONS = ['', 'vegan', 'vegetarian', 'contains-dairy', 'contains-eggs', 'contains-nuts'];

@Component({
  selector: 'app-root',
  imports: [FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App implements OnInit {
  private readonly http = inject(HttpClient);

  activeView = signal<View>('query');

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

  // -- My Documents (universal upload + chat) --------------------------

  documents = signal<DocumentInfo[]>([]);
  selectedFile = signal<File | null>(null);
  uploading = signal(false);
  docError = signal('');

  uploadQuestion = signal('');
  uploadLoading = signal(false);
  uploadChatResponse = signal<ChatResponse | null>(null);

  ngOnInit(): void {
    this.refreshDocuments();
  }

  setActiveView(view: View): void {
    this.activeView.set(view);
    if (view === 'documents') {
      this.refreshDocuments();
    }
  }

  refreshDocuments(): void {
    this.http.get<DocumentListResponse>(`${API_BASE}/api/documents`).subscribe({
      next: (response) => this.documents.set(response.documents),
      error: (err) => this.docError.set(`Failed to load documents: ${err.status ?? ''} ${err.message ?? err}`),
    });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedFile.set(input.files?.[0] ?? null);
  }

  uploadFile(): void {
    const file = this.selectedFile();
    if (!file) {
      return;
    }
    this.uploading.set(true);
    this.docError.set('');

    const formData = new FormData();
    formData.append('file', file);

    this.http.post<DocumentInfo>(`${API_BASE}/api/documents/upload`, formData).subscribe({
      next: () => {
        this.uploading.set(false);
        this.selectedFile.set(null);
        this.refreshDocuments();
      },
      error: (err) => {
        this.uploading.set(false);
        this.docError.set(`Upload failed: ${err.error?.detail ?? err.message ?? err}`);
      },
    });
  }

  deleteDocument(docId: string): void {
    this.http.delete(`${API_BASE}/api/documents/${docId}`).subscribe({
      next: () => this.refreshDocuments(),
      error: (err) => this.docError.set(`Delete failed: ${err.status ?? ''} ${err.message ?? err}`),
    });
  }

  askUploaded(): void {
    if (!this.uploadQuestion().trim()) {
      return;
    }
    this.uploadLoading.set(true);
    this.docError.set('');
    this.uploadChatResponse.set(null);

    this.http
      .post<ChatResponse>(`${API_BASE}/api/documents/chat`, { question: this.uploadQuestion() })
      .subscribe({
        next: (response) => {
          this.uploadChatResponse.set(response);
          this.uploadLoading.set(false);
        },
        error: (err) => {
          this.docError.set(`Request failed: ${err.status ?? ''} ${err.message ?? err}`);
          this.uploadLoading.set(false);
        },
      });
  }
}
