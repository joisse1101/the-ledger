import React, { useState, useRef, useId, useEffect } from 'react';
import styles from './Tooltip.module.css';
import { TooltipIcon } from './icons';

/**
 * A "?" button that reveals `tooltip` on hover, keyboard focus or tap (hover alone would leave
 * touch devices without it). A tap-opened tooltip closes on a second tap, Escape, a tap elsewhere,
 * the mouse leaving, or a finger dragging on the page. `label` names the trigger for assistive tech ("About <label>").
 * The bubble is absolutely positioned, so it anchors to the nearest positioned ancestor.
 */
export const Tooltip: React.FC<{ label?: string; tooltip: string }> = ({ label, tooltip }) => {
    const [tipOpen, setTipOpen] = useState(false);
    const tipRef = useRef<HTMLSpanElement>(null);
    const tipId = useId();

    useEffect(() => {
        if (!tipOpen) return;
        const closeOnOutsidePointer = (e: PointerEvent) => {
            if (!tipRef.current?.contains(e.target as Node)) setTipOpen(false);
        };
        const close = () => setTipOpen(false);
        document.addEventListener('pointerdown', closeOnOutsidePointer);
        // A finger dragging anywhere (page or a scrollable list) bubbles up to window, so the
        // bubble doesn't stay put while its trigger scrolls away underneath it.
        window.addEventListener('touchmove', close, { passive: true });
        return () => {
            document.removeEventListener('pointerdown', closeOnOutsidePointer);
            window.removeEventListener('touchmove', close);
        };
    }, [tipOpen]);

    return (
        <span
            ref={tipRef}
            className={styles.tip}
            onMouseLeave={() => setTipOpen(false)}
            onKeyDown={(e) => e.key === 'Escape' && setTipOpen(false)}
        >
            <button
                type="button"
                className={styles.tipButton}
                aria-label={label ? `About ${label}` : 'More information'}
                aria-describedby={tipId}
                aria-expanded={tipOpen}
                onClick={() => setTipOpen((open) => !open)}
            >
                <TooltipIcon width={16} height={16} />
            </button>
            <span
                id={tipId}
                role="tooltip"
                className={[styles.bubble, tipOpen && styles.bubbleOpen].filter(Boolean).join(' ')}
            >
                {tooltip}
            </span>
        </span>
    );
};