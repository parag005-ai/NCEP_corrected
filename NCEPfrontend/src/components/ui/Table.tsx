import { cn } from "@/lib/utils";

type Column<T> = {
  header: string;
  accessor: (row: T) => React.ReactNode;
};

export function Table<T>({ columns, data, className }: { columns: Column<T>[]; data: T[]; className?: string }) {
  return (
    <div className={cn("max-w-full overflow-x-auto overscroll-x-contain rounded-xl border border-border-muted", className)}>
      <table className="min-w-full divide-y divide-border-muted bg-surface-container-lowest text-left">
        <thead className="bg-surface-container-low">
          <tr>
            {columns.map((column) => (
              <th key={column.header} scope="col" className="whitespace-nowrap px-4 py-3 text-caption uppercase text-secondary">
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border-muted">
          {data.map((row, index) => (
            <tr key={index} className="hover:bg-secondary-container/25">
              {columns.map((column) => (
                <td key={column.header} className="whitespace-nowrap px-4 py-4 text-body-sm text-on-surface-variant">
                  {column.accessor(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
