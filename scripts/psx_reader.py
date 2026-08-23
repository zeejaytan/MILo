"""Read a Metashape project without Metashape.

A `.psx` is a few lines of XML pointing at a `<name>.files/` directory; the substance
lives in `chunk.zip` and `frame.zip` inside it, and both are plain zipped XML. So a
project made by the conservator in a licensed copy of Metashape can be read here, on the
laptop, with nothing installed. That is the whole reason this module exists: the N01
capture already HAS a professional solve, and it was sitting in the Mediaflux archive
unread.

What it gives you:

    proj = Project(chunk_xml, frame_xml)
    proj.calib          -- f, cx, cy, k1, p1, p2   (pixels, stored-frame convention)
    proj.cameras        -- name -> Camera(name, M)  where M is camera->chunk 4x4
    proj.markers        -- label -> Marker(label, kind, number, {camera_name: (x, y)})
    proj.scalebars      -- [(label_a, label_b, metres)]
    proj.chunk_scale    -- multiply a chunk-space length by this to get metres

TWO CONVENTIONS THAT WILL BITE IF YOU GUESS THEM.

Image coordinates. Every N01 frame carries EXIF orientation 8, meaning the pixels are
stored sideways and a viewer is expected to rotate them. Metashape records that tag but
declares the sensor 5568x3712 -- the STORED frame -- and its marker coordinates are in
that same stored frame. COLMAP also reads stored pixels and ignores the tag. So Metashape
and COLMAP agree already and nothing needs rotating. This was tested rather than assumed:
of the four candidate mappings, only the identity puts Metashape's marker positions on top
of independently detected ones (0.78 px median; the three rotations give 1668, 3110 and
4601 px).

Camera transform. `<transform>` is the camera-to-chunk matrix -- its translation column IS
the camera centre, not a COLMAP-style -R't. Metashape's camera looks down +Z with +X right
and +Y down, the same optical convention OpenCV uses, so the world->camera matrix `inv(M)`
drops straight into cv2.projectPoints / solvePnP without a handedness flip.
"""
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Calibration:
    width: int
    height: int
    f: float
    cx: float            # principal point in pixels from the image corner
    cy: float
    k1: float = 0.0
    k2: float = 0.0
    k3: float = 0.0
    p1: float = 0.0
    p2: float = 0.0

    @property
    def K(self):
        return np.array([[self.f, 0, self.cx], [0, self.f, self.cy], [0, 0, 1]], float)

    @property
    def dist(self):
        """OpenCV's (k1, k2, p1, p2, k3) -- WITH METASHAPE'S TANGENTIAL TERMS SWAPPED.

        Metashape and OpenCV both call their tangential coefficients p1 and p2, and they
        mean the opposite things by them: Metashape puts p1 on the (r^2 + 2x^2) term,
        OpenCV puts p2 there. Feeding Metashape's p1/p2 straight into cv2 is silently
        wrong -- not a crash, just a few pixels, which is exactly the size of error that
        gets mistaken for "triangulation noise" and reported as a result.

        This is not inferred from the docs. Projecting Metashape's own solved marker
        positions through this model and comparing against its own stored image
        measurements gives 0.00 px rms over 382 projections; with p1/p2 as written it
        gives 8.84 px, which is worse than using no distortion model at all (8.27).
        """
        return np.array([self.k1, self.k2, self.p2, self.p1, self.k3], float)


@dataclass
class Camera:
    name: str
    M: np.ndarray        # 4x4 camera -> chunk

    @property
    def centre(self):
        return self.M[:3, 3]

    @property
    def world_to_cam(self):
        return np.linalg.inv(self.M)


@dataclass
class Marker:
    label: str
    kind: str            # "target" for a decoded coded target, "point" for a hand-placed one
    number: int          # the number printed beside it on the board, or the point's number
    proj: dict = field(default_factory=dict)     # camera name -> (x, y) in stored pixels
    pinned: dict = field(default_factory=dict)   # camera name -> bool
    ref: np.ndarray = None      # Metashape's own solved position, chunk units, if stored


def _text(node, tag, default=None):
    el = node.find(tag)
    return el.text if el is not None else default


