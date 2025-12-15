"""
V4L2 (Video4Linux2) ioctl definitions for direct camera control.

Provides ctypes structures and constants for V4L2 API access.
"""

import ctypes
from ctypes import c_uint8, c_uint16, c_uint32, c_int32, c_int64, c_char

# ioctl magic number
_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14
_IOC_DIRBITS = 2

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

_IOC_NONE = 0
_IOC_WRITE = 1
_IOC_READ = 2


def _IOC(dir_: int, type_: int, nr: int, size: int) -> int:
    return (
        (dir_ << _IOC_DIRSHIFT) |
        (type_ << _IOC_TYPESHIFT) |
        (nr << _IOC_NRSHIFT) |
        (size << _IOC_SIZESHIFT)
    )


def _IOR(type_: int, nr: int, size: int) -> int:
    return _IOC(_IOC_READ, type_, nr, size)


def _IOW(type_: int, nr: int, size: int) -> int:
    return _IOC(_IOC_WRITE, type_, nr, size)


def _IOWR(type_: int, nr: int, size: int) -> int:
    return _IOC(_IOC_READ | _IOC_WRITE, type_, nr, size)


# Buffer types
V4L2_BUF_TYPE_VIDEO_CAPTURE = 1
V4L2_BUF_TYPE_VIDEO_OUTPUT = 2
V4L2_BUF_TYPE_VIDEO_OVERLAY = 3
V4L2_BUF_TYPE_VBI_CAPTURE = 4
V4L2_BUF_TYPE_VBI_OUTPUT = 5

# Memory types
V4L2_MEMORY_MMAP = 1
V4L2_MEMORY_USERPTR = 2
V4L2_MEMORY_OVERLAY = 3
V4L2_MEMORY_DMABUF = 4

# Field types
V4L2_FIELD_ANY = 0
V4L2_FIELD_NONE = 1
V4L2_FIELD_TOP = 2
V4L2_FIELD_BOTTOM = 3
V4L2_FIELD_INTERLACED = 4

# Pixel formats (FourCC codes)
def _v4l2_fourcc(a: str, b: str, c: str, d: str) -> int:
    return (
        ord(a) |
        (ord(b) << 8) |
        (ord(c) << 16) |
        (ord(d) << 24)
    )


V4L2_PIX_FMT_RGB24 = _v4l2_fourcc('R', 'G', 'B', '3')
V4L2_PIX_FMT_BGR24 = _v4l2_fourcc('B', 'G', 'R', '3')
V4L2_PIX_FMT_RGB32 = _v4l2_fourcc('R', 'G', 'B', '4')
V4L2_PIX_FMT_BGR32 = _v4l2_fourcc('B', 'G', 'R', '4')
V4L2_PIX_FMT_YUYV = _v4l2_fourcc('Y', 'U', 'Y', 'V')
V4L2_PIX_FMT_UYVY = _v4l2_fourcc('U', 'Y', 'V', 'Y')
V4L2_PIX_FMT_MJPEG = _v4l2_fourcc('M', 'J', 'P', 'G')
V4L2_PIX_FMT_JPEG = _v4l2_fourcc('J', 'P', 'E', 'G')
V4L2_PIX_FMT_H264 = _v4l2_fourcc('H', '2', '6', '4')
V4L2_PIX_FMT_NV12 = _v4l2_fourcc('N', 'V', '1', '2')
V4L2_PIX_FMT_NV21 = _v4l2_fourcc('N', 'V', '2', '1')

# Capability flags
V4L2_CAP_VIDEO_CAPTURE = 0x00000001
V4L2_CAP_VIDEO_OUTPUT = 0x00000002
V4L2_CAP_VIDEO_OVERLAY = 0x00000004
V4L2_CAP_STREAMING = 0x04000000
V4L2_CAP_READWRITE = 0x01000000

