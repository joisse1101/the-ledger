import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ConfirmDialog, type ConfirmDialogProps } from "./ConfirmDialog";

function setup(props: Partial<ConfirmDialogProps> = {}) {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  const view = render(
    <ConfirmDialog
      open
      title="Delete project"
      confirmLabel="Delete"
      onConfirm={onConfirm}
      onCancel={onCancel}
      {...props}
    >
      <p>C:\code\app</p>
    </ConfirmDialog>,
  );
  // A closed <dialog> is hidden from the accessibility tree, so look it up directly.
  const dialog = view.container.querySelector("dialog") as HTMLDialogElement;
  return { ...view, dialog, onConfirm, onCancel };
}

describe("ConfirmDialog", () => {
  it("opens and closes with `open`, staying mounted", () => {
    const { dialog, rerender, onConfirm, onCancel } = setup({ open: false });
    expect(dialog.open).toBe(false);

    const again = (open: boolean) =>
      rerender(
        <ConfirmDialog open={open} title="Delete project" confirmLabel="Delete" onConfirm={onConfirm} onCancel={onCancel}>
          <p>C:\code\app</p>
        </ConfirmDialog>,
      );
    again(true);
    expect(dialog.open).toBe(true);
    expect(screen.getByRole("dialog", { name: "Delete project" })).toBeInTheDocument();
    expect(screen.getByText("C:\\code\\app")).toBeInTheDocument();

    again(false);
    expect(dialog.open).toBe(false);
    // Closing because the parent said so isn't a cancel.
    expect(onCancel).not.toHaveBeenCalled();
  });

  it("confirms and cancels through its buttons", () => {
    const { onConfirm, onCancel } = setup();

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onCancel).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("cancels on Esc and on a backdrop click, but not on a click inside", () => {
    const { dialog, onCancel } = setup();

    const esc = new Event("cancel", { cancelable: true });
    dialog.dispatchEvent(esc);
    expect(esc.defaultPrevented).toBe(true); // the parent closes it, not the browser
    expect(onCancel).toHaveBeenCalledTimes(1);

    fireEvent.click(dialog);
    expect(onCancel).toHaveBeenCalledTimes(2);

    fireEvent.click(screen.getByText("C:\\code\\app"));
    expect(onCancel).toHaveBeenCalledTimes(2);
  });

  it("disables both buttons and ignores Esc and the backdrop while pending", () => {
    const { dialog, onConfirm, onCancel } = setup({ pending: true });

    expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();

    const esc = new Event("cancel", { cancelable: true });
    dialog.dispatchEvent(esc);
    expect(esc.defaultPrevented).toBe(true);
    fireEvent.click(dialog);

    expect(onCancel).not.toHaveBeenCalled();
    expect(onConfirm).not.toHaveBeenCalled();
    expect(dialog.open).toBe(true);
  });

  it("puts a dialog the browser closed itself back up while pending, and reports it otherwise", () => {
    const pending = setup({ pending: true });
    pending.dialog.close(); // e.g. Chrome's second Esc, which can't be prevented
    expect(pending.dialog.open).toBe(true);
    expect(pending.onCancel).not.toHaveBeenCalled();
    pending.unmount();

    const idle = setup();
    idle.dialog.close();
    expect(idle.onCancel).toHaveBeenCalledTimes(1);
  });

  it("shows the error inside the dialog and leaves it open", () => {
    const { dialog } = setup({ error: "Deleting a project needs a local request." });

    expect(screen.getByRole("alert")).toHaveTextContent("Deleting a project needs a local request.");
    expect(dialog.open).toBe(true);
  });

  it("shows no alert without an error", () => {
    setup();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
