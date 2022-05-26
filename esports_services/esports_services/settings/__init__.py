from .common import *


if LOCAL_MODE:
    from .local import *
else:
    from .production import *
