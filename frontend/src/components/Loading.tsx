interface LoadingProps {
  label?: string;
}

export function Loading({ label = 'Loading' }: LoadingProps) {
  return (
    <div className="loading" role="status">
      <span className="spinner" />
      {label}
    </div>
  );
}
