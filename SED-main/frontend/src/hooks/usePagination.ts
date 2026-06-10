import { useState } from 'react';

export function usePagination<T>(items: T[], perPage: number = 10) {
  const [page, setPage] = useState(1);

  const totalPages = Math.max(1, Math.ceil(items.length / perPage));

  // Clamp page if it exceeds totalPages (e.g., after search filter reduces items)
  const safePage = Math.min(page, totalPages);

  const startIdx = (safePage - 1) * perPage;
  const endIdx = Math.min(startIdx + perPage, items.length);
  const paginatedItems = items.slice(startIdx, endIdx);

  return {
    page: safePage,
    setPage,
    totalPages,
    paginatedItems,
    startIdx,
    endIdx,
    total: items.length,
  };
}
