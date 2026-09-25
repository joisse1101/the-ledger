import { useEffect, useRef } from "react";

export interface FilterMultiselectProps {
  label: string;
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
}

/** A `<details>`-based multi-select: a button-like summary naming the field and how many
 *  values are picked, opening a checkbox list. No positioning/portal logic needed since the
 *  browser handles the disclosure, and checkboxes are touch-friendly on a phone. */
export function FilterMultiselect({ label, options, selected, onChange }: FilterMultiselectProps) {
  const toggle = (option: string) => {
    onChange(selected.includes(option) ? selected.filter((o) => o !== option) : [...selected, option]);
  };

  const detailsRef = useRef<HTMLDetailsElement>(null);

  // A click anywhere outside this control closes it (native `<details>` only closes on its own summary).
  useEffect(() => {
    const closeOnOutsideClick = (e: MouseEvent) => {
      const details = detailsRef.current;
      if (details && !details.contains(e.target as Node)) details.open = false;
    };
    document.addEventListener("click", closeOnOutsideClick);
    return () => document.removeEventListener("click", closeOnOutsideClick);
  }, []);

  return (
    <details className="filter-multiselect" ref={detailsRef}>
      <summary className="filter-multiselect-summary">
        {label}
        {selected.length > 0 && <span className="filter-multiselect-count">{selected.length}</span>}
      </summary>
      {options.length === 0 ? (
        <p className="muted filter-multiselect-empty">No values yet</p>
      ) : (
        <div className="filter-multiselect-options">
          {options.map((option) => (
            <label key={option} className="filter-multiselect-option">
              <input type="checkbox" checked={selected.includes(option)} onChange={() => toggle(option)} />
              <span>{option}</span>
            </label>
          ))}
        </div>
      )}
    </details>
  );
}