# Control IDs
V4L2_CID_BASE = 0x00980900
V4L2_CID_BRIGHTNESS = V4L2_CID_BASE + 0
V4L2_CID_CONTRAST = V4L2_CID_BASE + 1
V4L2_CID_SATURATION = V4L2_CID_BASE + 2
V4L2_CID_HUE = V4L2_CID_BASE + 3
V4L2_CID_AUDIO_VOLUME = V4L2_CID_BASE + 5
V4L2_CID_AUDIO_BALANCE = V4L2_CID_BASE + 6
V4L2_CID_AUDIO_BASS = V4L2_CID_BASE + 7
V4L2_CID_AUDIO_TREBLE = V4L2_CID_BASE + 8
V4L2_CID_AUDIO_MUTE = V4L2_CID_BASE + 9
V4L2_CID_AUDIO_LOUDNESS = V4L2_CID_BASE + 10
V4L2_CID_BLACK_LEVEL = V4L2_CID_BASE + 11
V4L2_CID_AUTO_WHITE_BALANCE = V4L2_CID_BASE + 12
V4L2_CID_DO_WHITE_BALANCE = V4L2_CID_BASE + 13
V4L2_CID_RED_BALANCE = V4L2_CID_BASE + 14
V4L2_CID_BLUE_BALANCE = V4L2_CID_BASE + 15
V4L2_CID_GAMMA = V4L2_CID_BASE + 16
V4L2_CID_EXPOSURE = V4L2_CID_BASE + 17
V4L2_CID_AUTOGAIN = V4L2_CID_BASE + 18
V4L2_CID_GAIN = V4L2_CID_BASE + 19
V4L2_CID_HFLIP = V4L2_CID_BASE + 20
V4L2_CID_VFLIP = V4L2_CID_BASE + 21
V4L2_CID_POWER_LINE_FREQUENCY = V4L2_CID_BASE + 24
V4L2_CID_HUE_AUTO = V4L2_CID_BASE + 25
V4L2_CID_WHITE_BALANCE_TEMPERATURE = V4L2_CID_BASE + 26
V4L2_CID_SHARPNESS = V4L2_CID_BASE + 27
V4L2_CID_BACKLIGHT_COMPENSATION = V4L2_CID_BASE + 28
V4L2_CID_CHROMA_AGC = V4L2_CID_BASE + 29
V4L2_CID_COLOR_KILLER = V4L2_CID_BASE + 30

# Camera class controls
V4L2_CID_CAMERA_CLASS_BASE = 0x009a0900
V4L2_CID_EXPOSURE_AUTO = V4L2_CID_CAMERA_CLASS_BASE + 1
V4L2_CID_EXPOSURE_ABSOLUTE = V4L2_CID_CAMERA_CLASS_BASE + 2
V4L2_CID_EXPOSURE_AUTO_PRIORITY = V4L2_CID_CAMERA_CLASS_BASE + 3
V4L2_CID_PAN_RELATIVE = V4L2_CID_CAMERA_CLASS_BASE + 4
V4L2_CID_TILT_RELATIVE = V4L2_CID_CAMERA_CLASS_BASE + 5
V4L2_CID_PAN_RESET = V4L2_CID_CAMERA_CLASS_BASE + 6
V4L2_CID_TILT_RESET = V4L2_CID_CAMERA_CLASS_BASE + 7
V4L2_CID_PAN_ABSOLUTE = V4L2_CID_CAMERA_CLASS_BASE + 8
V4L2_CID_TILT_ABSOLUTE = V4L2_CID_CAMERA_CLASS_BASE + 9
V4L2_CID_FOCUS_ABSOLUTE = V4L2_CID_CAMERA_CLASS_BASE + 10
V4L2_CID_FOCUS_RELATIVE = V4L2_CID_CAMERA_CLASS_BASE + 11
V4L2_CID_FOCUS_AUTO = V4L2_CID_CAMERA_CLASS_BASE + 12
V4L2_CID_ZOOM_ABSOLUTE = V4L2_CID_CAMERA_CLASS_BASE + 13
V4L2_CID_ZOOM_RELATIVE = V4L2_CID_CAMERA_CLASS_BASE + 14
V4L2_CID_ZOOM_CONTINUOUS = V4L2_CID_CAMERA_CLASS_BASE + 15
V4L2_CID_PRIVACY = V4L2_CID_CAMERA_CLASS_BASE + 16


