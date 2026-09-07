"""Utility functions for OAK camera pipeline creation and metadata conversion.

Source:   https://github.com/maxsitt/insect-detect
License:  GNU GPLv3 (https://choosealicense.com/licenses/gpl-3.0/)
Author:   Maximilian Sittinger (https://github.com/maxsitt)
Docs:     https://maxsitt.github.io/insect-detect-docs/

Functions:
    convert_cm_lens_position(): Convert closest available centimeter value to OAK lens position value.
    deletterbox_bbox():         De-letterbox bounding box from NN-normalized letterboxed space
                                to frame-normalized space.
    create_pipeline():          Create and configure depthai pipeline for OAK camera.
"""

import json
import logging
import math
from datetime import timedelta
from pathlib import Path
from typing import cast

import depthai as dai

from insectdetect.config import AppConfig, get_field_constraints
from insectdetect.constants import MODELS_PATH, RESOLUTION_PRESETS, SENSOR_CROP, SENSOR_RES

# Initialize logger for this module
logger = logging.getLogger(__name__)

# Mapping of object-to-camera distances (8-80 cm) to OAK lens position values (255-120)
CM_LENS_POSITIONS: dict[int, int] = {
    8: 255, 9: 210, 10: 200, 11: 190, 12: 180, 13: 175, 14: 170, 15: 165, 16: 162, 17: 160,
    18: 158, 19: 156, 20: 154, 21: 152, 22: 150, 23: 148, 24: 146, 25: 144, 26: 142, 27: 141,
    28: 140, 29: 139, 30: 138, 31: 137, 32: 136, 34: 135, 36: 134, 38: 133, 40: 132, 42: 131,
    45: 130, 48: 129, 52: 128, 56: 127, 60: 126, 64: 125, 68: 124, 72: 123, 76: 122, 80: 120,
}
CM_KEYS: tuple[int, ...] = tuple(CM_LENS_POSITIONS.keys())


def convert_cm_lens_position(distance_cm: int) -> int:
    """Convert closest available centimeter value to OAK lens position value.

    Args:
        distance_cm: Object-to-camera distance in centimeters.

    Returns:
        OAK lens position value (120-255) corresponding to the given distance.
    """
    if distance_cm in CM_KEYS:
        return CM_LENS_POSITIONS[distance_cm]
    closest_cm = min(CM_KEYS, key=lambda k: abs(k - distance_cm))
    return CM_LENS_POSITIONS[closest_cm]


def _build_zoom_table(
    base_w: int,
    base_h: int,
    zoom_min: float = 1.0,
    zoom_max: float = 3.0,
    zoom_step: float = 0.1,
) -> dict[float, tuple[int, int]]:
    """Build a lookup table mapping zoom factors to aligned output pixel dimensions.

    Width is aligned to multiples of 32, as required by the VideoEncoder node.
    Height is aligned to multiples of the GCD of the base dimensions clamped to [2, 8],
    which ensures consistent aspect ratios across zoom steps. For near-square presets
    (aspect ratio within 2% of 1:1), height is additionally clamped to never exceed width,
    preventing width < height entries that would occur when the finer height alignment
    snaps height to a larger value than the coarser width alignment.

    Args:
        base_w:    Input frame width in pixels.
        base_h:    Input frame height in pixels.
        zoom_min:  Minimum zoom factor (default: 1.0).
        zoom_max:  Maximum zoom factor (default: 3.0).
        zoom_step: Zoom factor step size (default: 0.1).

    Returns:
        Dict mapping each zoom factor (rounded to 1 decimal) to (zoomed_w, zoomed_h).
    """
    align_w = 32
    align_h = max(2, min(8, math.gcd(base_w, base_h)))
    is_square = abs(base_w / base_h - 1.0) < 0.02
    zoom_table: dict[float, tuple[int, int]] = {zoom_min: (base_w, base_h)}
    n_steps = round((zoom_max - zoom_min) / zoom_step)
    for i in range(1, n_steps + 1):
        zoom = round(zoom_min + i * zoom_step, 1)
        zoomed_w = int(base_w / zoom) // align_w * align_w
        zoomed_h = int(base_h / zoom) // align_h * align_h
        if is_square and zoomed_h > zoomed_w:
            zoomed_h = zoomed_w
        zoom_table[zoom] = (zoomed_w, zoomed_h)
    return zoom_table


