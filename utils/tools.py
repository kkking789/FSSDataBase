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
import shutil

class ResultSplit:
    def __init__(self, data, freqs: list, extra: float = 0.01):
        self.angles = np.unique(data[:, 0]).tolist()
        self.data = data
        self.freqs = freqs
        self.extra = extra

    def __iter__(self):
        return self

    def __next__(self):

        if not self.angles:
            raise StopIteration

        angle = self.angles.pop()
        data = self.data
        mask_angle = np.isclose(data[:, 0], angle, atol=1e-3)
        data_sub_ = data[mask_angle]
        output_S11 = []
        output_S21 = []
        output_S11_angle = []
        output_S21_angle = []
        output_freq = []

        for freq in self.freqs:
            mask_band = (data_sub_[:, 1] >= freq[0]) & (data_sub_[:, 1] <= freq[1])
            data_sub = data_sub_[mask_band]

            if data_sub.shape[0] == 0:
                continue

            order = np.argsort(data_sub[:, 1])
            data_sub = data_sub[order]

            output_freq += data_sub[:, 1].tolist()
            output_freq.append(data_sub[:, 1][-1] + self.extra)

            output_S11 += data_sub[:, 2].astype(np.int8).tolist()
            output_S11.append(0)

            output_S21 += data_sub[:, 4].astype(np.int8).tolist()
            output_S21.append(0)

            output_S11_angle += data_sub[:, 6].astype(np.float16).tolist()
            output_S11_angle.append(np.nan)

            output_S21_angle += data_sub[:, 8].astype(np.float16).tolist()
            output_S21_angle.append(np.nan)

        return output_freq, angle, output_S11, output_S21, output_S11_angle, output_S21_angle





