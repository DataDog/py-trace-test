import types
import typing

from .. import event

def traceback_to_frames(
    traceback: types.TracebackType, max_nframes: int
) -> typing.Tuple[typing.List[event.DDFrame], int]: ...
def pyframe_to_frames(frame: types.FrameType, max_nframes: int) -> typing.Tuple[typing.List[event.DDFrame], int]: ...
