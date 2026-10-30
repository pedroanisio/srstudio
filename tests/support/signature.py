"""What test_signature.py shares with other test modules."""

from sr_core.scene import Scene

from srstudio import OFFICE, Canvas
from srstudio.canvas import Signature

# -- the cactus performs (ADR 0039): the defaults keep today's bytes, the act and the hand-off are checked ----------
TODAY = {  # sha256 of each drawing at da62288, before ADR 0039: act=None and cactus=None must keep these bytes
    "office_wide": "729f478cc99ad66244b9bc5c615e6ccce91006b2d9fe97e6f87bcb5ea1cdab9d",
    "office_wide_instanced": "fa6142603e814c9b64d6560100255c13287c627b02e355df82cc4a4f7498effd",
    "office_desk": "0e7b54a2af76bd393dc9576ac6e9f2df4ece6f95abe731d2edad758e1e1c0527",
    "office_desk_instanced": "62f177ce1c205cae33b7cbb9624f8fe2b7898bfe9c30b6b0a3f72df356bc6652",
    "office_reverse": "0059da92b94739b1ea5b13b5ebb27107c75c7b76876d9e054799677e752e98cb",
    "cafe": "fc9747749853f8bf9113ddef01a85b9bfc18e2718aaaf7978a2a0c8e08ad71a8",
    "park": "7890b394f5e9b918401b553951b358f13b9cb8c0c3cece620c5a209027d59592",
    "cactus_mono": "bf04357ead35aed1bc0795e7cc6a385a46c19d1f045f7f18b9fd77add0b3cb16",
    "cactus_office": "c871e0c046158ffc6c29d680d14bb6fb0157cc06695ded927e84aca6edb96881",
}


SPAN = 6.0


def _canvas(palette=OFFICE, signed=True) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=SPAN, background=palette.background)
    return Canvas(scene, palette, signature=Signature() if signed else None)
