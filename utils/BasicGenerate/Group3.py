import utils.BasicGenerate.Group2 as Group2
import math
import utils


def _fmt(value: float):
    if abs(value) < 1e-8:
        value = 0.0
    return f"{value:.2f}"


class Solid:
    def __init__(self,unit: utils.Unit, config: utils.Config3):
        self.unit = unit
        self.config = config

        config2 = utils.Config2(bend=config.bend,strategy=config.strategy,branch=config.branch)
        self.circular = Group2.Circular(self.unit, config2)

        self.circular_structure = []
        self.structure = []
        self.strategy = None

    def generate(self):
        self.circular_structure, self.strategy = self.circular.generate()
        if self.strategy==1:
            self.structure = self.circular.center_fun
        else:
            self.structure = [[f"{_fmt(data[0][0])}+{_fmt(data[2])}*t*cos({_fmt(data[1]/180*math.pi)})",
                               f"{_fmt(data[0][1])}+{_fmt(data[2])}*t*sin({_fmt(data[1]/180*math.pi)})"]
                              for data in self.circular_structure]
        return self.structure
