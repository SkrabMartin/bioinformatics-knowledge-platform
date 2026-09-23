import type {
  ApiErrorPayload,
  Page,
  EntityRelationship,
  RelatedEntityType,
  SearchEntityType,
  SearchResponse,
  SearchSuggestionsResponse,
} from "../types/entities";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(
  /\/$/,
  "",
);

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let payload: ApiErrorPayload = {};
  try {
    payload = (await response.json()) as ApiErrorPayload;
  } catch {
    // The fallback below intentionally handles non-JSON proxy/network responses.
  }
  return new ApiError(
    payload.error?.message ?? `The API returned ${response.status}.`,
    response.status,
    payload.error?.code ?? "api_error",
  );
}

async function requestJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, {
      headers: { Accept: "application/json" },
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new ApiError(
      "The biological knowledge API is currently unreachable. Check that the backend is running.",
      0,
      "network_error",
    );
  }
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as T;
}

export async function getPage<T>(
  resource: string,
  page: number,
  pageSize: number,
  signal?: AbortSignal,
): Promise<Page<T>> {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  return requestJson<Page<T>>(`${API_BASE_URL}/${resource}?${query}`, signal);
}

export async function getEntity<T>(resourcePath: string, signal?: AbortSignal): Promise<T> {
  return requestJson<T>(`${API_BASE_URL}/${resourcePath}`, signal);
}

export async function getRelationships(
  entityType: RelatedEntityType,
  entityId: number,
  page: number,
  signal?: AbortSignal,
): Promise<Page<EntityRelationship>> {
  const params = new URLSearchParams({ page: String(page), page_size: "10" });
  return requestJson<Page<EntityRelationship>>(
    `${API_BASE_URL}/relationships/${entityType}/${entityId}?${params}`,
    signal,
  );
}

export async function searchEntities(
  query: string,
  page: number,
  pageSize: number,
  entityTypes: SearchEntityType[],
  signal?: AbortSignal,
): Promise<SearchResponse> {
  const params = new URLSearchParams({
    q: query,
    page: String(page),
    page_size: String(pageSize),
  });
  entityTypes.forEach((entityType) => params.append("type", entityType));
  return requestJson<SearchResponse>(`${API_BASE_URL}/search?${params}`, signal);
}

export async function getSearchSuggestions(
  query: string,
  signal?: AbortSignal,
): Promise<SearchSuggestionsResponse> {
  const params = new URLSearchParams({ q: query, limit: "8" });
  return requestJson<SearchSuggestionsResponse>(
    `${API_BASE_URL}/search/suggestions?${params}`,
    signal,
  );
}