# Mapping of zoom factors to aligned output pixel dimensions for captured images and web app stream
_zoom_constraints = get_field_constraints(AppConfig, "camera", "zoom", "factor")
_ZOOM_MIN: float = float(_zoom_constraints["min"] or 1.0)
_ZOOM_MAX: float = float(_zoom_constraints["max"] or 3.0)
_ZOOM_STEP: float = float(_zoom_constraints["multiple_of"] or 0.1)
ZOOM_SIZES: dict[str, dict[str, dict[float, tuple[int, int]]]] = {
    preset: {
        "image": _build_zoom_table(image_w, image_h, _ZOOM_MIN, _ZOOM_MAX, _ZOOM_STEP),
        "stream": _build_zoom_table(stream_w, stream_h, _ZOOM_MIN, _ZOOM_MAX, _ZOOM_STEP)
    }
    for preset, (image_w, image_h, stream_w, stream_h) in RESOLUTION_PRESETS.items()
}


def deletterbox_bbox(
    bbox: tuple[float, float, float, float],
    frame_w: int,
    frame_h: int,
    nn_w: int,
    nn_h: int,
) -> tuple[float, float, float, float]:
    """De-letterbox bounding box from NN-normalized letterboxed space to frame-normalized space.

    Args:
        bbox:    Bounding box (x_min, y_min, x_max, y_max) in NN-normalized letterboxed space.
        frame_w: Active frame width in pixels.
        frame_h: Active frame height in pixels.
        nn_w:    NN input width in pixels.
        nn_h:    NN input height in pixels.

    Returns:
        Bounding box (x_min, y_min, x_max, y_max) in frame-normalized space [0, 1].
    """
    scale = min(nn_w / frame_w, nn_h / frame_h)
    scaled_w = frame_w * scale
    scaled_h = frame_h * scale
    pad_x = (nn_w - scaled_w) / 2 / nn_w
    pad_y = (nn_h - scaled_h) / 2 / nn_h
    content_x = scaled_w / nn_w
    content_y = scaled_h / nn_h
    return (
        max(0.0, (bbox[0] - pad_x) / content_x),
        max(0.0, (bbox[1] - pad_y) / content_y),
        min(1.0, (bbox[2] - pad_x) / content_x),
        min(1.0, (bbox[3] - pad_y) / content_y),
    )