class Project:
    def __init__(self, chunk_xml, frame_xml):
        ch = ET.parse(str(chunk_xml)).getroot()
        fr = ET.parse(str(frame_xml)).getroot()

        sensor = ch.find("sensors/sensor")
        cal = sensor.find("calibration")
        cres = cal.find("resolution")
        w, h = int(cres.get("width")), int(cres.get("height"))
        # Metashape stores cx/cy as an OFFSET from the image centre and omits the element
        # when it is zero, which is the case here. OpenCV wants absolute pixels.
        self.calib = Calibration(
            width=w, height=h,
            f=float(_text(cal, "f")),
            cx=w / 2 + float(_text(cal, "cx", 0)),
            cy=h / 2 + float(_text(cal, "cy", 0)),
            k1=float(_text(cal, "k1", 0)), k2=float(_text(cal, "k2", 0)),
            k3=float(_text(cal, "k3", 0)),
            p1=float(_text(cal, "p1", 0)), p2=float(_text(cal, "p2", 0)),
        )

        self.chunk_scale = float(_text(ch, "transform/scale", 1.0))

        # The frame file speaks only in numeric ids; the chunk file holds the labels.
        self.cameras, cam_name = {}, {}
        for c in ch.findall("cameras/camera"):
            name = c.get("label")
            cam_name[c.get("id")] = name
            t = _text(c, "transform")
            if t is None:                       # an unaligned photo has no transform
                continue
            self.cameras[name] = Camera(name, np.array(t.split(), float).reshape(4, 4))

        self.markers, mk_label = {}, {}
        for m in ch.findall("markers/marker"):
            label = m.get("label")
            mk_label[m.get("id")] = label
            kind, _, num = label.partition(" ")
            mk = Marker(label, kind, int(num) if num.isdigit() else -1)
            r = m.find("reference")
            if r is not None and r.get("x") is not None:
                mk.ref = np.array([r.get("x"), r.get("y"), r.get("z")], float)
            self.markers[label] = mk

        for m in fr.findall("markers/marker"):
            mk = self.markers.get(mk_label.get(m.get("marker_id")))
            if mk is None:
                continue
            for loc in m.findall("location"):
                nm = cam_name.get(loc.get("camera_id"))
                if nm is None:
                    continue
                mk.proj[nm] = (float(loc.get("x")), float(loc.get("y")))
                mk.pinned[nm] = loc.get("pinned") == "true"

        # A scale bar names its ends by marker id, not by splitting its label -- the label
        # happens to be "point 3_point 4" here, but that is Metashape's default text and
        # nothing stops a person renaming it.
        self.scalebars = []
        for sb in ch.findall("scalebars/scalebar"):
            ends = [mk_label.get(e.get("marker_id")) for e in sb.findall("endpoint")]
            ref = sb.find("reference")
            if len(ends) == 2 and None not in ends and ref is not None:
                self.scalebars.append((ends[0], ends[1], float(ref.get("d")),
                                       ref.get("enabled") == "true"))

    # -- convenience ------------------------------------------------------------------

    def targets(self):
        """Only the machine-decoded coded targets, ordered by the number printed on the board.

        The hand-placed `point` markers are excluded on purpose: they are flagged
        pinned="false", which in Metashape can mean a projection the software propagated
        rather than one a person clicked. Good enough to look at, not good enough to build
        a coordinate frame on.
        """
        return [m for _, m in sorted(
            ((m.number, m) for m in self.markers.values() if m.kind == "target"),
            key=lambda t: t[0])]

    def undistort(self, xy):
        """Image point -> ideal pinhole image point, same pixel units."""
        import cv2
        pts = np.asarray(xy, float).reshape(-1, 1, 2)
        return cv2.undistortPoints(pts, self.calib.K, self.calib.dist,
                                   P=self.calib.K).reshape(-1, 2)

    def triangulate(self, marker, min_views=2):
        """Linear SVD triangulation of one marker from its projections, in chunk units.

        Distortion is undone first, so this is a true ray intersection rather than the
        approximation an earlier pass here used.
        """
        views = [(nm, xy) for nm, xy in marker.proj.items() if nm in self.cameras]
        if len(views) < min_views:
            return None
        K = self.calib.K
        rows = []
        for nm, xy in views:
            u, v = self.undistort(xy)[0]
            P = K @ self.cameras[nm].world_to_cam[:3, :]
            rows.append(u * P[2] - P[0])
            rows.append(v * P[2] - P[1])
        _, _, Vt = np.linalg.svd(np.array(rows))
        X = Vt[-1]
        return X[:3] / X[3]


def find_project(root):
    """Locate chunk.xml / frame.xml under a directory, whatever they are called.

    Metashape's own unpacked layout names both files doc.xml (x/chunk/doc.xml,
    x/frame/doc.xml), so fall back to reading the root tag rather than the filename.
    """
    root = Path(root)
    chunk = next(iter(sorted(root.rglob("chunk.xml"))), None)
    frame = next(iter(sorted(root.rglob("frame.xml"))), None)
    if chunk is None or frame is None:
        for p in sorted(root.rglob("doc.xml")):
            tag = ET.parse(str(p)).getroot().tag
            if tag == "chunk" and chunk is None:
                chunk = p
            elif tag == "frame" and frame is None:
                frame = p
    if chunk is None or frame is None:
        raise SystemExit(f"no chunk.xml / frame.xml under {root}")
    return chunk, frame
