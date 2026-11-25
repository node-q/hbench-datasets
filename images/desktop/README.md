# desktop: the image for computer-use test sets

`ghcr.io/node-q/hbench-envs:desktop-1.0` (linux/amd64) is the image the tasks of `computer-use-browser` run in. An
agent that works a desktop through screenshots, mouse and keyboard (hbench's `computer-1`) starts in it what its
desktop runtime needs: Xvfb on display `:1`, `startxfce4`, `x11vnc` (optional), Chromium at `/usr/bin/chromium`,
`xdotool` and `wmctrl` to act and place the window, `import` (ImageMagick) or `scrot` for screenshots and `convert`
for zoom crops, `curl` for Chromium's readiness probe, and `pgrep`/`pkill`. The Dockerfile is the one node-q builds
its own desktop image from, on the same pinned base.

| What | Version |
|---|---|
| Debian | 13 (trixie), from `base-python-3.12-slim` (images/bases.yaml: `python:3.12-slim` by digest) |
| Python, pip | 3.12.15, 25.0.1 (from the base; the tasks' checker runs on it) |
| Debian archive | snapshot.debian.org at 2026-11-24T00:00:00Z (`SNAPSHOT`), so every dependency resolves the same on every build |
| xvfb | 2:21.1.16-1.3+deb13u4 |
| xfce4-session, xfwm4, xfconf | 4.20.2-2, 4.20.0-1, 4.20.0-1 (with xfce4-settings as their dependency; no panel, desktop or file manager) |
| dbus-x11 | 1.16.2-2 |
| chromium | 156.0.8078.108-1~deb13u1 (its built-in PDF viewer opens `file://` PDFs) |
| xdotool, wmctrl | 1:3.20160805.1-5.1, 1.07+git20240228.1105759-1 |
| imagemagick, scrot | 8:7.1.1.43+dfsg1-1+deb13u14, 1.12.1-1 |
| x11vnc | 0.9.17-1 |
| fonts-dejavu-core, fonts-liberation | 2.37-8, 1:2.1.5-3 |
| curl, procps, ca-certificates | 8.14.1-2+deb13u7, 2:4.0.4-9, 20250419+deb13u1 |

About 1.45 GB uncompressed on amd64. Give a task at least 2 CPUs and 4,096 MB: Chromium with a long PDF needs them.

## Licences

Everything in the image is free software that may be redistributed. Every package comes from Debian's `main`
archive (the only apt sources are the snapshot's `debian` and `debian-security`, component `main`), which holds only
software that meets the Debian Free Software Guidelines. Python in the base image is the Python Software Foundation's
build, under the PSF License. node-q changed none of it.

Checked on 2026-11-25 in an amd64 build: all 362 installed packages keep their licence and copyright notice at
`/usr/share/doc/<package>/copyright` inside the image. The packages named in the Dockerfile:

| Package | Licence (from its copyright file) |
|---|---|
| xvfb, xserver-common | MIT/X11 (X.Org) |
| xfce4-session, xfce4-settings, xfconf | GPL-2+, LGPL-2+ |
| xfwm4 | GPL-2+ |
| dbus-x11 | GPL-2+ or AFL-2.1, with LGPL-2.1+, Expat and BSD-3-Clause parts |
| chromium, chromium-common | BSD-3-Clause for most, with Apache-2.0, MPL-1.1, public-domain and other free parts |
| xdotool | BSD-3-Clause |
| wmctrl | GPL-2+ |
| imagemagick | ImageMagick License, with GPL-3+ (Autoconf exception) build files |
| scrot | MIT-feh, BSD-3-Clause, Unlicense |
| x11vnc | GPL-2 |
| fonts-dejavu-core | Bitstream Vera Fonts licence (DejaVu changes public domain) |
| fonts-liberation | SIL Open Font License 1.1 |
| curl | curl licence (MIT-style), ISC |
| procps | GPL-2+, LGPL-2+ |
| ca-certificates | MPL-2.0, GPL-2+ |

Source code. For the packages under the GPL or LGPL, and any other, the corresponding source of the exact versions
installed is kept by Debian at https://snapshot.debian.org (the archive at the `SNAPSHOT` time above), and the
Dockerfile names every version. node-q will also provide it on request: open an issue in this repository.

Names. Chromium, Debian, XFCE and the other names are their owners'; the image is not endorsed by any of them.
Chromium here is Debian's build, not Google Chrome.

## Checked

On 2026-11-25, with an amd64 build of this Dockerfile (`docker build images/desktop`) and hbench 0.5.3: the commands
`computer-1` runs at start brought up the display, the XFCE session, x11vnc and Chromium (its readiness probe answered
in 2 s); `wmctrl -l` listed the Chromium window with an IRS PDF open; `import -window root` wrote a 1024x900 PNG; the
whole desktop with the PDF open peaked at 331 MB. `hbench run -a oracle` on a `computer-use-browser` task scored 1,
and an empty answer 0. A run with a real model was not made.

When the image changes, add a new tag (`desktop-1.1`, ...) in images/images.yaml: tags are never moved.