def _create_rgb_branch(
    pipeline: dai.Pipeline,
    config: AppConfig,
    stream: bool = False,
) -> tuple[
    dai.MessageQueue,
    dai.MessageQueue,
    dai.InputQueue,
    tuple[int, int],
    tuple[int, int],
    tuple[int, int, int, int],
    list[str],
]:
    """Build the RGB camera branch and the detection/tracking chain for that branch."""
    sensor_w, sensor_h = SENSOR_RES
    image_w, image_h, stream_w, stream_h = RESOLUTION_PRESETS[config.camera.image.resolution]
    out_w, out_h = (stream_w, stream_h) if stream else (image_w, image_h)
    zoom_factor = config.camera.zoom.factor
    if config.camera.zoom.enabled and zoom_factor > 1.0:
        size_key = "stream" if stream else "image"
        target_w, target_h = ZOOM_SIZES[config.camera.image.resolution][size_key][zoom_factor]
    else:
        target_w, target_h = out_w, out_h

    # Create Camera node and set initial control options
    cam = pipeline.create(dai.node.Camera).build(
        sensorResolution=(sensor_w, sensor_h),
        sensorFps=config.camera.fps
    )

    cam.initialControl.setSharpness(config.camera.isp.sharpness)
    cam.initialControl.setLumaDenoise(config.camera.isp.luma_denoise)
    cam.initialControl.setChromaDenoise(config.camera.isp.chroma_denoise)

    if config.camera.focus.mode == "manual":
        # Set manual focus using either object-to-camera distance (cm) or lens position (0-255)
        cam.initialControl.setAutoFocusMode(dai.CameraControl.AutoFocusMode.OFF)
        if config.camera.focus.type == "distance":
            cam.initialControl.setManualFocus(
                convert_cm_lens_position(config.camera.focus.manual.distance)
            )
        elif config.camera.focus.type == "lens_pos":
            cam.initialControl.setManualFocus(config.camera.focus.manual.lens_pos)
    elif config.camera.focus.mode == "range":
        # Set auto focus range using either object-to-camera distance (cm) or lens position (0-255)
        # Note: higher distance -> lower lens position, so min/max are intentionally swapped
        if config.camera.focus.type == "distance":
            cam.initialControl.setAutoFocusLensRange(
                convert_cm_lens_position(config.camera.focus.range.distance.max),
                convert_cm_lens_position(config.camera.focus.range.distance.min)
            )
        elif config.camera.focus.type == "lens_pos":
            cam.initialControl.setAutoFocusLensRange(
                config.camera.focus.range.lens_pos.min,
                config.camera.focus.range.lens_pos.max,
            )

    # For square or zoomed presets, set AE/AF region to the sensor-space crop area
    sensor_crop_w, sensor_crop_h = SENSOR_CROP[config.camera.image.resolution]
    is_square_preset = sensor_crop_w < sensor_w or sensor_crop_h < sensor_h
    if is_square_preset or (config.camera.zoom.enabled and zoom_factor > 1.0):
        scale_to_crop_w = target_w / out_w
        scale_to_crop_h = target_h / out_h
        roi_w = round(sensor_crop_w * scale_to_crop_w)
        roi_h = round(sensor_crop_h * scale_to_crop_h)
        roi_x = round((sensor_w - roi_w) / 2)
        roi_y = round((sensor_h - roi_h) / 2)
        sensor_roi = (roi_x, roi_y, roi_w, roi_h)
        cam.initialControl.setAutoExposureRegion(*sensor_roi)
        if config.camera.focus.mode != "manual":
            cam.initialControl.setAutoFocusRegion(*sensor_roi)
    else:
        sensor_roi = (1, 1, sensor_crop_w - 2, sensor_crop_h - 2)

    # Request camera output with configured resolution
    cam_out = cam.requestOutput(
        size=(out_w, out_h),
        type=dai.ImgFrame.Type.NV12,
        resizeMode=dai.ImgResizeMode.CROP,
        fps=config.camera.fps
    )

    if config.camera.zoom.enabled and zoom_factor > 1.0:
        # Create ImageManip node to crop the center region for zooming
        crop_x = (out_w - target_w) // 2
        crop_y = (out_h - target_h) // 2
        zoom_manip = pipeline.create(dai.node.ImageManip)
        zoom_manip.initialConfig.setFrameType(dai.ImgFrame.Type.NV12)
        zoom_manip.initialConfig.addCrop(crop_x, crop_y, target_w, target_h)
        zoom_manip.setMaxOutputFrameSize(target_w * target_h * 3 // 2)
        zoom_manip.inputImage.setBlocking(False)
        cam_out.link(zoom_manip.inputImage)
        cam_frames = zoom_manip.out
    else:
        cam_frames = cam_out

    # Create VideoEncoder node for MJPEG-encoding of RGB HQ frames
    encoder = pipeline.create(dai.node.VideoEncoder).build(
        input=cam_frames,
        frameRate=1,
        profile=dai.VideoEncoderProperties.Profile.MJPEG,
        quality=config.webapp.stream.quality if stream else config.camera.image.quality
    )
    q_camctrl = cam.inputControl.createInputQueue(maxSize=1, blocking=False)

    # Load the specified detection model from the models directory and get input size and type
    nn_archive = dai.NNArchive(MODELS_PATH / config.detection.model)
    nn_input_size = nn_archive.getInputSize()
    if nn_input_size is None:
        raise ValueError(f"Could not retrieve input size from NN archive: {config.detection.model}")
    nn_input_type_str = nn_archive.getConfig().model.inputs[0].preprocessing.daiType or "BGR888p"
    nn_input_type = cast("dai.ImgFrame.Type", getattr(dai.ImgFrame.Type, nn_input_type_str))

    frame_aspect = target_w / target_h
    nn_aspect = nn_input_size[0] / nn_input_size[1]
    aspect_diff = abs(frame_aspect - nn_aspect)
    if aspect_diff > 0.1:
        logger.warning(
            "Aspect ratio mismatch between frame size (%dx%d) and NN input size (%dx%d). "
            "Letterboxing will add %.1f%% padding.",
            target_w,
            target_h,
            nn_input_size[0],
            nn_input_size[1],
            aspect_diff / max(frame_aspect, nn_aspect) * 100,
        )

    nn_manip = pipeline.create(dai.node.ImageManip)
    nn_manip.initialConfig.setFrameType(nn_input_type)
    nn_manip.initialConfig.setOutputSize(
        nn_input_size[0], nn_input_size[1], dai.ImageManipConfig.ResizeMode.LETTERBOX
    )
    nn_manip.setMaxOutputFrameSize(nn_input_size[0] * nn_input_size[1] * 3)
    nn_manip.inputImage.setBlocking(False)
    cam_frames.link(nn_manip.inputImage)

    # Create and configure DetectionNetwork node
    nn_det = pipeline.create(dai.node.DetectionNetwork).build(
        input=nn_manip.out,
        nnArchive=nn_archive,
    )
    nn_det.setNNArchive(nn_archive, numShaves=config.detection.num_shaves)  # type: ignore[call-arg]
    nn_det.setConfidenceThreshold(config.detection.conf_threshold)
    nn_det.setNumInferenceThreads(2)
    nn_det.input.setBlocking(False)
    labels = nn_det.getClasses()
    if labels is None:
        raise ValueError(f"Could not retrieve class labels from NN archive: {config.detection.model}")

    # Create and configure ObjectTracker node
    tracker = pipeline.create(dai.node.ObjectTracker)
    tracker.setTrackerType(dai.TrackerType.SHORT_TERM_IMAGELESS)
    tracker.setTrackerIdAssignmentPolicy(dai.TrackerIdAssignmentPolicy.UNIQUE_ID)
    tracker.setOcclusionRatioThreshold(0.5)
    tracker.setTrackletBirthThreshold(20)
    tracker.setTrackletMaxLifespan(300)
    nn_det.passthrough.link(tracker.inputTrackerFrame)
    nn_det.passthrough.link(tracker.inputDetectionFrame)
    nn_det.out.link(tracker.inputDetections)

    # Create Sync node to synchronize HQ frames with tracker output
    sync = pipeline.create(dai.node.Sync)
    sync.setSyncThreshold(timedelta(milliseconds=100))
    encoder.bitstream.link(sync.inputs["frames"])
    tracker.out.link(sync.inputs["tracks"])

    # Create MessageDemux node and output queues for frames and tracks
    demux = pipeline.create(dai.node.MessageDemux)
    sync.out.link(demux.input)
    q_frames = demux.outputs["frames"].createOutputQueue(maxSize=2, blocking=False)
    q_tracks = demux.outputs["tracks"].createOutputQueue(maxSize=2, blocking=False)

    return q_frames, q_tracks, q_camctrl, (target_w, target_h), nn_input_size, sensor_roi, labels


def _create_mono_branch(
    pipeline: dai.Pipeline,
    config: AppConfig,
    stream: bool = False,
) -> tuple[
    dai.MessageQueue,
    dai.MessageQueue,
    dai.InputQueue,
    tuple[int, int],
    tuple[int, int],
    tuple[int, int, int, int],
    list[str],
]:
    """Build the mono camera branch and its tracking pipeline."""
    mono_resolution_cfg = config.webapp.resolution_mono if stream else config.camera.resolution_mono
    target_w, target_h = mono_resolution_cfg.width, mono_resolution_cfg.height
    cam = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_B)

    if target_w <= 640 and target_h <= 400:
        mono_out = cam.requestOutput((640, 400), type=dai.ImgFrame.Type.YUV400p, fps=config.camera.fps)
        mono_sensor_width, mono_sensor_height = 640, 400
    else:
        mono_out = cam.requestOutput((1280, 720), type=dai.ImgFrame.Type.YUV400p, fps=config.camera.fps)
        mono_sensor_width, mono_sensor_height = 1280, 720

    #mono_sensor_width, mono_sensor_height = cam_mono.getMaxWidth(), cam_mono.getMaxHeight() #cam.getResolutionSize()

    cam.initialControl.setSharpness(config.camera.isp.sharpness)
    cam.initialControl.setLumaDenoise(config.camera.isp.luma_denoise)
    cam.initialControl.setChromaDenoise(config.camera.isp.chroma_denoise)
    if config.camera.exposure.mode == "manual":
        try:
            exp_time_us = int(float(config.camera.exposure.time) * 1000)
            iso_i = int(config.camera.exposure.iso)
            cam.initialControl.setManualExposure(exp_time_us, iso_i)
        except Exception:
            pass

    manip_mono_hq = pipeline.create(dai.node.ImageManip)
    crop_x = mono_sensor_width - target_w
    crop_y = (mono_sensor_height - target_h) // 2
    manip_mono_hq.initialConfig.addCrop(crop_x, crop_y, target_w, target_h)
    manip_mono_hq.setMaxOutputFrameSize(3 * target_w * target_h)
    mono_out.link(manip_mono_hq.inputImage)

    encoder = pipeline.create(dai.node.VideoEncoder)
    encoder.setDefaultProfilePreset(1, dai.VideoEncoderProperties.Profile.MJPEG)
    encoder.setQuality(config.webapp.stream.quality if stream else config.camera.image.quality)
    manip_mono_hq.out.link(encoder.input)

    sensor_roi = (
        int(round(mono_sensor_width - target_w)),
        int(round((mono_sensor_height - target_h) / 2)),
        target_w,
        target_h,
    )

    # Load the specified detection model from the models directory and get input size and type
    nn_archive = dai.NNArchive(MODELS_PATH / config.detection.model)
    nn_input_size = nn_archive.getInputSize()
    if nn_input_size is None:
        raise ValueError(f"Could not retrieve input size from NN archive: {config.detection.model}")
    nn_input_type_str = nn_archive.getConfig().model.inputs[0].preprocessing.daiType or "GRAY8"
    nn_input_type = cast("dai.ImgFrame.Type", getattr(dai.ImgFrame.Type, nn_input_type_str))

    frame_aspect = target_w / target_h
    nn_aspect = nn_input_size[0] / nn_input_size[1]
    aspect_diff = abs(frame_aspect - nn_aspect)
    if aspect_diff > 0.1:
        logger.warning(
            "Aspect ratio mismatch between frame size (%dx%d) and NN input size (%dx%d). "
            "Letterboxing will add %.1f%% padding.", target_w, target_h,
            nn_input_size[0], nn_input_size[1], aspect_diff / max(frame_aspect, nn_aspect) * 100
        )

    # Create ImageManip node to resize (Letterbox) and format frames for detection network input
    nn_manip = pipeline.create(dai.node.ImageManip)
    nn_manip.initialConfig.setFrameType(nn_input_type)
    nn_manip.initialConfig.setOutputSize(nn_input_size[0], nn_input_size[1],
                                         dai.ImageManipConfig.ResizeMode.LETTERBOX)
    nn_manip.setMaxOutputFrameSize(nn_input_size[0] * nn_input_size[1] * 3)
    nn_manip.inputImage.setBlocking(False)
    manip_mono_hq.out.link(nn_manip.inputImage)

    # Create and configure DetectionNetwork node
    nn_det = pipeline.create(dai.node.DetectionNetwork).build(
        input=nn_manip.out,
        nnArchive=nn_archive
    )
    nn_det.setNNArchive(nn_archive, numShaves=config.detection.num_shaves)  # type: ignore[call-arg]
    nn_det.setConfidenceThreshold(config.detection.conf_threshold)
    nn_det.setNumInferenceThreads(2)
    nn_det.input.setBlocking(False)
    labels = nn_det.getClasses()
    if labels is None:
        raise ValueError(f"Could not retrieve class labels from NN archive: {config.detection.model}")

    # Create and configure ObjectTracker node
    tracker = pipeline.create(dai.node.ObjectTracker)
    tracker.setTrackerType(getattr(dai.TrackerType, config.tracking.type))
    tracker.setTrackerIdAssignmentPolicy(dai.TrackerIdAssignmentPolicy.UNIQUE_ID)
    tracker.setOcclusionRatioThreshold(config.tracking.occlusion_ratio_threshold)
    tracker.setTrackletBirthThreshold(config.tracking.tracklet_birth_threshold)
    tracker.setTrackletMaxLifespan(config.tracking.tracklet_max_lifespan)
    nn_det.passthrough.link(tracker.inputTrackerFrame)
    nn_det.passthrough.link(tracker.inputDetectionFrame)
    nn_det.out.link(tracker.inputDetections)

    # Create Sync node to synchronize HQ frames with tracker output
    sync = pipeline.create(dai.node.Sync)
    sync.setSyncThreshold(timedelta(milliseconds=100))
    encoder.bitstream.link(sync.inputs["frames"])
    tracker.out.link(sync.inputs["tracks"])

    # Create MessageDemux node and output queues for frames and tracks
    demux = pipeline.create(dai.node.MessageDemux)
    sync.out.link(demux.input)
    q_frames = demux.outputs["frames"].createOutputQueue(maxSize=2, blocking=False)
    q_tracks = demux.outputs["tracks"].createOutputQueue(maxSize=2, blocking=False)

    q_camctrl = cam.inputControl.createInputQueue(maxSize=1, blocking=False)

    return q_frames, q_tracks, q_camctrl, (target_w, target_h), nn_input_size, sensor_roi, labels


