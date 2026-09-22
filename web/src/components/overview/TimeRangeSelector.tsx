import { TIME_RANGES, type TimeRange } from "../../api/types";

export interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
}

/** The seven Overview time ranges as a segmented control. It scrolls horizontally within its
 *  own box on a narrow screen rather than wrapping (and widening) the page - every option stays
 *  reachable by swiping instead of being clipped. */
export function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  return (
    <div className="time-range" role="radiogroup" aria-label="Time range">
      {TIME_RANGES.map((range) => (
        <button
          key={range}
          type="button"
          role="radio"
          aria-checked={range === value}
          className={`time-range-option${range === value ? " active" : ""}`}
          onClick={() => onChange(range)}
        >
          {range}
        </button>
      ))}
    </div>
  );
}
