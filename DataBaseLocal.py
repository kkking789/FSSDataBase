import os
import random
import tempfile
import time

from pathlib import Path

from utils.BasicGenerate import CentralConnect
import utils
from ansys.aedt.core import Hfss

import yaml

def load_settings(path="settings.yaml"):
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def _random_pick(data: int|list|float, _type: type = int) -> float|int:
    if type(data) == list:
        if _type == int:
            return random.randint(data[0], data[1])
        else:
            return random.uniform(data[0], data[1])
    else:
        return data

def _list_random_pick(data: str|list) -> str:
    if type(data) == list:
        return random.choice(data)
    else:
        return data

def generate_once(settings_stackup, opt: utils.Operation,cache: utils.CacheOperate, unit: utils.Unit,
                  config1 : utils.Config1, config2 : utils.Config2, config3 : utils.Config3,
                  frequency: list, angle: list, app: Hfss, NUM_CORES: int = 1):
    stackup = []
    flag = False
    if settings_stackup["mode"] == "arrangement":
        arrangement = settings_stackup["arrangement"]
        for detail in reversed(arrangement):
            if detail["type"] == "metal":
                stackup.append([detail["type"], _list_random_pick(detail["group"])])
            else:
                dielectric_layer = utils.Substrate(material=_list_random_pick(detail["material"]),
                                                   h = _random_pick(detail["h"], float))
                stackup.append([detail["type"],dielectric_layer])
    else:
        _random = settings_stackup["random"]
        dielectric_layers = _random_pick(_random["dielectric_layers"])
        metal_layers = _random_pick(_random["metal_layers"])
        current_metal = 0
        current_dielectric = 0
        if metal_layers > metal_layers-1:
            metal_layers = metal_layers - 1
        for idx in range(dielectric_layers+2):
            if idx%2 == 1:
                dielectric_layer = utils.Substrate(_list_random_pick(_random["dielectric_candidates"]), _random_pick(_random["dielectric_h"], float))
                stackup.append(["dielectric", dielectric_layer])
                current_dielectric += 1
            else:
                if (metal_layers - current_metal+1) == (dielectric_layers - current_dielectric):
                    stackup.append(["metal", _list_random_pick(_random["metal_candidates"])])
                elif random.random() > 0.5:
                    stackup.append(["metal", _list_random_pick(_random["metal_candidates"])])
                else:
                    continue
                current_metal += 1

    h = 0
    for detail in stackup:
        if detail[0] == "dielectric":
            opt.SubstrateSet([detail[1]])
            h += detail[1].h
        elif detail[0] == "metal":
            if detail[1] == "group1":
                generator = utils.BasicGenerate.CentralConnect(unit, config1)
                data = generator.generate()
                flag = opt.DrawGroup1(data, h)
                opt.RotateBranch(generator.branch)
            elif detail[1] == "group2":
                generator = utils.BasicGenerate.Circular(unit, config2)
                data = generator.generate()
                flag = opt.DrawGroup2(data, h)
            else:
                generator = utils.BasicGenerate.Solid(unit, config3)
                data = generator.generate()
                flag = opt.DrawGroup3(data, h)
    if flag:
        opt.BoundarySet()
        opt.SetSolution(frequency, angle)
        opt.Simulate(NUM_CORES)
        opt.SetReport()
        opt.JsonGenerate(author="kxk")
        opt.PNGandMaskGenerate()
        label_data = opt.ResultsGenerate()
        split = utils.ResultSplit(label_data, frequency)
        for freq, angle,S11, S21 in split:
            cache.write(opt.idx, 0, angle, S11, freq)
            cache.write(opt.idx, 1, angle, S21, freq)
        app.close_project()
    else:
        print("The generate structure is illegal.")
        opt.RemoveDir()

def main():
    print("loading settings ...")
    settings = load_settings()

    AEDT_VERSION = settings["AEDT_VERSION"]
    NUM_CORES = settings["NUM_CORES"]
    path = settings["path"]
    samples = settings["samples"]

    settings_unit = settings["unit"]
    unit = utils.Unit(settings_unit["size"],
                        _random_pick(settings_unit["wire_width"], float))

    settings_material = settings["materials"]
    materials = []
    for key in settings_material.keys():
        materials.append(utils.Material(key, settings_material[key]["permittivity"],
                                        settings_material[key]["permeability"],
                                        settings_material[key]["dielectric_loss_tangent"]))

    settings_generate = settings["generators"]
    settings_group1 = settings_generate["group1"]
    config1 = utils.Config1(_random_pick(settings_group1["max_region"], float),
                            utils.Control(settings_group1["branch"]["switch"], settings_group1["branch"]["content"]))
    settings_group2 = settings_generate["group2"]
    config2 = utils.Config2(utils.Control(settings_group2["bend"]["switch"],settings_group2["bend"]["content"]),
                            utils.Control(settings_group2["strategy"]["switch"],settings_group2["strategy"]["content"]),
                            utils.Control(settings_group2["strategy"]["switch"],settings_group2["branch"]["content"]))
    settings_group3 = settings_generate["group3"]
    config3 = utils.Config3(utils.Control(settings_group3["bend"]["switch"],settings_group3["bend"]["content"]),
                            utils.Control(settings_group3["strategy"]["switch"],settings_group3["strategy"]["content"]),
                            utils.Control(settings_group3["strategy"]["switch"],settings_group3["branch"]["content"]))

    settings_frequency = settings["frequency"]
    frequency = []
    for detail in settings_frequency:
        frequency.append(detail)
    settings_angle = settings["angle"]
    angle = []
    if settings_angle["enabled"]:
        for detail in settings_angle["detail"]:
            angle.append(detail)

    settings_stackup = settings["stackup"]

    print("done")

    temp_folder = tempfile.TemporaryDirectory(suffix=".ansys")
    cache = utils.CacheOperate(path, batch_size=100)

    for idx in range(samples):
        app = Hfss(
            project=os.path.join(temp_folder.name, f"FSS_DataBase"),
            design=f"FSS_DataBase_Design_{idx}",
            version=AEDT_VERSION,
            non_graphical=False,
            new_desktop=False,
        )
        operation = utils.Operation(app, path, unit)
        operation.SetMaterial(materials)
        try:
            generate_once(settings_stackup, operation,cache,unit,config1,config2,config3, frequency, angle, app, NUM_CORES)
        except:
            operation.RemoveDir()


if __name__ == "__main__":
    main()



