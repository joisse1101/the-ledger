import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, NetworkError, UnauthorizedError } from "./client";
import { uploadFile } from "./upload";

class FakeXhr {
  static last: FakeXhr;
  method = "";
  url = "";
  headers: Record<string, string> = {};
  body: unknown = null;
  status = 0;
  statusText = "";
  responseText = "";
  upload: { onprogress: ((event: ProgressEventInit) => void) | null } = { onprogress: null };
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onabort: (() => void) | null = null;
  aborted = false;

  constructor() {
    FakeXhr.last = this;
  }
  open(method: string, url: string) {
    this.method = method;
    this.url = url;
  }
  setRequestHeader(name: string, value: string) {
    this.headers[name] = value;
  }
  send(body: unknown) {
    this.body = body;
  }
  abort() {
    this.aborted = true;
    this.onabort?.();
  }
  respond(status: number, body: unknown) {
    this.status = status;
    this.responseText = JSON.stringify(body);
    this.onload?.();
  }
}

const file = new File(["hello"], "my photo.jpg", { type: "image/jpeg" });

beforeEach(() => {
  vi.stubGlobal("XMLHttpRequest", FakeXhr);
  localStorage.setItem("ledger_token", "tok");
});

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("uploadFile", () => {
  it("PUTs the raw file with the token and CSRF headers and an encoded name", () => {
    void uploadFile(file, () => {});

    const xhr = FakeXhr.last;
    expect(xhr.method).toBe("PUT");
    expect(xhr.url).toBe("/api/files?name=my+photo.jpg");
    expect(xhr.headers["Authorization"]).toBe("Bearer tok");
    expect(xhr.headers["X-Requested-With"]).toBe("ledger");
    expect(xhr.body).toBe(file);
  });

  it("reports progress as a fraction and finishes at 1", async () => {
    const seen: number[] = [];
    const promise = uploadFile(file, (fraction) => seen.push(fraction));

    FakeXhr.last.upload.onprogress?.({ lengthComputable: true, loaded: 25, total: 100 });
    FakeXhr.last.upload.onprogress?.({ lengthComputable: true, loaded: 100, total: 100 });
    FakeXhr.last.respond(200, { name: "my photo.jpg", size: 5, modified: "2026-01-01T00:00:00" });

    await expect(promise).resolves.toMatchObject({ name: "my photo.jpg" });
    expect(seen).toEqual([0.25, 1, 1]);
  });

  it("rejects with the server's message on a failure status", async () => {
    const promise = uploadFile(file, () => {});
    FakeXhr.last.respond(507, { detail: "not enough disk space for this file" });

    await expect(promise).rejects.toMatchObject({ status: 507, message: "not enough disk space for this file" });
    await expect(promise).rejects.toBeInstanceOf(ApiError);
  });

  it("rejects with UnauthorizedError on 401", async () => {
    const promise = uploadFile(file, () => {});
    FakeXhr.last.respond(401, {});

    await expect(promise).rejects.toBeInstanceOf(UnauthorizedError);
  });

  it("rejects with NetworkError when the connection fails", async () => {
    const promise = uploadFile(file, () => {});
    FakeXhr.last.onerror?.();

    await expect(promise).rejects.toBeInstanceOf(NetworkError);
  });

  it("aborts the request and rejects with an AbortError when the signal fires", async () => {
    const controller = new AbortController();
    const promise = uploadFile(file, () => {}, controller.signal);

    controller.abort();

    expect(FakeXhr.last.aborted).toBe(true);
    await expect(promise).rejects.toMatchObject({ name: "AbortError" });
  });
});
