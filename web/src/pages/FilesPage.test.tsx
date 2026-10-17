import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "../api/queryClient";
import { startDownload } from "../lib/download";
import { FilesPage } from "./FilesPage";

vi.mock("../lib/download", () => ({ startDownload: vi.fn() }));

const REMOTE_ON = { enabled: true, expires_at: null, state: "ready", step: null, reason: null };
const REMOTE_OFF = { ...REMOTE_ON, enabled: false, state: "off" };

interface World {
  isLocal: boolean;
  remote: typeof REMOTE_ON;
  files: { name: string; size: number; modified: string }[];
  calls: { method: string; url: string }[];
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

function stubServer(world: World) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init?: RequestInit) => {
      const method = (init?.method ?? "GET").toUpperCase();
      world.calls.push({ method, url: input });
      if (input === "/api/meta") {
        return json({ refreshed_at: null, is_local: world.isLocal, remote_mode: world.remote });
      }
      if (input === "/api/files" && method === "GET") {
        if (!world.remote.enabled) return json({ detail: "Remote mode is off" }, 403);
        return json({ files: world.files });
      }
      if (input.endsWith("/download-link")) return json({ url: "/api/files/download/ticket123" });
      if (method === "DELETE") return json({ deleted: "x" });
      return json({ detail: "unexpected" }, 500);
    }),
  );
}

class FakeXhr {
  static last: FakeXhr;
  upload: { onprogress: ((event: ProgressEventInit) => void) | null } = { onprogress: null };
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onabort: (() => void) | null = null;
  status = 0;
  responseText = "";
  constructor() {
    FakeXhr.last = this;
  }
  open() {}
  setRequestHeader() {}
  send() {}
}

function renderPage(world: World) {
  stubServer(world);
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter initialEntries={["/files"]}>
        <Routes>
          <Route path="/files" element={<FilesPage />} />
          <Route path="/" element={<div>home page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const photo = { name: "photo.jpg", size: 2_500_000, modified: "2026-10-17T09:00:00" };

let world: World;
beforeEach(() => {
  world = { isLocal: false, remote: REMOTE_ON, files: [photo], calls: [] };
  vi.stubGlobal("XMLHttpRequest", FakeXhr);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("FilesPage", () => {
  it("lists the folder with sizes", async () => {
    renderPage(world);

    const list = await screen.findByRole("list", { name: "Files in the folder" });
    expect(within(list).getByText("photo.jpg")).toBeInTheDocument();
    expect(within(list).getByText(/2\.5 MB/)).toBeInTheDocument();
  });

  it("says so when the folder is empty and still offers upload", async () => {
    world.files = [];
    renderPage(world);

    expect(await screen.findByText("The folder is empty.")).toBeInTheDocument();
    expect(screen.getByText("Upload files")).toBeInTheDocument();
  });

  it("shows progress for an upload and marks it uploaded", async () => {
    renderPage(world);
    await screen.findByText("photo.jpg");

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [new File(["abc"], "clip.mp4")] } });

    const bar = await screen.findByRole("progressbar", { name: "Uploading clip.mp4" });
    FakeXhr.last.upload.onprogress?.({ lengthComputable: true, loaded: 1, total: 4 });
    await waitFor(() => expect(bar).toHaveValue(0.25));

    FakeXhr.last.status = 200;
    FakeXhr.last.responseText = JSON.stringify({ name: "clip.mp4", size: 3, modified: "2026-10-17T09:05:00" });
    FakeXhr.last.onload?.();

    expect(await screen.findByText("Uploaded")).toBeInTheDocument();
  });

  it("shows why an upload failed", async () => {
    renderPage(world);
    await screen.findByText("photo.jpg");

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [new File(["abc"], "clip.mp4")] } });
    await screen.findByRole("progressbar");
    FakeXhr.last.status = 507;
    FakeXhr.last.responseText = JSON.stringify({ detail: "not enough disk space for this file" });
    FakeXhr.last.onload?.();

    expect(await screen.findByRole("alert")).toHaveTextContent("not enough disk space for this file");
  });

  it("asks for a download link and hands it to the browser", async () => {
    renderPage(world);

    fireEvent.click(await screen.findByRole("button", { name: "Download" }));

    await waitFor(() => expect(startDownload).toHaveBeenCalledWith("/api/files/download/ticket123"));
    expect(world.calls).toContainEqual({ method: "POST", url: "/api/files/photo.jpg/download-link" });
  });

  it("hides Delete on another device", async () => {
    renderPage(world);
    await screen.findByText("photo.jpg");

    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });

  it("deletes after confirmation on the PC itself", async () => {
    world.isLocal = true;
    renderPage(world);

    fireEvent.click(await screen.findByRole("button", { name: "Delete" }));
    // The dialog's own confirm button comes after the row's.
    const deletes = await screen.findAllByRole("button", { name: "Delete", hidden: true });
    fireEvent.click(deletes[deletes.length - 1]);

    await waitFor(() => expect(world.calls).toContainEqual({ method: "DELETE", url: "/api/files/photo.jpg" }));
  });

  it("leaves the page when Remote mode turns off while it is open", async () => {
    renderPage(world);
    await screen.findByText("photo.jpg");

    // Remote mode ends; the next thing the page asks the server (here, the list after an upload) is refused.
    world.remote = REMOTE_OFF;
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [new File(["abc"], "clip.mp4")] } });
    await screen.findByRole("progressbar");
    FakeXhr.last.status = 200;
    FakeXhr.last.responseText = JSON.stringify({ name: "clip.mp4", size: 3, modified: "2026-10-17T09:05:00" });
    FakeXhr.last.onload?.();

    expect(await screen.findByText("home page")).toBeInTheDocument();
  });

  it("sends the user home when Remote mode is off", async () => {
    world.remote = REMOTE_OFF;
    renderPage(world);

    expect(await screen.findByText("home page")).toBeInTheDocument();
    expect(world.calls.some((call) => call.url === "/api/files")).toBe(false);
  });
});
