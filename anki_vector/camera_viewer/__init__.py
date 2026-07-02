# Copyright (c) 2018 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This module provides the camera viewer's render process.

It should be launched in a separate process to allow Vector to run freely while
the viewer is rendering.

It uses Tkinter, a standard Python GUI package.
It also depends on the Pillow library for image processing.
"""

import multiprocessing as mp
import sys

try:
    import tkinter as tk
    _HAS_TK = True
except ModuleNotFoundError:
    tk = None
    _HAS_TK = False

try:
    import cv2
    import numpy as np
    _HAS_CV2 = True
except ModuleNotFoundError:
    cv2 = None
    np = None
    _HAS_CV2 = False

if _HAS_TK:
    try:
        from PIL import ImageTk
    except ImportError:
        sys.exit("Cannot import from PIL ImageTk support: Do `pip3 install --user Pillow` to install")


class TkCameraViewer:  # pylint: disable=too-few-public-methods
    """A Tkinter based camera video feed.

    :param queue: A queue to send frames between the user's main thread and the viewer process.
    :param event: An event to signal that the viewer process has closed.
    :param overlays: Overlays to be drawn on the images of the renderer.
    :param timeout: The time without a new frame before the process will exit.
    :param force_on_top: Specifies whether the window should be forced on top of all others.
    """

    def __init__(self, queue: mp.Queue, event: mp.Event, overlays: list = None, timeout: float = 10.0, force_on_top: bool = True):
        self.tk_root = tk.Tk()
        self.width = None
        self.height = None
        self.queue = queue
        self.event = event
        self.overlays = overlays
        self.timeout = timeout
        self.tk_root.title("Vector Camera Feed")
        self.tk_root.protocol("WM_DELETE_WINDOW", self._delete_window)
        self.tk_root.bind("<Configure>", self._resize_window)
        if force_on_top:
            self.tk_root.wm_attributes("-topmost", 1)
        self.label = tk.Label(self.tk_root, borderwidth=0)
        self.label.pack(fill=tk.BOTH, expand=True)

    def _delete_window(self) -> None:
        """Handle window close event."""
        self.event.set()
        self.tk_root.destroy()

    def _resize_window(self, evt) -> None:
        """Handle window resize event.

        :param evt: A Tkinter window event (keyboard, mouse events, etc).
        """
        self.width = evt.width
        self.height = evt.height

    def draw_frame(self) -> None:
        """Display an image on to a Tkinter label widget."""
        try:
            image = self.queue.get(True, timeout=self.timeout)
        except:
            return


class OpenCVCameraViewer:  # pylint: disable=too-few-public-methods
    """OpenCV-based camera viewer fallback for Python builds without tkinter."""

    def __init__(self, queue: mp.Queue, event: mp.Event, overlays: list = None, timeout: float = 10.0):
        self.queue = queue
        self.event = event
        self.overlays = overlays
        self.timeout = timeout
        self.window_name = "Vector Camera Feed"

    def _to_bgr(self, image):
        frame = np.array(image)
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    def draw_frame(self) -> None:
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        try:
            image = self.queue.get(True, timeout=self.timeout)
        except Exception:
            cv2.destroyWindow(self.window_name)
            return

        while image is not None:
            if self.event.is_set():
                break

            if self.overlays:
                for overlay in self.overlays:
                    overlay.apply_overlay(image)

            cv2.imshow(self.window_name, self._to_bgr(image))

            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord('q'):
                break

            if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                break

            try:
                image = self.queue.get(True, timeout=self.timeout)
            except Exception:
                break

        cv2.destroyWindow(self.window_name)


def main(queue: mp.Queue, event: mp.Event, overlays: list = None, timeout: float = 10.0, force_on_top: bool = False) -> None:
    """Rendering the frames in another process. This allows the UI to have the
    main thread of its process while the user code continues to execute.

    :param queue: A queue to send frames between the user's main thread and the viewer process.
    :param event: An event to signal that the viewer process has closed.
    :param overlays: Overlays to be drawn on the images of the renderer.
    :param timeout: The time without a new frame before the process will exit.
    :param force_on_top: Specifies whether the window should be forced on top of all others.
    """

    try:
        if _HAS_TK:
            tk_viewer = TkCameraViewer(queue, event, overlays, timeout, force_on_top)
            tk_viewer.draw_frame()
        elif _HAS_CV2:
            cv_viewer = OpenCVCameraViewer(queue, event, overlays, timeout)
            cv_viewer.draw_frame()
        else:
            raise RuntimeError(
                "No GUI backend available for camera viewer. Install tkinter-enabled Python or install opencv-python."
            )
    except TimeoutError:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        event.set()


__all__ = ['TkCameraViewer', 'main']
