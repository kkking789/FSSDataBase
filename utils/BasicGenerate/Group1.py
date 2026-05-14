import math

import random
import utils


class CentralConnect:
    def __init__(self,unit: utils.Unit, config: utils.Config1):
        self.unit = unit
        self.config = config

        # 以中心为原点，共要几个分叉
        self.branch = None
        # 区域顶点
        self.points = []
        # 生成后各个矩阵的起始点，角度，长度
        self.structure = []
        # 区域内能放置的最大面积
        self.max_region = config.max_region
        # 正六边形的面积
        self.area = 6*math.sqrt(3)/4*(self.unit.size**2)

    def generate(self):
        self.structure = []
        if self.config.branch.switch:
            self.branch = random.choice([2,3,4])
        else:
            self.branch = self.config.branch.content
        self._points()
        begin = [0,0]
        bear = 0
        region = 0
        while True:
            if len(self.structure) == 0:
                wire, begin = self._first_wire(begin)
            else:
                wire, begin = self._wire(begin)
            if wire[2]!=0:
                bear = 0
                self.structure.append(wire)
                region += self.unit.wire_width*wire[2]
            else:
                bear+=1
                if bear == 5:
                    break
            if region*self.branch > self.max_region*self.area:
                break
        return self.structure

    def _first_wire(self, begin: list):
        if self.branch == 2:
            angle = random.randint(0,180)
        else:
            angle = random.randint(0,90)
        distance = 0.4*self.unit.size
        end_point = [begin[0]+distance*math.cos(angle/180*math.pi),begin[1]+distance*math.sin(angle/180*math.pi)]
        return [begin, angle, distance], end_point

    def _wire(self,begin: list):
        last_angle = self.structure[-1][1]
        angle = last_angle
        while abs(last_angle-angle)<=45:
            angle = random.randint(0,359)
        max_distance = self._judge(begin, angle)
        if max_distance == 1e8: max_distance = 0
        if max_distance <= 0.1*self.unit.size: max_distance=0
        distance = random.random() * max_distance
        end_point = [begin[0]+distance*math.cos(angle/180*math.pi),begin[1]+distance*math.sin(angle/180*math.pi)]
        return [begin, angle, distance], end_point

    def _points(self):
        branch = self.branch
        unit_size = self.unit.size
        s3 = math.sqrt(3)
        if branch == 2:
            self.points = [[-unit_size,0],
                      [unit_size,0],
                      [unit_size/2,unit_size/2*s3],
                      [-unit_size/2,unit_size/2*s3],
                      [-unit_size,0]]
        elif branch == 3:
            self.points = [[0,0],
                           [0, unit_size / 2 * s3],
                           [unit_size/2,unit_size/2*s3],
                           [unit_size, 0],
                           [unit_size/2*s3/2*s3,-unit_size/2*s3/2],
                           [0,0]]
        else:
            self.points = [[0,0],
                           [0,unit_size/2*s3],
                           [unit_size/2,unit_size/2*s3],
                           [unit_size,0],
                           [0,0]]

    def _judge(self,begin: list, angle: int):
        eps = 1e-6
        min_distance = 1e8
        for idx in range(len(self.points)-1):
            near_points = [self.points[idx],self.points[idx+1]]
            distance = _find_distance(begin,angle,near_points)
            if distance < min_distance:
                min_distance = distance
        for wire in self.structure:
            end_point = [wire[0][0]+wire[2]*math.cos(wire[1]/180*math.pi),
                         wire[0][1]+wire[2]*math.sin(wire[1]/180*math.pi)]
            if (abs(begin[0]-wire[0][0]) < eps and abs(begin[1]-wire[0][1]) < eps) or \
                    (abs(begin[0]-end_point[0]) < eps and abs(begin[1]-end_point[1]) < eps):
                continue
            near_points = [wire[0], end_point]
            distance = _find_distance(begin,angle,near_points)
            if distance < min_distance:
                min_distance = distance

        return min_distance


def _find_distance(inside: list, angle: int, points: list):
    eps = 1e-6
    edge = [points[1][0]-points[0][0], points[1][1]-points[0][1]]
    angle = angle % 360

    if angle == 90 or angle == 270:
        d = None
    else:
        d = math.tan(angle / 180 * math.pi)
    if edge[0] == 0:
        de = None
    else:
        de = edge[1] / edge[0]

    if de is None and d is None:
        return 1e8
    elif de is None:
        x = points[0][0]
        y = d * (x - inside[0]) + inside[1]
    elif d is None:
        x = inside[0]
        y = de * (x - points[0][0]) + points[0][1]
    else:
        if abs(de-d)<1e-3:
            return 1e8
        x = (-de * points[0][0] + points[0][1] - inside[1] + d * inside[0]) / (d - de)
        y = d * (x - inside[0]) + inside[1]

    dx = math.cos(angle / 180 * math.pi)
    dy = math.sin(angle / 180 * math.pi)
    if (x - inside[0]) * dx + (y - inside[1]) * dy < -eps:
        return 1e8

    distance = math.sqrt((inside[0] - x) ** 2 + (inside[1] - y) ** 2)
    if distance < eps:
        return 1e8
    if (min(points[0][0], points[1][0])-eps <= x <= max(points[0][0], points[1][0])+eps and
            min(points[0][1], points[1][1])-eps <= y <= max(points[0][1], points[1][1])+eps):
        return distance
    else:
        return 1e8







