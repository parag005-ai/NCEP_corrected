export function Divider({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-4">
      <div className="h-px flex-1 bg-border-muted" />
      {label ? <span className="text-caption uppercase text-secondary">{label}</span> : null}
      <div className="h-px flex-1 bg-border-muted" />
    </div>
  );
}
