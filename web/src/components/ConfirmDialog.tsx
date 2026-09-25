import { useEffect, useId, useRef, type ReactNode } from "react";
import styles from "./ConfirmDialog.module.css";

export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  /** The body: what is being confirmed (e.g. the path about to be deleted). */
  children: ReactNode;
  confirmLabel: string;
  /** The confirmed action is running: both buttons are disabled and nothing can dismiss the dialog. */
  pending?: boolean;
  /** Shown inside the dialog, which stays open, when the confirmed action failed. */
  error?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}

/** A small modal asking the user to confirm a destructive action. A native `<dialog>` kept mounted
 *  (an effect syncs `open` to `showModal()`/`close()`, as `SessionDialog` does), so the browser
 *  supplies the focus trap and inert background. Esc, a backdrop click and Cancel all call
 *  `onCancel` - the parent closes it by flipping `open` - except while `pending`, when none of them
 *  can dismiss it. The confirm button is styled as dangerous: this is for deletes. */
export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  pending = false,
  error = null,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    else if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      className={styles.root}
      aria-labelledby={titleId}
      onCancel={(event) => {
        // Never let the browser close it itself: `open` is the parent's to change.
        event.preventDefault();
        if (!pending) onCancel();
      }}
      onClose={() => {
        // A browser can still close a dialog whose cancel was prevented (Chrome, on a second Esc
        // in a row). Keep it in step with `open`: back up while pending, else tell the parent.
        if (!open) return;
        if (pending) dialogRef.current?.showModal();
        else onCancel();
      }}
      onClick={(event) => {
        // A click on the dialog element itself, not on its content, is a click on the backdrop.
        if (event.target === event.currentTarget && !pending) onCancel();
      }}
    >
      <div className={styles.body}>
        <h2 id={titleId} className={styles.title}>
          {title}
        </h2>
        <div className={styles.content}>{children}</div>
        {error && (
          <p role="alert" className={styles.error}>
            {error}
          </p>
        )}
        <div className={styles.actions}>
          <button type="button" className="button button-danger" disabled={pending} onClick={onConfirm}>
            {confirmLabel}
          </button>
          <button type="button" className="button" disabled={pending} onClick={onCancel}>
            Cancel
          </button>
        </div>
      </div>
    </dialog>
  );
}
