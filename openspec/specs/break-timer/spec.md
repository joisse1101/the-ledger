# break-timer Specification

## Purpose

Reminds the user to rest their neck by opening a break window in the desktop widget after a set stretch of work time, showing one randomly chosen workout (a video or a timed series of images) that plays only when the user presses Start.

## Requirements

### Requirement: The widget counts work time toward a break
The widget SHALL count work time from the moment it opens and SHALL open the break window when the count reaches the break length. The count SHALL advance only while the AFK switch is off, SHALL NOT include time the PC spent asleep, and SHALL start again from zero when the break window is closed. The break length SHALL be 60 minutes until set in Settings.

#### Scenario: Break after an hour of work
- **WHEN** the widget has been open for 60 minutes with the AFK switch off and the break length is the default
- **THEN** the break window opens

#### Scenario: AFK pauses the count
- **WHEN** the AFK switch is on for 20 minutes of a 60 minute stretch and is then turned off
- **THEN** the break window opens 20 minutes later than it would have, and not before

#### Scenario: Sleep does not count
- **WHEN** the PC sleeps for 3 hours after 10 minutes of work
- **THEN** on waking the count is about 10 minutes, not 3 hours 10 minutes

#### Scenario: Closing starts the next count
- **WHEN** the user closes the break window
- **THEN** the count restarts from zero, whether or not the workout was played

#### Scenario: Widget restarted
- **WHEN** the widget is quit and opened again
- **THEN** the count starts from zero

### Requirement: The break window waits for Start
The break window SHALL be a separate window from the widget's list. It SHALL open above other windows without taking keyboard focus and SHALL show the chosen workout's name with a Start button, a Skip button and a Close button. Nothing SHALL play or advance until the user presses Start.

#### Scenario: Opens without playing
- **WHEN** the break window opens
- **THEN** it shows the workout's name and a Start button, and no video plays and no image sequence advances

#### Scenario: Does not capture typing
- **WHEN** the user is typing in another window as the break window opens
- **THEN** the typing continues in that window and does not press any button in the break window

#### Scenario: Start plays
- **WHEN** the user presses Start
- **THEN** the workout begins

#### Scenario: Close from any state
- **WHEN** the user presses Close before Start, during play, or after play ends
- **THEN** the window closes and the widget's list window is unaffected

### Requirement: The workout is picked at random and Skip picks another
The widget SHALL pick the workout at random from all valid workouts in the starter and personal folders together. Skip SHALL pick a different workout when more than one is available, and SHALL wait for Start again. When only one workout is available, Skip SHALL keep it.

#### Scenario: Both folders in one pool
- **WHEN** the starter folder holds three workouts and the personal folder holds two
- **THEN** each of the five can be picked

#### Scenario: Different breaks differ
- **WHEN** several breaks happen with more than one workout available
- **THEN** the workouts shown are not always the same one

#### Scenario: Skip changes the workout
- **WHEN** the user presses Skip on a window showing one of several workouts
- **THEN** a different workout is shown and waits for Start

#### Scenario: Skip during play
- **WHEN** the user presses Skip while a workout is playing
- **THEN** the playing stops and the new workout waits for Start

### Requirement: A video workout plays on Start
A video file placed directly in a workouts folder SHALL be a workout named after its file. Pressing Start SHALL play it in the break window.

#### Scenario: Video plays
- **WHEN** a video workout is shown and the user presses Start
- **THEN** the video plays in the break window

#### Scenario: Unplayable video
- **WHEN** the video cannot be played
- **THEN** the window shows a short note and the user can still Skip or Close

### Requirement: An image workout steps through its images from its YAML file
A subfolder holding images SHALL be a workout named after the folder. Pressing Start SHALL show its images one after another in the order and for the durations given in its YAML file, and SHALL end after the last one.

#### Scenario: Order and duration followed
- **WHEN** the YAML file lists `b.svg` for 10 seconds then `a.svg` for 30 seconds and the user presses Start
- **THEN** `b.svg` shows for 10 seconds, then `a.svg` for 30 seconds, then the sequence ends

#### Scenario: Edited file is used as written
- **WHEN** the user changes an image's duration in the YAML file and the next break picks that workout
- **THEN** the new duration is used

### Requirement: A YAML file is generated for an image folder that has none
When an image folder has no YAML file, the widget SHALL create one listing every image in the folder in file-name order, each with a default duration of 20 seconds. The widget SHALL NOT overwrite or rewrite an existing YAML file.

#### Scenario: Generated
- **WHEN** a personal folder holds `1.png`, `2.png` and `10.png` and no YAML file
- **THEN** a YAML file is created listing the three images in file-name order, each with 20 seconds

#### Scenario: Never overwritten
- **WHEN** a YAML file already exists, however it was written
- **THEN** its content is unchanged after the widget has read it, and after any number of breaks

#### Scenario: Generated only where the user keeps files
- **WHEN** a committed starter folder is read
- **THEN** no file is written into it

### Requirement: Workout files can only come from the workouts folders
The break window SHALL receive workout files only from the widget's main process, and only from inside the starter and personal folders. It SHALL have no other file access. A YAML entry that points outside the workouts folders, by an absolute path, a parent-folder path or a link, SHALL make that workout invalid.

#### Scenario: Parent-folder entry rejected
- **WHEN** a YAML file lists `../../secret.png`
- **THEN** that workout is skipped with a short note and the file is not read

#### Scenario: Absolute path rejected
- **WHEN** a YAML file lists `C:/Users/someone/photo.png`
- **THEN** that workout is skipped with a short note

#### Scenario: Link out of the folder rejected
- **WHEN** a file in a workouts folder is a link to a file outside it
- **THEN** it is not served

#### Scenario: Request for another file refused
- **WHEN** the break window asks for a file that is not inside a workouts folder
- **THEN** nothing is returned

### Requirement: Missing, empty or broken workouts never break the widget
When no valid workout exists, the break window SHALL open with a short note saying so and a Close button, and the widget SHALL otherwise keep working. A workout with a broken YAML file, a missing image or an unsupported file SHALL be left out of the pool and a short note SHALL be available, without a crash.

#### Scenario: No workouts at all
- **WHEN** both folders are missing or hold no workouts and the break is due
- **THEN** the break window shows a short note that there are no workouts, and closing it restarts the count

#### Scenario: Broken YAML skipped
- **WHEN** one workout's YAML file cannot be parsed and others are valid
- **THEN** the broken one is never picked, and a note names it where the user can see it

#### Scenario: Personal folder missing
- **WHEN** the personal folder does not exist
- **THEN** the widget creates it and the starter workouts are still used

### Requirement: Starter workouts ship with the repo and personal ones stay out of it
The repo SHALL include a set of starter neck stretches as images with YAML files, drawn for this project. The personal workouts folder SHALL be listed in `.gitignore`, so the user's files never appear in `git status`.

#### Scenario: Fresh checkout is not empty
- **WHEN** the repo is freshly cloned and a break is due
- **THEN** the break window shows one of the starter stretches

#### Scenario: Personal files ignored
- **WHEN** the user adds a video and an image folder to the personal folder
- **THEN** `git status` does not list them
