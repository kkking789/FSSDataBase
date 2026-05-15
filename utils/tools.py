from ansys.aedt.core import Hfss
from BasicGenerate import *
from ansys.aedt.core.generic.constants import Axis
from utils import *

def DrawGroup1(app: Hfss, data: list, unit: Unit, Zbias: float = 0):
    modeler = app.modeler
    idx = 0
    rect_list = []
    width = unit.wire_width

    for item in data:
        begin = item[0]
        angle = item[1]
        distance = item[2]
        pivot = [f"{begin[0]}mm",f"{begin[1]}mm",f"{Zbias}mm"]
        cs = modeler.create_coordinate_system(
            origin=pivot,
            reference_cs="Global",
            name="RotatePivotCS",
            mode="axis",
            x_pointing=[1, 0, 0],
            y_pointing=[0, 1, 0],
        )
        old_cs = modeler.get_working_coordinate_system()
        modeler.set_working_coordinate_system("RotatePivotCS")
        if idx == 0:
            rect_name = "metal"
        else:
            rect_name = f"Rec{idx}"
        rect = modeler.create_rectangle("XY", origin=[0,f"-{width/2}mm",0],sizes=[f"{distance}mm",f"{width}mm"],name=rect_name)
        rect_list.append(rect)
        modeler.rotate(
            assignment=rect_name,
            axis=Axis.Z,
            angle=angle,
            units="deg"
        )
        modeler.set_working_coordinate_system(old_cs)
        idx += 1

    modeler.unite(rect_list)

def RotateBranch(app: Hfss, branch: int):
    modeler = app.modeler
    metal_ = modeler.duplicate_around_axis("metal", Axis.Z, angle=int(360/branch), clones=branch)
    metal = [metal_[0]]
    for idx in range(branch):
        metal.append(metal_[0][idx-1])
    modeler.unite(metal)

def BoundarySet(app: Hfss, unit: Unit):
    modeler = app.modeler
    app["angle"] = "0deg"
    h = unit.subH*unit.layer_num
    d = unit.size*2
    f = 1e9 # 激励高度选择的参考频率为1Ghz
    extraH = int(3e8/f/4*1000)
    airbox = modeler.create_box([f"{-d/2}mm", f"{-d/2}mm", f"-{h+extraH/2}mm"],
                                    [f"{d}mm", f"{d}mm", f"{h*2+extraH}"], name="air_box", material="air")

    top_sheet = app.create_rectangle("XY", origin=[f"{-d/2}mm", f"{-d/2}mm", f"{h+extraH/2}mm"],
                                            sizes=[f"{d}mm", f"{d}mm"],
                                            name="TopSheet", material="Vacuum")
    floquet_top = app.create_floquet_port(
        assignment=top_sheet.name,
        deembed_distance=extraH,
        modes=2,
        name="Floquet_Top"
    )
    bottom_sheet = modeler.create_rectangle("XY",
                                               origin=[f"{-d/2}mm", f"{-d/2}mm", f"-{h+extraH/2}mm"],
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
        origin=[f"{-d/2}mm", f"{-d/2}mm", f"-{h+extraH/2}mm"],
        sizes=[f"{h*2+extraH}mm", f"{d}mm"],
        name="Primary1_Sheet",
        material="Vacuum"
    )
    primary1 = app.assign_primary(
        assignment=primary1_sheet.id,
        u_start=[f"{d/2}mm", f"-{d/2}mm", f"{h+extraH/2}mm"],
        u_end=[f"-{d/2}mm", f"-{d/2}mm", f"{h+extraH/2}mm"],
        name="Primary1"
    )

    slave1_sheet = modeler.create_rectangle(
        "XZ",
        origin=[f"{-d/2}mm", f"{d/2}mm", f"-{h+extraH/2}mm"],
        sizes=[f"{h*2+extraH}", f"{d}mm"],
        name="Slave1_Sheet",
        material="Vacuum"
    )

    slave1 = app.assign_secondary(
        assignment=slave1_sheet.id,
        primary=primary1.name,
        u_start=[f"{d/2}mm", f"{d/2}mm", f"{h+extraH/2}mm"],
        u_end=[f"{-d/2}mm", f"{d/2}mm", f"{h+extraH/2}mm"],
        phase_delay_param2="angle",
        name="Slave1"
    )

    primary2_sheet = modeler.create_rectangle(
        "YZ",
        origin=[f"{-d/2}mm", f"{-d/2}mm", f"-{h+extraH/2}mm"],
        sizes=[f"{d}mm", f"{h*2+extraH}mm"],
        name="Primary2_Sheet",
        material="Vacuum"
    )
    primary2 = app.assign_primary(
        assignment=primary2_sheet.id,
        u_start=[f"-{d / 2}mm", f"{d / 2}mm", f"{h+extraH/2}mm"],
        u_end=[f"-{d / 2}mm", f"-{d / 2}mm", f"{h+extraH/2}mm"],
        name="Primary2",
        reverse_v=True
    )

    slave2_sheet = modeler.create_rectangle(
        "YZ",
        origin=[f"{d / 2}mm", f"-{d / 2}mm", f"-{h+extraH/2}mm"],
        sizes=[f"{d}mm", f"{h*2+extraH}mm"],
        name="Slave2_Sheet",
        material="Vacuum"
    )

    slave2 = app.assign_secondary(
        assignment=slave2_sheet.id,
        primary=primary2.name,
        u_start=[f"{d / 2}mm", f"{d / 2}mm", f"{h+extraH/2}mm"],
        u_end=[f"{d / 2}mm", f"-{d / 2}mm", f"{h+extraH/2}mm"],
        name="Slave2",
        phase_delay_param2="angle",
        reverse_v=True
    )



def SetSolution(app: Hfss, freqs: list, points: int = 50, angles: list = None):
    setup = app.create_setup("Setup1")
    sweep = None
    for freq in freqs:
        if sweep is None:
            sweep = setup.create_frequency_sweep(
                name="LinearStepSweep", unit="GHz", start_frequency=freq[0], stop_frequency=freq[1], num_of_freq_points=points,
                save_fields=False
            )
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



