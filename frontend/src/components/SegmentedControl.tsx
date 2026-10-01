import type { ReactNode } from 'react';

export interface SegmentOption<T extends string> {
  value: T;
  label: ReactNode;
  disabled?: boolean;
}

interface SegmentedControlProps<T extends string> {
  options: SegmentOption<T>[];
  value: T | null;
  onChange: (value: T) => void;
  ariaLabel: string;
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
}: SegmentedControlProps<T>) {
  return (
    <div className="segmented" role="radiogroup" aria-label={ariaLabel}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          className={value === option.value ? 'active' : ''}
          disabled={option.disabled}
          onClick={(event) => {
            event.stopPropagation();
            onChange(option.value);
          }}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