class Operation:
    def __init__(self, app: Hfss, path: str, unit: Unit):
        self.app = app
        self.modeler = app.modeler
        self.unit = unit

        self.data = []
        self.Zbias = 0
        self.branch = 0
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
        self.metal_idx = 0
        self.global_idx = 0
        self.solutions = []
        self.idx = time.time()
        self.path = path+fr"\{self.idx}"

        try:
            os.makedirs(self.path, exist_ok=True)
        except FileNotFoundError:
            pass

    def DrawGroup1(self, data: list, Zbias:float = 0):
        self.data.append(data)
        modeler = self.modeler
        idx = self.global_idx
        rect_list = []
        width = self.unit.wire_width
        self.Zbias = Zbias

        for item in data:
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
            if idx == self.global_idx:
                rect_name = f"metal_{self.metal_idx}"
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
            self.build[f"SetWorkCs_{self.operate_idx}"] = [f"RotatePivotCS{idx}"]
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
        self.global_idx = idx

        return True

    def DrawGroup2(self, data: list, Zbias:float = 0):
        modeler = self.modeler
        app = self.app
        idx = self.global_idx
        metal_list = []
        cover = None
        self.Zbias = Zbias

        if type(data[0][0]) == str:
            self.data.append(data)
            for item in data:
                x_up = item[0]
                y_up = item[1]
                x_down = item[2]
                y_down = item[3]
                x_up_start = item[4][0]
                y_up_start = item[4][1]
                x_up_end = item[5][0]
                y_up_end = item[5][1]
                x_down_start = item[6][0]
                y_down_start = item[6][1]
                x_down_end = item[7][0]
                y_down_end = item[7][1]

                modeler.create_equationbased_curve(
                    x_t=f"({x_up})*1mm",
                    y_t=f"({y_up})*1mm",
                    z_t=f"({Zbias})*1mm",
                    name=f"curve_up_{idx}",
                )
                self.build[f"Curve_{self.operate_idx}"] = [f"({x_up})*1mm", f"({y_up})*1mm", f"{Zbias}*1mm",f"curve_up_{idx}"]
                self.operate_idx += 1

                modeler.create_equationbased_curve(
                    x_t=f"({x_down})*1mm",
                    y_t=f"({y_down})*1mm",
                    z_t=f"{Zbias}*1mm",
                    name=f"curve_down_{idx}"
                )
                self.build[f"Curve_{self.operate_idx}"] = [f"({x_down})*1mm", f"({y_down})*1mm", f"{Zbias}*1mm", f"curve_down_{idx}"]
                self.operate_idx += 1

                start_line = modeler.create_polyline(
                    points=[
                        [f"{x_up_start}mm", f"{y_up_start}mm", f"{Zbias}mm"],
                        [f"{x_down_start}mm", f"{y_down_start}mm", f"{Zbias}mm"],
                    ],
                    name=f"connect_start_{idx}",
                )
                self.build[f"Line_{self.operate_idx}"] = [[
                        [f"{x_up_start}mm", f"{y_up_start}mm", f"{Zbias}mm"],
                        [f"{x_down_start}mm", f"{y_down_start}mm", f"{Zbias}mm"],
                    ], f"connect_start_{idx}"]
                self.operate_idx += 1

                end_line = modeler.create_polyline(
                    points=[
                        [f"{x_up_end}mm", f"{y_up_end}mm", f"{Zbias}mm"],
                        [f"{x_down_end}mm", f"{y_down_end}mm", f"{Zbias}mm"],
                    ],
                    name=f"connect_end_{idx}",
                )
                self.build[f"Line_{self.operate_idx}"] = [[
                        [f"{x_up_end}mm", f"{y_up_end}mm", f"{Zbias}mm"],
                        [f"{x_down_end}mm", f"{y_down_end}mm", f"{Zbias}mm"],
                    ], f"connect_end_{idx}"]
                self.operate_idx += 1

                modeler.unite([f"curve_up_{idx}", f"curve_down_{idx}",f"connect_start_{idx}",f"connect_end_{idx}"])
                self.build[f"Unite_{self.operate_idx}"] = [f"curve_up_{idx}", f"curve_down_{idx}",f"connect_start_{idx}",f"connect_end_{idx}"]
                self.operate_idx += 1

                if cover is None:
                    cover = modeler.cover_lines(f"curve_up_{idx}")
                    modeler[f"curve_up_{idx}"].name = f"metal_{self.metal_idx}"
                    metal_list.append(f"metal_{self.metal_idx}")
                    self.build[f"Cover_{self.operate_idx}"] = [f"curve_up_{idx}"]
                    self.operate_idx += 1

                    self.build[f"Rename_{self.operate_idx}"] = [f"curve_up_{idx}", f"metal_{self.metal_idx}"]
                    self.operate_idx += 1
                else:
                    cover = modeler.cover_lines(f"curve_up_{idx}")
                    metal_list.append(f"curve_up_{idx}")
                    self.build[f"Cover_{self.operate_idx}"] = [f"curve_up_{idx}"]
                    self.operate_idx += 1
                if not cover:
                    return False
                idx+=1
            modeler.unite(metal_list)
            self.build[f"Unite_{self.operate_idx}"] = metal_list
            self.operate_idx += 1
            self.global_idx = idx
        else:
            self.DrawGroup1(data, Zbias)

        metal_boundary = app.assign_perfect_e([f"metal_{self.metal_idx}"], name=f"metal_boundary_{self.metal_idx}")
        self.metal_idx += 1
        if modeler.line_objects:
            return False
        return True

    def DrawGroup3(self, data: list, Zbias: float = 0):
        self.data.append(data)
        modeler = self.modeler
        app = self.app
        idx = self.global_idx
        metal_list = []
        self.Zbias = Zbias

        for item in data:
            x = item[0]
            y = item[1]
            modeler.create_equationbased_curve(
                x_t=f"({x})*1mm",
                y_t=f"({y})*1mm",
                z_t=f"({Zbias})*1mm",
                name=f"curve_{idx}",
            )
            self.build[f"Curve_{self.operate_idx}"] = [f"({x})*1mm", f"({y})*1mm", f"{Zbias}*1mm",
                                                       f"curve_{idx}"]
            self.operate_idx += 1
            metal_list.append(f"curve_{idx}")
            idx += 1

        modeler.unite(metal_list)
        self.build[f"Unite_{self.operate_idx}"] = metal_list
        self.operate_idx += 1

        cover = modeler.cover_lines(metal_list[0])
        self.build[f"Cover_{self.operate_idx}"] = [metal_list[0]]
        self.operate_idx += 1
        modeler[metal_list[0]].name = f"metal_{self.metal_idx}"
        self.build[f"Rename_{self.operate_idx}"] = [metal_list[0], f"metal_{self.metal_idx}"]
        self.operate_idx += 1

        metal_boundary = app.assign_perfect_e([f"metal_{self.metal_idx}"], name=f"metal_boundary_{self.metal_idx}")
        self.metal_idx += 1
        self.global_idx = idx
        if not cover or modeler.line_objects:
            return False
        return True

    def RotateBranch(self, branch: int):
        self.branch = branch
        modeler = self.modeler
        app =self.app
        metal_ = modeler.duplicate_around_axis(f"metal_{self.metal_idx}", Axis.Z, angle=int(360 / branch), clones=branch)
        metal = [f"metal_{self.metal_idx}"]
        for idx in range(1, branch):
            metal.append(metal_[1][idx - 1])
        modeler.unite(metal)

        self.build[f"DupAxis_{self.operate_idx}"] = ["metal", "Axis.Z", int(360 / branch), branch]
        self.operate_idx += 1
        self.build[f"Unite_{self.operate_idx}"] = metal
        self.operate_idx += 1

        metal_boundary = app.assign_perfect_e([f"metal_{self.metal_idx}"], name=f"metal_boundary_{self.metal_idx}")
        self.metal_idx += 1

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

    def SetSolution(self, freqs: list, angles: list = None):
        if angles is None:
            angles = []

        self.freqs = freqs
        self.angles = angles
        app = self.app

        for cnt, freq in enumerate(freqs):
            setup = app.create_setup(f"setup{cnt}", )
            setup.props["Frequency"] = f"{(freq[0]+freq[1])/2}GHz"
            setup.props["MaximumPasses"] = 12
            setup.props["MaxDeltaS"] = 0.03
            sweep = setup.create_frequency_sweep(
                name="LinearStepSweep", unit="GHz",
                start_frequency=freq[0] if cnt == 0 else freq[0] + 1e-3,
                stop_frequency=freq[1],
                num_of_freq_points=freq[2],
                save_fields=False
            )

        if angles is not None:
            for cnt, _ in enumerate(freqs):
                angle_sweep = None
                for angle in angles:
                    if angle_sweep is None:
                        angle_sweep = app.parametrics.add(
                            variable="angle",
                            start_point=angle[0],
                            end_point=angle[1],
                            step=angle[2],
                            name=f"AngleSweep{cnt}",
                            solution=f"setup{cnt}"
                        )
                    else:
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

    def SubstrateSet(self, subs: list):

        modeler = self.modeler
        unit = self.unit
        d = unit.size*2
        self.d = d
        bias = self.subH
        idx = 0

        for detail in subs:
            sub = modeler.create_box([f"-{d / 2}mm", f"-{d / 2}mm", f"{bias}mm"], [f"{d}mm", f"{d}mm", f"{detail.h}mm"],
                                     name=f"sub{idx}", material=f"{detail.material.name if type(detail.material) is Material else detail.material}")
            bias += detail.h
            idx += 1
            self.subs.append(detail)
        self.subH = bias

    def Simulate(self, NUM_CORES: int = 1):
        app = self.app
        app.analyze(cores=NUM_CORES)

    def SetReport(self):
        app = self.app
        variations = app.available_variations.nominal_values
        variations["angle"] = ["All"]
        expressions = ["dB(S(Floquet_Top:1,Floquet_Top:1))","dB(S(Floquet_Top:2,Floquet_Top:2))",
                       "dB(S(Floquet_Bottom:1,Floquet_Top:1))", "dB(S(Floquet_Bottom:2,Floquet_Top:2))",
                       "ang_deg(S(Floquet_Top:1,Floquet_Top:1))","ang_deg(S(Floquet_Top:2,Floquet_Top:2))",
                       "ang_deg(S(Floquet_Bottom:1,Floquet_Top:1))", "ang_deg(S(Floquet_Bottom:2,Floquet_Top:2))"]
        for idx, _ in enumerate(self.freqs):
            report = app.post.create_report(expressions=expressions, variations=variations, setup_sweep_name=f"setup{idx}")
            self.solutions.append(report.get_solution_data())

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
        data["unit"] = [self.unit.wire_width, self.unit.size]
        for detail in self.material:
            data["material"][detail.name] ={
                "permittivity": detail.permittivity,
                "permeability": detail.permeability,
                "dielectric_loss_tangent": detail.dielectric_loss_tangent
            }
        for detail in self.subs:
            sub_idx += 1
            data["sub"][f"sub{sub_idx}"] = {
                "material": detail.material.name if type(detail.material) is Material else detail.material,
                "h": detail.h,
            }
        data["range_freq"] = self.freqs
        data["range_angle"] = self.angles
        data["build"] = self.build

        with open(f"{file_path}/data.json", "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=4)

    def PNGandMaskGenerate(self, size: int = 500):
        d = self.d
        width = self.unit.wire_width

        safe_env = {
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "pow": pow,
            "abs": abs,
            "pi": math.pi,
        }

        def _eval_expr(expr, t):
            env = dict(safe_env)
            env["_t"] = float(t)
            return float(eval(expr, {"__builtins__": {}}, env))

        def _eval_curve(x_expr, y_expr, t):
            return [
                _eval_expr(x_expr, t),
                _eval_expr(y_expr, t),
            ]

        def _world_to_pixel(point):
            x, y = point
            px = x * size / d + size / 2
            py = size / 2 - y * size / d
            return (px, py)

        def _rec2pixel(point,angle,length,width):
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

        def _fun2pixel(x_up: str, y_up: str, x_down: str, y_down: str, points=120):

            up_points = [
                _eval_curve(x_up, y_up, t)
                for t in np.linspace(0, 1, points)
            ]

            down_points = [
                _eval_curve(x_down, y_down, t)
                for t in np.linspace(0, 1, points)
            ]

            polygon = up_points + down_points[::-1]
            polygon = [
                _world_to_pixel(p)
                for p in polygon
            ]

            return polygon

        def _group3_fun2pixel(fun_list, points=120):
            polygon = []

            for x_expr, y_expr in fun_list:
                segment = [
                    _eval_curve(x_expr, y_expr, t)
                    for t in np.linspace(0, 1, points)
                ]

                if polygon:
                    segment = segment[1:]

                polygon.extend(segment)

            return [_world_to_pixel(p) for p in polygon]

        def _draw_structure(data, structure_idx):
            if isinstance(data[0][0], str) and len(data[0]) == 2:
                pixel = _group3_fun2pixel(data)
                draw.polygon(pixel, fill=255)
            else:
                for item in data:
                    if type(item[0]) == str:
                        x_up = item[0]
                        y_up = item[1]
                        x_down = item[2]
                        y_down = item[3]
                        pixel = _fun2pixel(x_up, y_up, x_down, y_down)
                        draw.polygon(pixel, fill=255)
                    else:
                        begin = item[0]
                        r = math.sqrt(begin[0]**2+begin[1]**2)
                        theta = math.atan2(begin[1],begin[0])*180/math.pi
                        angle = item[1]
                        distance = item[2]
                        self.branch = 1 if self.branch == 0 else self.branch
                        for idx in range(self.branch):
                            x = r*math.cos((theta+int(360/self.branch)*idx)/180*math.pi)
                            y = r*math.sin((theta+int(360/self.branch)*idx)/180*math.pi)
                            xy = _rec2pixel([x, y], angle + int(360 / self.branch) * idx, distance, width)
                            draw.polygon(xy, fill=255)

            image.save(self.path + rf"\structure_{structure_idx}.png")
            img = Image.open(self.path + rf"\structure_{structure_idx}.png").convert("L")
            mask = (np.array(img) > 0).astype(np.uint8)
            np.savetxt(f"{self.path}/mask_{structure_idx}.csv", mask, delimiter=",", fmt="%d")

        idx = 0
        for data in self.data:
            image = Image.new("L", (size, size), 0)
            draw = ImageDraw.Draw(image)
            _draw_structure(data, idx)
            idx += 1

    def ResultsGenerate(self, passdB: float = -5):
        freq = []
        angle = []
        S11_te_real = []
        S11_tm_real = []
        S21_te_real = []
        S21_tm_real = []
        S11_te_angle = []
        S11_tm_angle = []
        S21_te_angle = []
        S21_tm_angle = []

        for solution in self.solutions:
            sweep_names = list(solution._sweeps_names)

            S11_te_real_data = np.asarray(solution._solutions_real["dB(S(Floquet_Top:1,Floquet_Top:1))"], dtype=float)
            S11_tm_real_data = np.asarray(solution._solutions_real["dB(S(Floquet_Top:2,Floquet_Top:2))"], dtype=float)
            S21_te_real_data = np.asarray(solution._solutions_real["dB(S(Floquet_Bottom:1,Floquet_Top:1))"], dtype=float)
            S21_tm_real_data = np.asarray(solution._solutions_real["dB(S(Floquet_Bottom:2,Floquet_Top:2))"], dtype=float)
            S11_te_real_angle_data = np.asarray(solution._solutions_real["ang_deg(S(Floquet_Top:1,Floquet_Top:1))"], dtype=float)
            S11_tm_real_angle_data = np.asarray(solution._solutions_real["ang_deg(S(Floquet_Top:2,Floquet_Top:2))"], dtype=float)
            S21_te_real_angle_data = np.asarray(solution._solutions_real["ang_deg(S(Floquet_Bottom:1,Floquet_Top:1))"], dtype=float)
            S21_tm_real_angle_data = np.asarray(solution._solutions_real["ang_deg(S(Floquet_Bottom:2,Floquet_Top:2))"], dtype=float)

            freq_idx = sweep_names.index("Freq")
            freq.append(S11_te_real_data[:, freq_idx])

            if "angle" in sweep_names:
                angle_idx = sweep_names.index("angle")
                angle.append(S11_te_real_data[:, angle_idx])
            else:
                angle.append(np.zeros_like(S11_te_real_data[:, freq_idx]))

            S11_te_real.append(S11_te_real_data[:, -1])
            S11_tm_real.append(S11_tm_real_data[:, -1])
            S21_te_real.append(S21_te_real_data[:, -1])
            S21_tm_real.append(S21_tm_real_data[:, -1])
            S11_te_angle.append(S11_te_real_angle_data[:, -1])
            S11_tm_angle.append(S11_tm_real_angle_data[:, -1])
            S21_te_angle.append(S21_te_real_angle_data[:, -1])
            S21_tm_angle.append(S21_tm_real_angle_data[:, -1])

        freq = np.concatenate(freq)
        angle = np.concatenate(angle)
        S11_te_real = np.concatenate(S11_te_real)
        S11_tm_real = np.concatenate(S11_tm_real)
        S21_te_real = np.concatenate(S21_te_real)
        S21_tm_real = np.concatenate(S21_tm_real)
        S11_te_angle = np.concatenate(S11_te_angle)
        S11_tm_angle = np.concatenate(S11_tm_angle)
        S21_te_angle = np.concatenate(S21_te_angle)
        S21_tm_angle = np.concatenate(S21_tm_angle)

        raw_data = np.column_stack(
            [angle, freq, S11_te_real, S11_tm_real, S21_te_real, S21_tm_real,
             S11_te_angle, S11_tm_angle, S21_te_angle,S21_tm_angle]
        )
        angles = np.unique(raw_data[:, 0])
        S11_te_label = np.where(S11_te_real > passdB, 1, -1)
        S11_tm_label = np.where(S11_tm_real > passdB, 1, -1)
        S21_te_label = np.where(S21_te_real > passdB, 1, -1)
        S21_tm_label = np.where(S21_tm_real > passdB, 1, -1)
        label_data = np.column_stack([angle, freq, S11_te_label, S11_tm_label, S21_te_label, S21_tm_label,
                                      S11_te_angle, S11_tm_angle, S21_te_angle,S21_tm_angle])

        np.savetxt(f"{self.path}/raw_result.csv", raw_data, delimiter=",", fmt="%f")
        np.savetxt(f"{self.path}/label_result.csv", label_data, delimiter=",", fmt="%f")

        def plot_one_band(freq_min: float, freq_max: float, save_path: str, data: np.ndarray, component:str, angle_tol:float = 1e-3):
            plt.figure(figsize=(10, 6))

            if component == "S11TE":
                plt.ylabel("dB")
                idx = 2
            elif component == "S11TM":
                plt.ylabel("dB")
                idx = 3
            elif component == "S21TE":
                plt.ylabel("dB")
                idx = 4
            elif component == "S21TM":
                plt.ylabel("dB")
                idx = 5
            elif component == "S11TE_angle":
                plt.ylabel("degree")
                idx = 6
            elif component == "S11TM_angle":
                plt.ylabel("degree")
                idx = 7
            elif component == "S21TE_angle":
                plt.ylabel("degree")
                idx = 8
            else:
                plt.ylabel("degree")
                idx = 9

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
                raw_y = data_sub[:, idx]

                plt.plot(freq, raw_y, linestyle="-", label=f"angle={angle:g}deg")

            plt.xlabel("Frequency (GHz)")
            plt.title(f"idx{self.idx} simulate {component} result")
            plt.grid(True)
            plt.legend()
            plt.tight_layout()
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()

        for detail in self.freqs:
            plot_one_band(detail[0], detail[1], self.path+f"/{detail[0]}~{detail[1]}Ghz_S11TE.png", raw_data, "S11TE")
            plot_one_band(detail[0], detail[1], self.path + f"/{detail[0]}~{detail[1]}Ghz_S11TM.png", raw_data, "S11TM")
            plot_one_band(detail[0], detail[1], self.path + f"/{detail[0]}~{detail[1]}Ghz_S21TE.png", raw_data, "S21TE")
            plot_one_band(detail[0], detail[1], self.path + f"/{detail[0]}~{detail[1]}Ghz_S21TM.png", raw_data, "S21TM")
            plot_one_band(detail[0], detail[1], self.path + f"/{detail[0]}~{detail[1]}Ghz_S11TE_angle.png", raw_data, "S11TE_angle")
            plot_one_band(detail[0], detail[1], self.path + f"/{detail[0]}~{detail[1]}Ghz_S11TM_angle.png", raw_data, "S11TM_angle")
            plot_one_band(detail[0], detail[1], self.path + f"/{detail[0]}~{detail[1]}Ghz_S21TE_angle.png", raw_data,
                          "S21TE_angle")
            plot_one_band(detail[0], detail[1], self.path + f"/{detail[0]}~{detail[1]}Ghz_S21TM_angle.png", raw_data,
                          "S21TM_angle")

        return label_data

    def RemoveDir(self):
        self.app.close_desktop()
        time.sleep(2)
        shutil.rmtree(self.path)