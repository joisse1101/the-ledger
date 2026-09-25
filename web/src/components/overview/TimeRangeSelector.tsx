import { TIME_RANGES, type TimeRange } from "../../api/types";
import { ButtonSelector } from "../ButtonSelector";

export interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
}

const OPTIONS = TIME_RANGES.map((range) => ({ value: range, label: range }));

/** The seven Overview time ranges as a segmented control. It scrolls horizontally within its
 *  own box on a narrow screen rather than wrapping (and widening) the page - every option stays
 *  reachable by swiping instead of being clipped. */
export function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  return (
    <ButtonSelector
      className="time-range"
      label="Time range"
      hideLabel
      options={OPTIONS}
      value={value}
      onChange={onChange}
    />
  );
}
