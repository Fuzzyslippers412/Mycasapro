type EmptyStateProps = {
  title: string;
  body: string;
  cta?: string;
};

export function EmptyState({ title, body, cta }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{body}</p>
      {cta ? <span className="inline-cta">{cta}</span> : null}
    </div>
  );
}
