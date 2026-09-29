import React, { useState, useRef, useId, useEffect, useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';
import styles from './Tooltip.module.css';
import { TooltipIcon } from './icons';

/** Gap kept between the bubble and the edge of the viewport. */
const EDGE_MARGIN = 8;
/** Gap kept between the bubble and the icon it points at. */
const BUBBLE_GAP = 4;

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
 * The bubble is rendered through a portal (into the nearest open `<dialog>` ancestor, so it stays
 * part of that dialog's top-layer stacking, or `document.body` otherwise) so it can't be clipped by
 * an `overflow: hidden/auto` ancestor such as a scrollable table cell or dialog body. Its position is
 * computed in viewport coordinates and kept in sync with the icon on open.
 *
 * The bubble sits just below the icon, centred on it, and is nudged sideways (or flipped above)
 * whenever that would push it off screen.
 */
export const Tooltip: React.FC<TooltipProps> = ({ label, tooltip, size = 'md' }) => {
    const [tapOpen, setTapOpen] = useState(false);
    const [hoverOpen, setHoverOpen] = useState(false);
    const [focusOpen, setFocusOpen] = useState(false);
    const open = tapOpen || hoverOpen || focusOpen;
    const tipRef = useRef<HTMLSpanElement>(null);
    const bubbleRef = useRef<HTMLSpanElement>(null);
    const tipId = useId();
    const [portalTarget, setPortalTarget] = useState<Element>(() => document.body);

    // A dialog shown via showModal() is promoted to the browser's "top layer", rendered above all
    // non-top-layer content regardless of z-index; a bubble portaled to document.body while one is
    // open would render behind it. Portaling into the dialog instead keeps the bubble in that layer.
    useLayoutEffect(() => {
        setPortalTarget(tipRef.current?.closest('dialog') ?? document.body);
    }, []);

    useEffect(() => {
        if (!tapOpen) return;
        const closeOnOutsidePointer = (e: PointerEvent) => {
            const target = e.target as Node;
            if (!tipRef.current?.contains(target) && !bubbleRef.current?.contains(target)) setTapOpen(false);
        };
        const close = () => setTapOpen(false);
        document.addEventListener('pointerdown', closeOnOutsidePointer);
        // A finger dragging anywhere (page or a scrollable list) bubbles up to window, so the
        // bubble doesn't stay put while its trigger scrolls away underneath it.
        window.addEventListener('touchmove', close, { passive: true });
        return () => {
            document.removeEventListener('pointerdown', closeOnOutsidePointer);
            window.removeEventListener('touchmove', close);
        };
    }, [tapOpen]);

    // Positions the bubble in viewport coordinates. Written straight to the element: it's pure
    // layout, no re-render. Safe to call whenever the bubble might become visible - it's always
    // mounted (just hidden via CSS), so it's always measurable.
    const place = () => {
        const tip = tipRef.current;
        const bubble = bubbleRef.current;
        if (!tip || !bubble) return;

        const anchor = tip.getBoundingClientRect();
        const { width, height } = bubble.getBoundingClientRect();
        const viewportWidth = document.documentElement.clientWidth;
        const viewportHeight = document.documentElement.clientHeight;

        const centred = anchor.left + anchor.width / 2 - width / 2;
        const left = Math.max(EDGE_MARGIN, Math.min(centred, viewportWidth - EDGE_MARGIN - width));
        bubble.style.left = `${left}px`;

        const fitsBelow = anchor.bottom + height <= viewportHeight - EDGE_MARGIN;
        const fitsAbove = anchor.top - height >= EDGE_MARGIN;
        const side = !fitsBelow && fitsAbove ? 'top' : 'bottom';
        bubble.dataset.side = side;
        bubble.style.top = side === 'bottom' ? `${anchor.bottom + BUBBLE_GAP}px` : `${anchor.top - height - BUBBLE_GAP}px`;
    };

    return (
        <span
            ref={tipRef}
            className={[styles.tip, size === 'sm' && styles.small].filter(Boolean).join(' ')}
            onMouseEnter={() => {
                place();
                setHoverOpen(true);
            }}
            onMouseLeave={() => {
                setHoverOpen(false);
                setTapOpen(false);
            }}
            onFocus={(e) => {
                // Only a keyboard focus, not one caused by the mouse click below (which also
                // toggles tapOpen, and would otherwise fight with it).
                let focusVisible = true;
                try {
                    focusVisible = e.target.matches(':focus-visible');
                } catch {
                    // Older engines without :focus-visible support: fall back to always showing.
                }
                if (focusVisible) {
                    place();
                    setFocusOpen(true);
                }
            }}
            onBlur={() => setFocusOpen(false)}
            onKeyDown={(e) => e.key === 'Escape' && setTapOpen(false)}
        >
            <button
                type="button"
                className={styles.tipButton}
                aria-label={label ? `About ${label}` : 'More information'}
                aria-describedby={tipId}
                aria-expanded={tapOpen}
                onClick={(e) => {
                    // Stops a tap on the icon from also activating whatever the tooltip sits
                    // inside (e.g. a clickable table row) - it should only open the tooltip.
                    e.stopPropagation();
                    place();
                    setTapOpen((wasOpen) => !wasOpen);
                }}
            >
                <TooltipIcon />
            </button>
            {createPortal(
                <span
                    ref={bubbleRef}
                    id={tipId}
                    role="tooltip"
                    className={[styles.bubble, open && styles.bubbleOpen].filter(Boolean).join(' ')}
                >
                    {tooltip}
                </span>,
                portalTarget,
            )}
        </span>
    );
};
