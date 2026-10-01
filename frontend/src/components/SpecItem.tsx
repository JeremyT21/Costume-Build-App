interface SpecItemProps {
  label: string;
  value: string;
}

export function SpecItem({ label, value }: SpecItemProps) {
  return (
    <div className="spec">
      <div className="spec-label">{label}</div>
      <div className="spec-value">{value}</div>
    </div>
  );
}
