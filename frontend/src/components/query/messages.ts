import type { QueryResult } from '../../types';

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  result?: QueryResult;
  tone?: 'default' | 'error';
}
