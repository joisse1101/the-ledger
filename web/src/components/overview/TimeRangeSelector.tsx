import { TIME_RANGES, type TimeRange } from "../../api/types";
import { ButtonSelector } from "../ButtonSelector";

export interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
  /** The ranges that have something to show; every other one is disabled. Omit to enable all
   *  (e.g. while the answer is still loading, so the buttons don't flash disabled). */
  availableRanges?: readonly string[];
}

/** The seven Overview time ranges as a segmented control. It scrolls horizontally within its
 *  own box on a narrow screen rather than wrapping (and widening) the page - every option stays
 *  reachable by swiping instead of being clipped. */
export function TimeRangeSelector({ value, onChange, availableRanges }: TimeRangeSelectorProps) {
  const options = TIME_RANGES.map((range) => ({
    value: range,
    label: range,
    // The chosen range stays enabled so the control never sits on a disabled selection.
    disabled: availableRanges !== undefined && range !== value && !availableRanges.includes(range),
  }));
  return (
    <ButtonSelector
      className="time-range"
      label="Time range"
      hideLabel
      options={options}
      value={value}
      onChange={onChange}
    />
  );
}