# Structures
class v4l2_capability(ctypes.Structure):
    """V4L2 device capability structure."""
    _fields_ = [
        ('driver', c_char * 16),
        ('card', c_char * 32),
        ('bus_info', c_char * 32),
        ('version', c_uint32),
        ('capabilities', c_uint32),
        ('device_caps', c_uint32),
        ('reserved', c_uint32 * 3),
    ]


class v4l2_pix_format(ctypes.Structure):
    """V4L2 pixel format structure."""
    _fields_ = [
        ('width', c_uint32),
        ('height', c_uint32),
        ('pixelformat', c_uint32),
        ('field', c_uint32),
        ('bytesperline', c_uint32),
        ('sizeimage', c_uint32),
        ('colorspace', c_uint32),
        ('priv', c_uint32),
        ('flags', c_uint32),
        ('ycbcr_enc', c_uint32),
        ('quantization', c_uint32),
        ('xfer_func', c_uint32),
    ]


class v4l2_format_union(ctypes.Union):
    """Union for format types."""
    _fields_ = [
        ('pix', v4l2_pix_format),
        ('raw_data', c_char * 200),
    ]


class v4l2_format(ctypes.Structure):
    """V4L2 format structure."""
    _fields_ = [
        ('type', c_uint32),
        ('fmt', v4l2_format_union),
    ]


class v4l2_requestbuffers(ctypes.Structure):
    """V4L2 request buffers structure."""
    _fields_ = [
        ('count', c_uint32),
        ('type', c_uint32),
        ('memory', c_uint32),
        ('capabilities', c_uint32),
        ('flags', c_uint32),
        ('reserved', c_uint32 * 3),
    ]


class v4l2_timecode(ctypes.Structure):
    """V4L2 timecode structure."""
    _fields_ = [
        ('type', c_uint32),
        ('flags', c_uint32),
        ('frames', c_uint8),
        ('seconds', c_uint8),
        ('minutes', c_uint8),
        ('hours', c_uint8),
        ('userbits', c_uint8 * 4),
    ]


class timeval(ctypes.Structure):
    """Time value structure."""
    _fields_ = [
        ('tv_sec', c_int64),
        ('tv_usec', c_int64),
    ]


class v4l2_buffer_m(ctypes.Union):
    """Buffer memory union."""
    _fields_ = [
        ('offset', c_uint32),
        ('userptr', ctypes.c_ulong),
        ('planes', ctypes.c_void_p),
        ('fd', c_int32),
    ]


class v4l2_buffer(ctypes.Structure):
    """V4L2 buffer structure."""
    _fields_ = [
        ('index', c_uint32),
        ('type', c_uint32),
        ('bytesused', c_uint32),
        ('flags', c_uint32),
        ('field', c_uint32),
        ('timestamp', timeval),
        ('timecode', v4l2_timecode),
        ('sequence', c_uint32),
        ('memory', c_uint32),
        ('m', v4l2_buffer_m),
        ('length', c_uint32),
        ('reserved2', c_uint32),
        ('request_fd', c_int32),
    ]


class v4l2_fract(ctypes.Structure):
    """V4L2 fraction structure."""
    _fields_ = [
        ('numerator', c_uint32),
        ('denominator', c_uint32),
    ]


class v4l2_captureparm(ctypes.Structure):
    """V4L2 capture parameter structure."""
    _fields_ = [
        ('capability', c_uint32),
        ('capturemode', c_uint32),
        ('timeperframe', v4l2_fract),
        ('extendedmode', c_uint32),
        ('readbuffers', c_uint32),
        ('reserved', c_uint32 * 4),
    ]


class v4l2_outputparm(ctypes.Structure):
    """V4L2 output parameter structure."""
    _fields_ = [
        ('capability', c_uint32),
        ('outputmode', c_uint32),
        ('timeperframe', v4l2_fract),
        ('extendedmode', c_uint32),
        ('writebuffers', c_uint32),
        ('reserved', c_uint32 * 4),
    ]


class v4l2_streamparm_parm(ctypes.Union):
    """Stream parameter union."""
    _fields_ = [
        ('capture', v4l2_captureparm),
        ('output', v4l2_outputparm),
        ('raw_data', c_char * 200),
    ]