def create_pipeline(
    config: AppConfig,
    stream: bool = False,
) -> tuple[
    dai.Pipeline,
    dict[str, dai.MessageQueue],
    dict[str, dai.MessageQueue],
    dai.MessageQueue,
    dict[str, dai.InputQueue],
    dict[str, tuple[int, int]],
    tuple[int, int],
    dict[str, tuple[int, int, int, int]],
    list[str],
]:
    """Create both RGB and mono branches in a single pipeline.

    The selected camera mode controls which branch is used for detection/tracking,
    while both streams remain available for preview switching and simultaneous
    recording in night mode.
    """
    pipeline = dai.Pipeline()
    active_mode = getattr(config.camera, "mode", "rgb")

    q_frames_rgb, q_tracks_rgb, q_camctrl_rgb, frame_size_rgb, nn_input_size_rgb, sensor_roi_rgb, labels_rgb = _create_rgb_branch(
        pipeline, config, stream
    )
    q_frames_mono, q_tracks_mono, q_camctrl_mono, frame_size_mono, nn_input_size_mono, sensor_roi_mono, labels_mono = _create_mono_branch(
        pipeline, config, stream
    )

    active_labels = labels_rgb if active_mode == "rgb" else labels_mono
    active_nn_input_size = nn_input_size_rgb if active_mode == "rgb" else nn_input_size_mono

    q_frames_by_mode = {"rgb": q_frames_rgb, "mono": q_frames_mono}
    q_tracks_by_mode = {"rgb": q_tracks_rgb, "mono": q_tracks_mono}
    q_camctrl_by_mode = {"rgb": q_camctrl_rgb, "mono": q_camctrl_mono}
    frame_sizes_by_mode = {"rgb": frame_size_rgb, "mono": frame_size_mono}
    sensor_rois_by_mode = {"rgb": sensor_roi_rgb, "mono": sensor_roi_mono}

    # Single shared SystemLogger for the whole device (not per-branch)
    syslog = pipeline.create(dai.node.SystemLogger)
    syslog.setRate(1)
    q_syslog = syslog.out.createOutputQueue(maxSize=2, blocking=False)

    return (
        pipeline,
        q_frames_by_mode,
        q_tracks_by_mode,
        q_syslog,
        q_camctrl_by_mode,
        frame_sizes_by_mode,
        active_nn_input_size,
        sensor_rois_by_mode,
        active_labels,
    )
