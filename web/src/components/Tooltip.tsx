import React, { useState, useRef, useId, useEffect } from 'react';
import styles from './Tooltip.module.css';
import { TooltipIcon } from './icons';

/** Gap kept between the bubble and the edge of the viewport. */
const EDGE_MARGIN = 8;

export interface TooltipProps {
    /** Names the trigger for assistive tech ("About <label>"). */
    label?: string;
    tooltip: string;
    size?: 'sm' | 'md';
}

/**
 * A "?" button that reveals `tooltip` on hover, keyboard focus or tap (hover alone would leave
 * touch devices without it). A tap-opened tooltip closes on a second tap, Escape, a tap elsewhere,
 * the mouse leaving, or a finger dragging on the page.
 *
 * The bubble sits just below the icon, centred on it, and is nudged sideways (or flipped above)
 * whenever that would push it off screen.
 */
export const Tooltip: React.FC<TooltipProps> = ({ label, tooltip, size = 'md' }) => {
    const [tipOpen, setTipOpen] = useState(false);
    const tipRef = useRef<HTMLSpanElement>(null);
    const bubbleRef = useRef<HTMLSpanElement>(null);
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

    // Runs just before the bubble can appear (hover, focus, tap). While closed it's `display: none`
    // (so it can't stretch the page past the screen edge), so it's shown for the instant it takes
    // to measure it. Written straight to the element: it's pure layout, no re-render.
    const place = () => {
        const tip = tipRef.current;
        const bubble = bubbleRef.current;
        if (!tip || !bubble) return;

        const anchor = tip.getBoundingClientRect();
        bubble.style.display = 'block';
        const { width, height } = bubble.getBoundingClientRect();
        bubble.style.display = '';
        const viewportWidth = document.documentElement.clientWidth;
        const viewportHeight = document.documentElement.clientHeight;

        const centred = anchor.left + anchor.width / 2 - width / 2;
        const left = Math.max(EDGE_MARGIN, Math.min(centred, viewportWidth - EDGE_MARGIN - width));
        bubble.style.left = `${left - anchor.left}px`;

        const fitsBelow = anchor.bottom + height <= viewportHeight - EDGE_MARGIN;
        const fitsAbove = anchor.top - height >= EDGE_MARGIN;
        bubble.dataset.side = !fitsBelow && fitsAbove ? 'top' : 'bottom';
    };

    return (
        <span
            ref={tipRef}
            className={[styles.tip, size === 'sm' && styles.small].filter(Boolean).join(' ')}
            onMouseEnter={place}
            onFocus={place}
            onMouseLeave={() => setTipOpen(false)}
            onKeyDown={(e) => e.key === 'Escape' && setTipOpen(false)}
        >
            <button
                type="button"
                className={styles.tipButton}
                aria-label={label ? `About ${label}` : 'More information'}
                aria-describedby={tipId}
                aria-expanded={tipOpen}
                onClick={() => {
                    place();
                    setTipOpen((open) => !open);
                }}
            >
                <TooltipIcon />
            </button>
            <span
                ref={bubbleRef}
                id={tipId}
                role="tooltip"
                className={[styles.bubble, tipOpen && styles.bubbleOpen].filter(Boolean).join(' ')}
            >
                {tooltip}
            </span>
        </span>
    );
};
