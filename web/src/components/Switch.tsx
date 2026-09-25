import React, { useState } from 'react';
import { Tooltip } from './Tooltip';
import styles from './Switch.module.css';

export interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size' | 'onChange' | 'className'> {
    size?: 'sm' | 'md';
    checked?: boolean;
    defaultChecked?: boolean;
    disabled?: boolean;
    label?: string;
    /** Applied to the outer <label>, for layout. Every other prop goes to the <input>. */
    className?: string;
    onChange?: (checked: boolean) => void;
    /** Optional tooltip text displayed alongside the switch. */
    tooltip?: string;
}

/**
 * A switch component that allows users to toggle between two states (on/off).
 * Supports controlled and uncontrolled usage, with optional labels and size variations.
 */
export const Switch: React.FC<SwitchProps> = ({
    size = 'md',
    checked,
    defaultChecked = false,
    disabled = false,
    label,
    className,
    onChange,
    tooltip,
    ...restProps
}) => {
    const isControlled = checked !== undefined;

    // Internal state for uncontrolled usage
    const [internalChecked, setInternalChecked] = useState(defaultChecked);

    // Drive UI state based on controlled vs. uncontrolled status
    const currentChecked = isControlled ? checked : internalChecked;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const nextChecked = e.target.checked;

        // Update internal state only when uncontrolled
        if (!isControlled) {
            setInternalChecked(nextChecked);
        }

        // Always trigger callback
        onChange?.(nextChecked);
    };

    const rootClass = [styles.root, size === 'sm' && styles.small, className].filter(Boolean).join(' ');

    return (
        <span className={styles.field}>
            <label className={rootClass}>
                <input
                    {...restProps}
                    className={styles.input}
                    type="checkbox"
                    role="switch"
                    checked={currentChecked}
                    disabled={disabled}
                    onChange={handleChange}
                />
                <span className={styles.track} aria-hidden="true">
                    <span className={styles.thumb} />
                </span>
                {label && <span className={styles.label}>{label}</span>}
            </label>
            {/* A sibling of the <label>, not inside it: inside, tapping the trigger would toggle the switch. */}
            {tooltip && <Tooltip tooltip={tooltip} label={label} />}
        </span>
    );
};
