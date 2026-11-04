# Guide: Files

Move files between the PC and another device, such as a phone, through one shared folder on the PC.
The page exists only while [Remote mode](Glossary.md#remote-mode) is on. See [Remote access](Guide-Remote-Access.md) to turn it on.

## Open the page

1. Turn on Remote mode on the PC.
2. Sign in on the other device. See [Remote access](Guide-Remote-Access.md).
3. Open **Files** in the navigation.
4. If Remote mode is off there is no Files entry. Opening the address sends you to the home page.
5. If Remote mode turns off while the page is open, you are sent home.

## Upload files

1. Click **Upload files**.
2. Pick one or more files. They upload one at a time.
3. Watch the progress bar beside each file name.
4. Read "Uploaded" when a file is done, or "Failed:" and a reason if it was not.
5. Find the file in the list below once it is done.

## Download a file

1. Find the file in the list. Each row shows the name, size and last-changed time.
2. Click **Download**.
3. If the file was removed meanwhile, the page says it couldn't download and refreshes the list.
4. If the folder has nothing in it, the page says "The folder is empty."

## Delete a file

Only a browser on the PC that runs the Ledger shows **Delete**.

1. Click **Delete** on a row.
2. Read "Delete this file?" and the file name.
3. Click **Delete** to confirm, or **Cancel**.

## Checked and unchecked

- Checked: every name above against `FilesPage.tsx`.
- Unchecked: where the shared folder lives on the PC. This page does not say, and the source for this page does not name it.
- Unchecked: the page was not tried from a real phone.

## More detail

- [Frontend: Files](Frontend-Files.md) explains the page.
- [API routes](Backend-API-Routes.md) lists the file-drop routes.
- `openspec/specs/file-drop/spec.md` holds the requirements.
