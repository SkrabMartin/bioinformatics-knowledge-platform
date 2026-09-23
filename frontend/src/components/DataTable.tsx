import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  heading: string;
  render: (item: T) => ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  caption: string;
  columns: Column<T>[];
  items: T[];
  getKey: (item: T) => string | number;
}

export function DataTable<T>({ caption, columns, items, getKey }: DataTableProps<T>) {
  return (
    <div className="table-frame">
      <table>
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} scope="col" className={column.className}>
                {column.heading}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={getKey(item)}>
              {columns.map((column) => (
                <td key={column.key} className={column.className} data-label={column.heading}>
                  {column.render(item)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
