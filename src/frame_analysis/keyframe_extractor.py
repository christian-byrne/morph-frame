import cv2
from pprint import pformat

class KeyFrames:
    """
    This class analyzes a video file and determines the differences between each frame.
    It then determines the threshold for a keyframe based on the average difference
    between frames and the minimum difference between frames.

    The algorithm for determining the threshold is as follows:
    (average diff) -  (minimum diff) * (1 - threshold)

    The threshold is then used to determine which frames are keyframes.

    The algorithm for determining if a frame is a keyframe is as follows:
    if (combined score) > (threshold):
        frame is a keyframe

    The combined score is the sum of the motion difference and the color difference.
    The motion difference is the absolute difference between the current frame and the
    previous frame. The color difference is the difference between the current frame
    and the previous frame using the chi-squared histogram comparison method.

    The motion difference is weighted by the motion_weight parameter. The color
    difference is weighted by the color_weight parameter. The motion_weight and
    color_weight parameters are used to adjust the importance of the motion difference.
    """

    def __init__(self, config, log):
        self.config = config
        self.log = log
        self.frames = []  # list of frame objects
        self.keyframes = []  # list of pointers to frame objects in self.frames
        self.all_color_diffs = []
        self.all_motion_diffs = []

        self.analyze_frames()
        self.set_difference_measures()
        self.set_difference_thresholds()
        self.set_keyframes()

        self.log.write(
            [
                "fps:",
                self.get_fps(),
                "frame count:",
                self.get_frame_count(),
                "difference properties:",
                pformat(self.get_difference_properties()),
                "keyframe details:",
                pformat(self.get_keyframe_details()),
                "keyframe original indices:",
                self.get_keyframe_original_indices(),
                "\n\nkeyframe visualization:",
                self.get_keyframe_vizualization(),
                "\nframe objects:",
                pformat(self.get_frame_objects()),
                "keyframe objects:",
                pformat(self.get_keyframe_objects()),
            ]
        )

    def get_fps(self):
        return self.fps

    def get_frame_count(self):
        return len(self.frames)

    def get_frame_objects(self):
        return self.frames

    def get_keyframe_objects(self):
        return self.keyframes

    def get_keyframe_original_indices(self):
        return [frame["frame_index_original"] for frame in self.keyframes]

    def get_keyframe_details(self):
        return {
            "number of keyframes": len(self.keyframes),
            "ratio of keyframes to frames": len(self.keyframes) / len(self.frames),
            "average keyframe group size": len(self.frames) / len(self.keyframes),
            "largest keyframe group size": max(
                self.keyframes, key=lambda x: x["frame_index_original"]
            )["frame_index_original"],
            "smallest keyframe group size": min(
                self.keyframes, key=lambda x: x["frame_index_original"]
            )["frame_index_original"],
        }

    def get_keyframe_vizualization(self, line_width=40):
        characters = []
        cur_width = 0
        for frame in self.frames:
            if frame["keyframe"]:
                characters.append("_X_")
            else:
                characters.append("___")
            cur_width += 3
            if cur_width % line_width == 0:
                characters.append("\n")
                cur_width = 0

        return "".join(characters)

    def get_difference_properties(self):
        return {
            "min_color_diff": self.min_color_diff,
            "max_color_diff": self.max_color_diff,
            "average_color_diff": self.average_color_diff,
            "min_motion_diff": self.min_motion_diff,
            "max_motion_diff": self.max_motion_diff,
            "average_motion_diff": self.average_motion_diff,
            "calculated_motion_threshold": self.calculated_motion_threshold,
            "calculated_color_threshold": self.calculated_color_threshold,
            "combined_threshold": self.combined_threshold,
        }

    def set_difference_measures(self):
        self.min_color_diff = min(self.all_color_diffs)
        self.max_color_diff = max(self.all_color_diffs)
        self.average_color_diff = sum(self.all_color_diffs) / len(self.all_color_diffs)
        self.min_motion_diff = min(self.all_motion_diffs)
        self.max_motion_diff = max(self.all_motion_diffs)
        self.average_motion_diff = sum(self.all_motion_diffs) / len(
            self.all_motion_diffs
        )

    def set_difference_thresholds(self):
        # Placeholder algorithm (needs improving):
        # (average diff) -  (minimum diff) * (1 - threshold)
        self.calculated_motion_threshold = (
            self.average_motion_diff - self.min_motion_diff
        ) * (1 - self.config.get("keyframe_determination")["motion_threshold"])
        self.calculated_color_threshold = (
            self.average_color_diff - self.min_color_diff
        ) * (1 - self.config.get("keyframe_determination")["color_threshold"])
        self.combined_threshold = (
            self.calculated_motion_threshold + self.calculated_color_threshold
        )

    def set_keyframes(self):
        for frame in self.frames:
            if frame["combined_score"] > self.combined_threshold:
                frame["keyframe"] = True
                frame["keyframe_children_indices"] = []
                frame["keyframe_index"] = len(self.keyframes) + 1
                self.keyframes.append(frame)
            else:
                frame["keyframe"] = False
                # TODO: handle situation where there are no keyframes because the first keyframe is not the first frame
                try:
                    self.keyframes[-1]["keyframe_children_indices"].append(
                        frame["frame_index_original"]
                    )
                except IndexError:
                    print(
                        "Frame "
                        + str(frame["frame_index_original"])
                        + " cannot be assigned a parent keyframe because there are no keyframes yet (i.e., this frame occurs before the first keyframe)."
                    )

    def calculate_color_difference(self, frame1, frame2):
        hist1 = cv2.calcHist(
            [cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)], [0], None, [256], [0, 256]
        )
        hist2 = cv2.calcHist(
            [cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)], [0], None, [256], [0, 256]
        )
        color_diff = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CHISQR)
        return color_diff

    def analyze_frames(self):
        video_capture = cv2.VideoCapture(self.config.get("alpha_vid"))
        frame_count = 0
        ret, prev_frame = video_capture.read()

        self.fps = video_capture.get(cv2.CAP_PROP_FPS)

        while True:
            ret, frame = video_capture.read()

            if not ret:
                break

            cur_frame = {
                "frame_index_original": frame_count,
            }
            frame_count += 1
            if frame_count > 1:
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray_prev_frame = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
                motion_diff = cv2.absdiff(gray_frame, gray_prev_frame).sum()
                motion_diff = (
                    motion_diff
                    * self.config.get("keyframe_determination")["motion_weight"]
                )
                self.all_motion_diffs.append(motion_diff)
                cur_frame["motion_diff"] = motion_diff

                color_diff = self.calculate_color_difference(frame, prev_frame)
                color_diff = (
                    color_diff
                    * self.config.get("keyframe_determination")["color_weight"]
                )
                self.all_color_diffs.append(color_diff)
                cur_frame["color_diff"] = color_diff

                cur_frame["combined_score"] = motion_diff + color_diff
                self.frames.append(cur_frame)

            prev_frame = frame

        video_capture.release()
        cv2.destroyAllWindows()