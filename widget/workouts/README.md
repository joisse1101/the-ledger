# Break workouts

The break window picks one workout at random from the two folders here.

- `starter/` ships with the repo: neck stretches drawn as SVG frames. The widget never writes into it.
- `mine/` is yours and is not committed (git ignores it). The widget creates it when it is missing.
  Put your own videos and picture folders there.

## Two forms

- **Video**: a file directly in the folder (`.mp4`, `.webm`, `.m4v`, `.ogv`, `.mov`). Its name is the workout's name.
- **Image folder**: a folder of pictures (`.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`). Its name is the workout's name.
  The frames show one after another, each for its own number of seconds.

## `workout.yaml`

An image folder lists its frames in a `workout.yaml` inside it:

```yaml
images:
  - {file: 1.svg, seconds: 20}
  - {file: 2.svg, seconds: 25}
```

- `file`: a path inside the workout's own folder. A missing file, a non-image, or a path that leaves the folder skips the whole workout.
- `seconds`: how long to show the frame; above 0 and up to 600.
- Frames show in the order listed.

In `mine/`, if a folder of pictures has no `workout.yaml`, the widget writes one in natural file order (1, 2, 10) with 20 seconds a frame.
Edit it freely; the widget never overwrites it. Every `starter/` folder must carry its own `workout.yaml`.
