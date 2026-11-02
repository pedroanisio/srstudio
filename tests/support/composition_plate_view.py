"""A canonical point through the plate camera as the engine projects it, shared by the plate-view and spatial
camera tests."""

from srstudio import proxy


def engine_project(view, point):
    camera = view.camera
    lens = proxy.View(camera.position, camera.target, camera.fov, size=(view.width, view.height))
    return lens.project([view.point(point)])[0] + view.offset
