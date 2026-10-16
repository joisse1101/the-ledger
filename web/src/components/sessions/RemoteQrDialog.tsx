import { useEffect, useId, useRef } from "react";
import { useRemoteQr } from "../../api/queries";
import { useNow } from "../../hooks/useNow";
import { formatTimeLeft } from "../../lib/format";
import styles from "./RemoteQrDialog.module.css";

export interface RemoteQrDialogProps {
  open: boolean;
  onClose: () => void;
}

/** The sign-in code for other devices, in a modal. A native `<dialog>` kept mounted (an effect
 *  syncs `open` to `showModal()`/`close()`, as `ConfirmDialog` does); Esc, a backdrop click and
 *  Close all call `onClose`. The code is fetched only while open, and its body is unmounted on
 *  close so the token-bearing image does not stay in the page. */
export function RemoteQrDialog({ open, onClose }: RemoteQrDialogProps) {
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
        event.preventDefault(); // `open` is the parent's to change
        onClose();
      }}
      onClose={() => {
        if (open) onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className={styles.body}>
        <h2 id={titleId} className={styles.title}>
          Open on another device
        </h2>
        {open && <QrBody />}
        <button type="button" className="button" onClick={onClose}>
          Close
        </button>
      </div>
    </dialog>
  );
}

function QrBody() {
  const qr = useRemoteQr(true);
  const now = useNow(30_000);

  if (qr.isError) {
    return (
      <p role="alert" className={styles.error}>
        {qr.error.message}
      </p>
    );
  }
  if (!qr.data) return <p className={styles.caption}>Loading…</p>;

  const expiresAt = qr.data.expires_at ? Date.parse(qr.data.expires_at) : null;
  const timeLeft = expiresAt !== null && !Number.isNaN(expiresAt) ? `${formatTimeLeft(expiresAt - now)} left` : null;
  // An <img> never runs script, so the server's SVG can't do anything but draw.
  const src = `data:image/svg+xml;utf8,${encodeURIComponent(qr.data.svg)}`;

  return (
    <>
      <img className={styles.code} src={src} alt="Sign-in QR code" />
      <p className={styles.address}>{qr.data.display_url}</p>
      <p className={styles.caption}>
        Scan with your phone's camera. The browser warns about the certificate once; accept it.
        {timeLeft && ` ${timeLeft}.`}
      </p>
    </>
  );
}
