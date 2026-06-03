import os
from ansys.aedt.core import Hfss
import json
import utils
import time
from utils import *
import re
from pathlib import Path
from ansys.aedt.core.generic.constants import Axis

_AXIS_MAP = {
    "Axis.X": Axis.X,
    "Axis.Y": Axis.Y,
    "Axis.Z": Axis.Z,
}
_BUILD_KEY_RE = re.compile(r"^([A-Za-z]+)_(\d+)$")

class Rebuild:
    def __init__(self, data_path: str, project_path: str, AEDT_VERSION: str = "2023.1"):
        data_path = str(Path(data_path).expanduser().resolve())
        project_path = str(Path(project_path).expanduser().resolve())

        app = Hfss(
            project=os.path.join(project_path, f"Rebuild"),
            design=f"RebuildDesign",
            version=AEDT_VERSION,
            non_graphical=False,
            new_desktop=False,
        )

        self.app = app
        self.path = data_path

        with open(data_path, 'r') as f:
            self.data = json.load(f)
        self.build = self.data['build']
        self.material = []
        for key, details in self.data['material'].items():
            self.material.append(utils.Material(key,
                                                permeability=details['permeability'],
                                                permittivity=details['permittivity'],
                                                dielectric_loss_tangent=details['dielectric_loss_tangent']))
        self.unit = utils.Unit(size=self.data["unit"][1], wire_width=self.data["unit"][0])
        self.substrate = []
        for key, details in self.data['sub'].items():
            self.substrate.append(utils.Substrate(details["material"],details["h"]))
        self.range_angle = self.data['range_angle']
        self.range_freq = self.data['range_freq']

        self.opt = Operation(app, path=self.path, unit = self.unit)

    def rebuild(self):
        self._structure_rebuild()
        self.opt.SetMaterial(self.material)
        self.opt.SubstrateSet(self.substrate)
        self.opt.BoundarySet()
        self.opt.SetSolution(self.range_freq, self.range_angle)

    def _structure_rebuild(self):
        app = self.app
        build = self.build
        modeler = app.modeler

        def parse_build_key(key: str):
            match = _BUILD_KEY_RE.match(key)
            if not match:
                return key, -1

            return match.group(1), int(match.group(2))

        for operate, details in build.items():
            if operate == 'var':
                for name, value in details.items():
                    app[name] = value
                continue
            operate,_ = parse_build_key(operate)
            if operate == 'Curve':
                modeler.create_equationbased_curve(x_t=details[0], y_t=details[1], z_t=details[2], name=details[3])
            elif operate == 'Unite':
                modeler.unite(details)
            elif operate == 'Rename':
                modeler[details[0]].name = details[1]
            elif operate == 'Cover':
                modeler.cover_lines(details[0])
            elif operate == 'CreatCs':
                modeler.create_coordinate_system(
                    origin=details[0],
                    reference_cs=details[1],
                    name=details[2],
                    mode=details[3],
                    x_pointing=details[4],
                    y_pointing=details[5],
                )
            elif operate == 'SetWorkCs':
                modeler.set_working_coordinate_system(details[0])
            elif operate == 'CreateRec':
                modeler.create_rectangle(details[0], origin=details[1], sizes=details[2], name=details[3])
            elif operate == 'Rotate':
                modeler.rotate(
                    assignment=details[0],
                    axis=_AXIS_MAP[details[1]],
                    angle=details[2],
                    units=details[3],
                )
            elif operate == 'DupAxis':
                modeler.duplicate_around_axis(details[0], axis=_AXIS_MAP[details[1]], angle=details[2], clones=details[3])
            elif operate == 'Line':
                modeler.create_polyline(points=details[0], name=details[1])
            else:
                raise ValueError(f"Invalid operate: {operate}, please check the json")

        for name in list(modeler.objects_by_name.keys()):
            object_name,_ = parse_build_key(name)
            if object_name == "metal":
                app.assign_perfect_e([name], name=f"metal_boundary_{name}")
            else:
                raise Exception(f"the {object_name} object is not the metal,please check the json")