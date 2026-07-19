export type Citation = {
  id: number;
  document_id: number;
  title: string;
  source_uri?: string | null;
  chunk_index: number;
  score: number;
  excerpt: string;
};

export type ConversationSummary = {
  id: number;
  title: string;
  model: string;
  created_at: string;
};
