import { useId, useRef, type ReactNode } from "react";
import { useCanSideScroll } from "../hooks/useCanSideScroll";
import styles from "./ButtonSelector.module.css";

export interface ButtonSelectorOption<T extends string | number> {
  value: T;
  label: ReactNode;
}

interface CommonProps<T extends string | number> {
  /** Names the group. Shown above the buttons unless `hideLabel` is set, in which case it's
   *  still what a screen reader announces. */
  label: string;
  hideLabel?: boolean;
  options: ButtonSelectorOption<T>[];
  /** Applied to the outer element, for layout. */
  className?: string;
}

interface SingleProps<T extends string | number> extends CommonProps<T> {
  multiple?: false;
  value: T;
  onChange: (value: T) => void;
}

interface MultiProps<T extends string | number> extends CommonProps<T> {
  multiple: true;
  value: T[];
  onChange: (value: T[]) => void;
}

export type ButtonSelectorProps<T extends string | number> = SingleProps<T> | MultiProps<T>;

/**
 * A row of toggle buttons for choosing among a few options. Fully controlled: pass `value` and
 * `onChange`.
 *
 * - **Single-select** (default): exactly one option is selected; `onChange` gets the new one.
 *   Announced as a radio group.
 * - **Multi-select** (`multiple`): each button toggles independently; `value` and `onChange` are
 *   arrays. Announced as toggle buttons.
 *
 * On a narrow screen the row scrolls sideways within its own box rather than wrapping, and the
 * edge with more to reveal fades out.
 */
export function ButtonSelector<T extends string | number>(props: ButtonSelectorProps<T>) {
  const { label, hideLabel = false, options, className } = props;
  const labelId = useId();
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const { canScrollLeft, canScrollRight } = useCanSideScroll(scrollerRef);

  const isSelected = (optionValue: T) =>
    props.multiple ? props.value.includes(optionValue) : props.value === optionValue;

  const select = (optionValue: T) => {
    if (props.multiple) {
      props.onChange(
        props.value.includes(optionValue)
          ? props.value.filter((v) => v !== optionValue)
          : [...props.value, optionValue],
      );
    } else if (optionValue !== props.value) {
      props.onChange(optionValue);
    }
  };

  return (
    <div className={[styles.root, className].filter(Boolean).join(" ")}>
      {!hideLabel && (
        <span id={labelId} className={styles.label}>
          {label}
        </span>
      )}
      <div
        ref={scrollerRef}
        className={styles.scroller}
        role={props.multiple ? "group" : "radiogroup"}
        aria-label={hideLabel ? label : undefined}
        aria-labelledby={hideLabel ? undefined : labelId}
        data-fade-start={canScrollLeft ? "" : undefined}
        data-fade-end={canScrollRight ? "" : undefined}
      >
        {options.map((option) => {
          const selected = isSelected(option.value);
          return (
            <button
              key={option.value}
              type="button"
              {...(props.multiple
                ? { "aria-pressed": selected }
                : { role: "radio", "aria-checked": selected })}
              className={selected ? `${styles.option} ${styles.selected}` : styles.option}
              onClick={() => select(option.value)}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
