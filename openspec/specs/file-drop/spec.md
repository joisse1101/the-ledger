# file-drop Specification

## Purpose

Lets the user move files between the PC and another device on the same network, such as a phone,
through one shared folder, with no cable and no traffic leaving the local network.

## Requirements

### Requirement: Files page is available only while Remote mode is on
The app SHALL offer a Files page, and SHALL accept requests to list, upload, download or delete
drop-folder files, only while Remote mode is on. While Remote mode is off the navigation SHALL NOT
show the Files page, and every file endpoint SHALL refuse the request, whether it comes from this
machine or another device. The refusal SHALL be enforced by the server, not only by hiding the page.

#### Scenario: Remote mode off hides the page
- **WHEN** Remote mode is off
- **THEN** the navigation has no Files entry, and opening the Files address shows the default page

#### Scenario: Remote mode off refuses requests
- **WHEN** Remote mode is off and any device, including this machine, requests a file list, upload,
  download or delete
- **THEN** the request is refused and no file is read, written or removed

#### Scenario: Remote mode on shows the page
- **WHEN** Remote mode is on and a device signed in to the app opens it
- **THEN** the navigation shows the Files entry and the page lists the drop folder

#### Scenario: Remote mode turns off mid-session
- **WHEN** Remote mode turns off (switched off, or its time limit runs out) while a device has the
  Files page open
- **THEN** that device's next file request is refused and the page leaves the Files view

### Requirement: Other devices need the access token
A file request from any device other than this machine SHALL carry the app's access token, exactly
as other data requests do, and SHALL be refused without it. No separate credential SHALL exist for
files.

#### Scenario: No token
- **WHEN** a phone requests the file list without the token while Remote mode is on
- **THEN** it receives an unauthorized response and no file names

### Requirement: Files live in one fixed drop folder
All listing, upload, download and delete SHALL act only on files directly inside a single drop
folder on the PC, whose location is set by the server and changeable by the user through
configuration. A request SHALL NOT be able to name a path, subfolder or location of its own. The
folder SHALL be created when first needed.

#### Scenario: Path traversal in a name
- **WHEN** a request names a file as `../../secret.txt` or with a path separator
- **THEN** it is refused and nothing outside the drop folder is read or written

#### Scenario: Subfolders are not exposed
- **WHEN** the drop folder contains a subfolder
- **THEN** the list does not show it and its contents cannot be downloaded through the app

### Requirement: Listing the drop folder
The page SHALL list the files in the drop folder with each name, size and modified time, newest
first.

#### Scenario: Files listed
- **WHEN** the drop folder holds two files
- **THEN** the page shows both with name, size and modified time, the most recently modified first

#### Scenario: Empty folder
- **WHEN** the drop folder is empty
- **THEN** the page says so and still offers upload

### Requirement: Uploading a file
The user SHALL be able to upload one or more files from the page into the drop folder, with
progress shown per file. Large files SHALL be accepted, with no fixed size cap lower than the free
disk space. An upload SHALL NOT overwrite an existing file: a name already in use SHALL be kept
and the new file saved under a distinct name. A failed or interrupted upload SHALL leave no
partial file in the list.

#### Scenario: Successful upload
- **WHEN** the user uploads a 500 MB video from a phone
- **THEN** it appears in the list under its own name with its full size

#### Scenario: Name already taken
- **WHEN** the user uploads `photo.jpg` and the folder already holds `photo.jpg`
- **THEN** both files exist afterwards, the new one under a different name, and the original is
  unchanged

#### Scenario: Interrupted upload
- **WHEN** the connection drops partway through an upload
- **THEN** no partial file appears in the list and the user is told the upload failed

#### Scenario: Unsafe file name
- **WHEN** an uploaded file's name contains path separators or characters Windows rejects
- **THEN** it is saved under a sanitized name inside the drop folder

### Requirement: Downloading a file
The user SHALL be able to download any file in the drop folder from the page, receiving the file
byte for byte under its own name, with large files streamed rather than held in memory.

#### Scenario: Download to phone
- **WHEN** the user taps Download on a file in the list
- **THEN** the device receives the identical file with the same name

#### Scenario: File no longer exists
- **WHEN** the user downloads a file that was removed from the folder after the list loaded
- **THEN** the request fails with a not-found response and the page refreshes its list

### Requirement: Downloads use a single-use link
A signed-in device SHALL start a download by asking the app for a download link for one named file.
The link SHALL work without the access token, for that one file only, at most once, and for about a
minute, so the browser can save the file directly without holding it in memory. An expired, used,
unknown or invented link SHALL be refused and return no file data. Links SHALL be refused while
Remote mode is off, and SHALL NOT be written to logs.

#### Scenario: Link works once
- **WHEN** a device opens a freshly issued download link, and then opens the same link again
- **THEN** the first request returns the file and the second is refused

#### Scenario: Link expires
- **WHEN** a download link is opened more than about a minute after it was issued
- **THEN** it is refused and no file data is returned

#### Scenario: Asking for a link needs the token
- **WHEN** a phone asks for a download link without the access token
- **THEN** it receives an unauthorized response and no link

#### Scenario: Link does not reach other data
- **WHEN** a download link is used on any address other than the download address, or to read any
  other file
- **THEN** the request is refused as for any request without the token

#### Scenario: Remote mode off
- **WHEN** Remote mode is off and a download link, even a freshly issued one, is opened
- **THEN** it is refused and no file data is returned

### Requirement: Deleting a file requires a local request
Deleting a file from the drop folder SHALL be refused unless the request comes from this machine,
after a confirmation, regardless of any token. The page SHALL hide the delete control on other
devices.

#### Scenario: Delete from this machine
- **WHEN** the user confirms deletion of a file on the PC's own browser
- **THEN** the file is removed from the folder and the list

#### Scenario: Delete from another device
- **WHEN** a signed-in phone sends a delete request
- **THEN** it is refused with a forbidden response and the file remains
