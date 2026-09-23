interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pages, total, onPageChange }: PaginationProps) {
  if (pages <= 1) return <p className="result-count">{total} total records</p>;
  return (
    <div className="pagination" aria-label="Pagination">
      <p>{total} total records</p>
      <div>
        <button disabled={page <= 1} onClick={() => onPageChange(page - 1)} type="button">
          Previous
        </button>
        <span>
          Page {page} of {pages}
        </span>
        <button disabled={page >= pages} onClick={() => onPageChange(page + 1)} type="button">
          Next
        </button>
      </div>
    </div>
  );
}
