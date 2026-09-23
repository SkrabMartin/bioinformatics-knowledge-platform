import { type FormEvent, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getSearchSuggestions } from "../services/api";
import type { SearchSuggestion } from "../types/entities";

interface SearchBoxProps {
  initialValue?: string;
  compact?: boolean;
}

export function SearchBox({ initialValue = "", compact = false }: SearchBoxProps) {
  const [query, setQuery] = useState(initialValue);
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestionError, setSuggestionError] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    setQuery(initialValue);
  }, [initialValue]);

  useEffect(() => {
    const normalized = query.trim();
    if (!showSuggestions || normalized.length < 2 || normalized.length > 200) {
      setSuggestions([]);
      setSuggestionError(false);
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      getSearchSuggestions(normalized, controller.signal)
        .then((response) => {
          setSuggestions(response.items);
          setSuggestionError(false);
        })
        .catch((reason: unknown) => {
          if (reason instanceof DOMException && reason.name === "AbortError") return;
          setSuggestions([]);
          setSuggestionError(true);
        });
    }, 250);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query, showSuggestions]);

  useEffect(() => {
    function closeOutside(event: PointerEvent) {
      if (event.target instanceof Node && !containerRef.current?.contains(event.target)) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("pointerdown", closeOutside);
    return () => document.removeEventListener("pointerdown", closeOutside);
  }, []);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = query.trim();
    setShowSuggestions(false);
    navigate(normalized ? `/search?q=${encodeURIComponent(normalized)}` : "/search");
  }

  return (
    <div className="search-control" ref={containerRef}>
      <form className={`search-box${compact ? " search-box--compact" : ""}`} onSubmit={submit}>
        <label className="sr-only" htmlFor={compact ? "compact-search" : "main-search"}>
          Search biological entities
        </label>
        <span aria-hidden="true" className="search-icon">
          ⌕
        </span>
        <input
          id={compact ? "compact-search" : "main-search"}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setShowSuggestions(true);
          }}
          onFocus={() => setShowSuggestions(true)}
          onKeyDown={(event) => {
            if (event.key === "Escape") setShowSuggestions(false);
          }}
          placeholder="Search genes, proteins, identifiers…"
          type="search"
          maxLength={200}
          autoComplete="off"
        />
        <button type="submit">Search</button>
      </form>
      {showSuggestions && (suggestions.length > 0 || suggestionError) && (
        <div className="suggestion-panel" aria-label="Search suggestions">
          {suggestions.map((suggestion) => (
            <Link
              key={`${suggestion.entity_type}-${suggestion.value}`}
              onClick={() => setShowSuggestions(false)}
              to={suggestion.href ?? `/search?q=${encodeURIComponent(suggestion.value)}`}
            >
              <span className="suggestion-type">{suggestion.entity_type}</span>
              <strong>{suggestion.value}</strong>
              <small>{suggestion.secondary_label}</small>
            </Link>
          ))}
          {suggestionError && <p>Suggestions are unavailable. Press Search to try a full query.</p>}
        </div>
      )}
    </div>
  );
}
