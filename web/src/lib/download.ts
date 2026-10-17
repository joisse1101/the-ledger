/** Hands a download address to the browser, which saves it as a file without leaving the page.
 *  The server answers it with `Content-Disposition: attachment`. */
export function startDownload(url: string): void {
  const link = document.createElement("a");
  link.href = url;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
}