class v4l2_streamparm(ctypes.Structure):
    """V4L2 stream parameter structure."""
    _fields_ = [
        ('type', c_uint32),
        ('parm', v4l2_streamparm_parm),
    ]


class v4l2_control(ctypes.Structure):
    """V4L2 control structure."""
    _fields_ = [
        ('id', c_uint32),
        ('value', c_int32),
    ]


class v4l2_queryctrl(ctypes.Structure):
    """V4L2 query control structure."""
    _fields_ = [
        ('id', c_uint32),
        ('type', c_uint32),
        ('name', c_char * 32),
        ('minimum', c_int32),
        ('maximum', c_int32),
        ('step', c_int32),
        ('default_value', c_int32),
        ('flags', c_uint32),
        ('reserved', c_uint32 * 2),
    ]


class v4l2_fmtdesc(ctypes.Structure):
    """V4L2 format description structure."""
    _fields_ = [
        ('index', c_uint32),
        ('type', c_uint32),
        ('flags', c_uint32),
        ('description', c_char * 32),
        ('pixelformat', c_uint32),
        ('mbus_code', c_uint32),
        ('reserved', c_uint32 * 3),
    ]


class v4l2_frmsizeenum(ctypes.Structure):
    """V4L2 frame size enumeration structure."""
    _fields_ = [
        ('index', c_uint32),
        ('pixel_format', c_uint32),
        ('type', c_uint32),
        ('discrete_width', c_uint32),
        ('discrete_height', c_uint32),
        ('reserved', c_uint32 * 6),
    ]


# ioctl commands
VIDIOC_QUERYCAP = _IOR(ord('V'), 0, ctypes.sizeof(v4l2_capability))
VIDIOC_ENUM_FMT = _IOWR(ord('V'), 2, ctypes.sizeof(v4l2_fmtdesc))
VIDIOC_G_FMT = _IOWR(ord('V'), 4, ctypes.sizeof(v4l2_format))
VIDIOC_S_FMT = _IOWR(ord('V'), 5, ctypes.sizeof(v4l2_format))
VIDIOC_REQBUFS = _IOWR(ord('V'), 8, ctypes.sizeof(v4l2_requestbuffers))
VIDIOC_QUERYBUF = _IOWR(ord('V'), 9, ctypes.sizeof(v4l2_buffer))
VIDIOC_QBUF = _IOWR(ord('V'), 15, ctypes.sizeof(v4l2_buffer))
VIDIOC_DQBUF = _IOWR(ord('V'), 17, ctypes.sizeof(v4l2_buffer))
VIDIOC_STREAMON = _IOW(ord('V'), 18, ctypes.sizeof(ctypes.c_int))
VIDIOC_STREAMOFF = _IOW(ord('V'), 19, ctypes.sizeof(ctypes.c_int))
VIDIOC_G_PARM = _IOWR(ord('V'), 21, ctypes.sizeof(v4l2_streamparm))
VIDIOC_S_PARM = _IOWR(ord('V'), 22, ctypes.sizeof(v4l2_streamparm))
VIDIOC_G_CTRL = _IOWR(ord('V'), 27, ctypes.sizeof(v4l2_control))
VIDIOC_S_CTRL = _IOWR(ord('V'), 28, ctypes.sizeof(v4l2_control))
VIDIOC_QUERYCTRL = _IOWR(ord('V'), 36, ctypes.sizeof(v4l2_queryctrl))
VIDIOC_ENUM_FRAMESIZES = _IOWR(ord('V'), 74, ctypes.sizeof(v4l2_frmsizeenum))


def fourcc_to_string(fourcc: int) -> str:
    """Convert FourCC code to string."""
    return (
        chr(fourcc & 0xFF) +
        chr((fourcc >> 8) & 0xFF) +
        chr((fourcc >> 16) & 0xFF) +
        chr((fourcc >> 24) & 0xFF)
    )


def string_to_fourcc(s: str) -> int:
    """Convert string to FourCC code."""
    return _v4l2_fourcc(s[0], s[1], s[2], s[3])
