import utils.BasicGenerate.Group2 as Group2
import math
import utils


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
        self.circular_structure = self.circular.generate()
        self.strategy = self.circular.strategy
        if self.strategy==1:
            self.structure = self.circular.center_fun
        else:
            self.structure = [[f"{data[0][0]}+{data[2]}*_t*cos({data[1]/180*math.pi})",
                               f"{data[0][1]}+{data[2]}*_t*sin({data[1]/180*math.pi})"]
                              for data in self.circular_structure]
        return self.structure
