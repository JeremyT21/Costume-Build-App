import type {
  AnalysisResult,
  AppInfo,
  BudgetTier,
  ComponentUpdate,
  CostumeComponent,
  CostumeDetail,
  CostumeSummary,
  ImprovementAdvice,
  Profile,
  ProfileInput,
  StartMode,
} from './types';

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: unknown } | null;
    const detail = typeof body?.detail === 'string' ? body.detail : response.statusText;
    throw new ApiError(detail, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function json(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
}

export interface AnalyzeInput {
  images: File[];
  name: string;
  hint: string;
  intent: 'references' | 'variants';
  budgetTier: BudgetTier;
  startMode: StartMode;
}

export const api = {
  info: () => request<AppInfo>('/api/info'),
  getProfile: () => request<Profile | null>('/api/profile'),
  saveProfile: (input: ProfileInput) => request<Profile>('/api/profile', json('PUT', input)),

  listCostumes: () => request<CostumeSummary[]>('/api/costumes'),
  getCostume: (id: number) => request<CostumeDetail>(`/api/costumes/${id}`),
  deleteCostume: (id: number) => request<void>(`/api/costumes/${id}`, { method: 'DELETE' }),
  setMode: (id: number, mode: StartMode) =>
    request<CostumeDetail>(`/api/costumes/${id}/mode`, json('POST', { mode })),

  analyze: (input: AnalyzeInput) => {
    const form = new FormData();
    input.images.forEach((file) => form.append('images', file));
    form.append('name', input.name);
    form.append('hint', input.hint);
    form.append('intent', input.intent);
    form.append('budget_tier', input.budgetTier);
    form.append('start_mode', input.startMode);
    return request<AnalysisResult>('/api/costumes/analyze', { method: 'POST', body: form });
  },
  selectConcept: (costumeId: number, keepIds: number[]) =>
    request<CostumeDetail>(
      '/api/costumes/select',
      json('POST', { costume_id: costumeId, keep_ids: keepIds }),
    ),

  updateComponent: (id: number, update: ComponentUpdate) =>
    request<CostumeComponent>(`/api/components/${id}`, json('PATCH', update)),
  regenerateModel: (id: number) =>
    request<CostumeComponent>(`/api/components/${id}/model`, { method: 'POST' }),
  refreshProducts: (id: number) =>
    request<CostumeComponent>(`/api/components/${id}/products`, { method: 'POST' }),
  improve: (id: number, notes: string, photos: File[]) => {
    const form = new FormData();
    form.append('notes', notes);
    photos.forEach((file) => form.append('photos', file));
    return request<ImprovementAdvice>(`/api/components/${id}/improve`, {
      method: 'POST',
      body: form,
    });
  },
  patternUrl: (id: number) => `/api/components/${id}/pattern.svg`,
  stlUrl: (id: number) => `/api/components/${id}/model.stl`,
};
