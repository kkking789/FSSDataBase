import os

import json

import matplotlib.pyplot as plt
from ansys.aedt.core import Hfss
from ansys.aedt.core.modules import variation
from ansys.aedt.core.visualization.post.solution_data import SolutionData

from PIL import Image, ImageDraw
from ansys.aedt.core.generic.constants import Axis
from utils import *
from utils.types import *
import time
import numpy as np
import math


class Operation:
    def __init__(self, app: Hfss, path: str):
        self.app = app
        self.modeler = app.modeler

        self.data = []
        self.Zbias = 0
        self.branch = 0
        self.unit = 0
        self.subH = 0
        self.d = 0
        self.freqs = []
        self.points = 50
        self.angles = []
        self.subs = []
        self.material = []
        self.build = {}
        self.build["var"] = {}
        self.operate_idx = 0
        self.solutions = None
        self.idx = time.time()
        self.path = path+fr"\{self.idx}"
        os.makedirs(self.path, exist_ok=True)

    def DrawGroup1(self, data: list, Zbias:float = 0):
        self.data = data
        modeler = self.modeler
        idx = 0
        rect_list = []
        width = self.unit.wire_width
        self.Zbias = Zbias

        for item in self.data:
            begin = item[0]
            angle = item[1]
            distance = item[2]
            pivot = [f"{begin[0]}mm", f"{begin[1]}mm", f"{Zbias}mm"]
            cs = modeler.create_coordinate_system(
                origin=pivot,
                reference_cs="Global",
                name=f"RotatePivotCS{idx}",
                mode="axis",
                x_pointing=[1, 0, 0],
                y_pointing=[0, 1, 0],
            )
            modeler.set_working_coordinate_system(f"RotatePivotCS{idx}")
            if idx == 0:
                rect_name = "metal"
            else:
                rect_name = f"Rec{idx}"
            rect = modeler.create_rectangle("XY", origin=[0, f"-{width / 2}mm", 0],
                                            sizes=[f"{distance}mm", f"{width}mm"], name=rect_name)
            rect_list.append(rect)
            modeler.rotate(
                assignment=rect_name,
                axis=Axis.Z,
                angle=angle,
                units="deg"
            )
            modeler.set_working_coordinate_system("Global")

            self.build[f"CreatCs_{self.operate_idx}"] = [pivot, "Global", f"RotatePivotCS{idx}", "axis", [1, 0, 0], [0, 1, 0]]
            self.operate_idx += 1
            self.build[f"SetWorkCs_{self.operate_idx}"] = ["LastCreateCs"]
            self.operate_idx += 1
            self.build[f"CreateRec_{self.operate_idx}"] = ["XY", [0, f"-{width / 2}mm", 0], [f"{distance}mm", f"{width}mm"], rect_name]
            self.operate_idx += 1
            self.build[f"Rotate_{self.operate_idx}"] = [rect_name, "Axis.Z", angle, "deg"]
            self.operate_idx += 1
            self.build[f"SetWorkCs_{self.operate_idx}"] = ["Global"]
            self.operate_idx += 1
            idx += 1

        modeler.unite(rect_list)
        self.build[f"Unite_{self.operate_idx}"] = [rect.name for rect in rect_list]
        self.operate_idx += 1

    def RotateBranch(self, branch: int):
        self.branch = branch
        modeler = self.modeler
        metal_ = modeler.duplicate_around_axis("metal", Axis.Z, angle=int(360 / branch), clones=branch)
        metal = ["metal"]
        for idx in range(1, branch):
            metal.append(metal_[1][idx - 1])
        modeler.unite(metal)

        self.build[f"DupAxis_{self.operate_idx}"] = ["metal", "Axis.Z", int(360 / branch), branch]
        self.operate_idx += 1
        self.build[f"Unite_{self.operate_idx}"] = metal
        self.operate_idx += 1

    def BoundarySet(self):
        self.app["angle"] = "0deg"
        self.build["var"]["angle"] = "0deg"

        modeler = self.modeler
        app = self.app
        h = self.subH
        d = self.d

        f = 1e9
        extraH = int(3e8 / f / 4 * 1000)
        airbox = modeler.create_box([f"{-d / 2}mm", f"{-d / 2}mm", f"-{h + extraH / 2}mm"],
                                    [f"{d}mm", f"{d}mm", f"{h * 2 + extraH}mm"], name="air_box", material="air")

        top_sheet = modeler.create_rectangle("XY", origin=[f"{-d / 2}mm", f"{-d / 2}mm", f"{h + extraH / 2}mm"],
                                         sizes=[f"{d}mm", f"{d}mm"],
                                         name="TopSheet", material="Vacuum")
        floquet_top = app.create_floquet_port(
            assignment=top_sheet.name,
            deembed_distance=extraH,
            modes=2,
            name="Floquet_Top"
        )
        bottom_sheet = modeler.create_rectangle("XY",
                                                origin=[f"{-d / 2}mm", f"{-d / 2}mm", f"-{h + extraH / 2}mm"],
                                                sizes=[f"{d}mm", f"{d}mm"],
                                                name="BottomSheet", material="Vacuum")
        floquet_bottom = app.create_floquet_port(
            assignment=bottom_sheet.name,
            deembed_distance=int(extraH),
            modes=2,
            name="Floquet_Bottom"
        )
        primary1_sheet = modeler.create_rectangle(
            "XZ",
            origin=[f"{-d / 2}mm", f"{-d / 2}mm", f"-{h + extraH / 2}mm"],
            sizes=[f"{h * 2 + extraH}mm", f"{d}mm"],
            name="Primary1_Sheet",
            material="Vacuum"
        )
        primary1 = app.assign_primary(
            assignment=primary1_sheet.id,
            u_start=[f"{d / 2}mm", f"-{d / 2}mm", f"{h + extraH / 2}mm"],
            u_end=[f"-{d / 2}mm", f"-{d / 2}mm", f"{h + extraH / 2}mm"],
            name="Primary1"
        )

        slave1_sheet = modeler.create_rectangle(
            "XZ",
            origin=[f"{-d / 2}mm", f"{d / 2}mm", f"-{h + extraH / 2}mm"],
            sizes=[f"{h * 2 + extraH}mm", f"{d}mm"],
            name="Slave1_Sheet",
            material="Vacuum"
        )

        slave1 = app.assign_secondary(
            assignment=slave1_sheet.id,
            primary=primary1.name,
            u_start=[f"{d / 2}mm", f"{d / 2}mm", f"{h + extraH / 2}mm"],
            u_end=[f"{-d / 2}mm", f"{d / 2}mm", f"{h + extraH / 2}mm"],
            phase_delay_param2="angle",
            name="Slave1"
        )

        primary2_sheet = modeler.create_rectangle(
            "YZ",
            origin=[f"{-d / 2}mm", f"{-d / 2}mm", f"-{h + extraH / 2}mm"],
            sizes=[f"{d}mm", f"{h * 2 + extraH}mm"],
            name="Primary2_Sheet",
            material="Vacuum"
        )
        primary2 = app.assign_primary(
            assignment=primary2_sheet.id,
            u_start=[f"-{d / 2}mm", f"{d / 2}mm", f"{h + extraH / 2}mm"],
            u_end=[f"-{d / 2}mm", f"-{d / 2}mm", f"{h + extraH / 2}mm"],
            name="Primary2",
            reverse_v=True
        )

        slave2_sheet = modeler.create_rectangle(
            "YZ",
            origin=[f"{d / 2}mm", f"-{d / 2}mm", f"-{h + extraH / 2}mm"],
            sizes=[f"{d}mm", f"{h * 2 + extraH}mm"],
            name="Slave2_Sheet",
            material="Vacuum"
        )

        slave2 = app.assign_secondary(
            assignment=slave2_sheet.id,
            primary=primary2.name,
            u_start=[f"{d / 2}mm", f"{d / 2}mm", f"{h + extraH / 2}mm"],
            u_end=[f"{d / 2}mm", f"-{d / 2}mm", f"{h + extraH / 2}mm"],
            name="Slave2",
            phase_delay_param2="angle",
            reverse_v=True
        )

        metal_boundary = app.assign_perfect_e(["metal"], name="metal_boundary")

    def SetSolution(self, freqs: list, points: int = 50, angles: list = None):
        if angles is None:
            angles = []

        self.freqs = freqs
        self.points = points
        self.angles = angles
        app = self.app

        setup = app.create_setup("Setup1")
        sweep = None
        for freq in freqs:
            if sweep is None:
                sweep = setup.create_frequency_sweep(
                    name="LinearStepSweep", unit="GHz", start_frequency=freq[0], stop_frequency=freq[1],
                    num_of_freq_points=points,
                    save_fields=False
                )
            else:
                sweep.add_subrange(
                    range_type="LinearCount",
                    start=freq[0],
                    end=freq[1],
                    count=points,
                    unit="GHz"
                )
        angle_sweep = None
        if angles is not None:
            for angle in angles:
                if angle_sweep is None:
                    angle_sweep = app.parametrics.add(
                        variable="angle",
                        start_point=angle[0],
                        end_point=angle[1],
                        step=angle[2],
                        name="AngleSweep"
                    )
                angle_sweep.add_variation(
                    sweep_variable="angle",
                    start_point=angle[0],
                    end_point=angle[1],
                    step=angle[2],
                )

    def SetMaterial(self, material: list):
        self.material = material
        app = self.app

        for detail in material:
            material_ = app.materials.add_material(detail.name)
            material_.permittivity = detail.permittivity
            material_.permeability = detail.permeability
            material_.dielectric_loss_tangent = detail.dielectric_loss_tangent

    def SubstrateSet(self, subs: list, unit: Unit):
        self.subs = subs
        self.unit = unit

        modeler = self.modeler
        d = unit.size*2
        self.d = d
        bias = 0
        idx = 0

        for detail in subs:
            sub = modeler.create_box([f"-{d / 2}mm", f"-{d / 2}mm", f"{bias}mm"], [f"{d}mm", f"{d}mm", f"{detail.h}mm"],
                                     name=f"sub{idx}", material=f"{detail.material.name}")
            bias += detail.h
            idx += 1

        self.subH = bias

    def SetReport(self, direction: str):
        app = self.app
        variations = app.available_variations.nominal_values
        variations["angle"] = ["All"]

        if direction == "S11":
            expressions = ["dB(S(Floquet_Top:1,Floquet_Top:1))","dB(S(Floquet_Top:2,Floquet_Top:2))"]
        else:
            expressions = ["dB(S(Floquet_Top:1,Floquet_Bottom:1))","dB(S(Floquet_Top:2,Floquet_Bottom:2))"]
        report = app.post.create_report(expressions=expressions, variations=variations)
        self.solutions = report.get_solution_data()


    def JsonGenerate(self, author: str):
        data = {}
        sub_idx = 0
        idx = self.idx
        file_path = self.path
        data["author"] = author
        data["time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        data["idx"] = idx
        data["material"] = {}
        data["sub"] = {}
        for detail in self.material:
            data["material"][detail.name] ={
                "permittivity": detail.permittivity,
                "permeability": detail.permeability,
                "dielectric_loss_tangent": detail.dielectric_loss_tangent
            }
        for detail in self.subs:
            sub_idx += 1
            data["sub"][f"sub{sub_idx}"] = {
                "material": detail.material.name,
                "h": detail.h,
            }
        data["range_freq"] = self.freqs
        data["points"] = self.points
        data["range_angle"] = self.angles
        data["build"] = self.build

        with open(f"{file_path}/data.json", "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=4)

    def PNGandMaskGenerate(self, size: int = 500):
        image = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(image)
        d = self.d
        width = self.unit.wire_width

        def rec2pixel(point,angle,length,width):
            x = point[0]*size/d
            y = point[1]*size/d
            rad  = angle/180*math.pi
            bias = size/2
            dx = width/2*math.sin(rad)*size/d
            dy = width/2*math.cos(rad)*size/d

            x0 = x + dx + bias
            y0 = y - dy + bias
            x1 = x - dx + bias
            y1 = y + dy + bias

            x2 = x + length*math.cos(rad)*size/d - dx+bias
            y2 = y + length*math.sin(rad)*size/d + dy+bias
            x3 = x + length*math.cos(rad)*size/d + dx + bias
            y3 = y + length*math.sin(rad)*size/d - dy + bias

            y0 = size - 1 - y0
            y1 = size - 1 - y1
            y2 = size - 1 - y2
            y3 = size - 1 - y3

            return [(x0,y0),(x1,y1),(x2,y2),(x3,y3)]

        for item in self.data:
            begin = item[0]
            r = math.sqrt(begin[0]**2+begin[1]**2)
            theta = math.atan2(begin[1],begin[0])*180/math.pi
            angle = item[1]
            distance = item[2]
            for idx in range(self.branch):
                x = r*math.cos((theta+int(360/self.branch)*idx)/180*math.pi)
                y = r*math.sin((theta+int(360/self.branch)*idx)/180*math.pi)
                xy = rec2pixel([x,y],angle+int(360/self.branch)*idx,distance,width)
                draw.polygon(xy, fill=255)

        image.save(self.path + rf"\structure.png")
        img = Image.open(self.path + rf"\structure.png").convert("L")
        mask = (np.array(img) > 0).astype(np.uint8)
        np.savetxt(f"{self.path}/mask.csv", mask, delimiter=",", fmt="%d")

    def ResultsGenerate(self, passdB: float = -3, blockdB: float = -10):
        solutions = self.solutions
        expressions = list(solutions.expressions)
        sweep_names = list(solutions._sweeps_names)

        angle_idx = sweep_names.index("angle")
        freq_idx = sweep_names.index("Freq")

        te_expr = expressions[0]
        tm_expr = expressions[1]

        te_real_data = np.asarray(solutions._solutions_real[te_expr], dtype=float)
        tm_real_data = np.asarray(solutions._solutions_real[tm_expr], dtype=float)

        angle = te_real_data[:, angle_idx]
        freq = te_real_data[:, freq_idx]

        te_real = te_real_data[:, -1]
        tm_real = tm_real_data[:, -1]

        raw_data = np.column_stack(
            [angle, freq, te_real, tm_real]
        )
        angles = np.unique(raw_data[:, 0])
        te_label = np.where(te_real > passdB, 0, np.where(te_real < -blockdB, -10, -5))
        tm_label = np.where(tm_real > passdB, 0, np.where(tm_real < -blockdB, -10, -5))
        label_data = np.column_stack([angle, freq, te_label, tm_label])

        np.savetxt(f"{self.path}/raw_result.csv", raw_data, delimiter=",", fmt="%f")
        np.savetxt(f"{self.path}/label_result.csv", label_data, delimiter=",", fmt="%f")

        def plot_one_band(freq_min: float, freq_max: float, save_path: str, data: np.ndarray, component:str = "TE", angle_tol:float = 1e-3):
            plt.figure(figsize=(10, 6))

            if component == "TE":
                value_col = 2
            else:
                value_col = 3

            for angle in angles:
                mask_angle = np.isclose(raw_data[:, 0], angle, atol=angle_tol)
                data_sub = data[mask_angle]

                mask_band = (data_sub[:, 1] >= freq_min) & (data_sub[:, 1] <= freq_max)
                data_sub = data_sub[mask_band]

                if data_sub.shape[0] == 0:
                    continue

                order = np.argsort(data_sub[:, 1])
                data_sub = data_sub[order]
                freq = data_sub[:, 1]
                raw_y = data_sub[:, value_col]

                plt.plot(freq, raw_y, linestyle="-", label=f"angle={angle:g}deg")

            plt.xlabel("Frequency (GHz)")
            plt.ylabel(f"dB")
            plt.title(f"idx{self.idx} simulate {component} result")
            plt.grid(True)
            plt.legend()
            plt.tight_layout()
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()

        for detail in self.freqs:
            plot_one_band(detail[0], detail[1], self.path+f"/{detail[0]}~{detail[1]}Ghz_TE.png", raw_data, "TE")
            plot_one_band(detail[0], detail[1], self.path + f"/{detail[0]}~{detail[1]}Ghz_TM.png", raw_data, "TM")
