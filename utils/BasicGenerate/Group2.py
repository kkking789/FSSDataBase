import math
import random
import utils


def _fmt(value: float):
    if abs(value) < 1e-8:
        value = 0.0
    return f"{value:.2f}"


def _same_point(point1: list, point2: list):
    eps = 1e-8
    return abs(point1[0]-point2[0]) < eps and abs(point1[1]-point2[1]) < eps


class Circular:
    def __init__(self,unit: utils.Unit, config: utils.Config2):
        self.unit = unit
        self.config = config

        # 环形线生成策略
        self.strategy = None
        # 以中心为原点，共要几个分叉
        self.branch = None
        # 曲线的连接点
        self.points = []
        # 需要的弯折点
        self.bend = None
        # 直线生成策略下的金属线
        self.wire = []
        # 曲线生成策略下的金属线函数
        self.fun = []
        # 曲线生成策略下的中心线函数
        self.center_fun = []

    def generate(self):
        self.points = []
        self.wire = []
        self.fun = []
        self.center_fun = []

        if self.config.strategy.switch:
            self.strategy = random.choice([0,1])
        else:
            self.strategy = self.config.strategy.content

        if self.config.branch.switch:
            self.branch = random.choice([2,3,4])
        else:
            self.branch = self.config.branch.content

        if self.config.bend.switch:
            self.bend = random.choice([1,2,3])
        else:
            self.bend = self.config.bend.content

        self._points()
        self._pick()
        self.points = self._full_points()

        if self.strategy == 0:
            # 直线生成策略
            for idx in range(len(self.points)-1):
                start_point = self.points[idx]
                end_point = self.points[idx+1]
                angle = math.atan2(end_point[1]-start_point[1],end_point[0]-start_point[0])*180/math.pi
                distance = math.sqrt((start_point[0]-end_point[0])**2 + (start_point[1]-end_point[1])**2)
                self.wire.append([start_point,angle,distance])
            return self.wire, self.strategy
        else:
            # 曲线生成策略
            w = self.unit.wire_width
            self._catmull_rom(w)
            return self.fun, self.strategy

    def _full_points(self):
        points = self.points.copy()
        all_points = []
        for idx in range(self.branch):
            angle = 2*math.pi/self.branch*idx
            for point_idx in range(len(points)):
                if idx != 0 and point_idx == 0:
                    continue
                point = points[point_idx]
                x = point[0]*math.cos(angle)-point[1]*math.sin(angle)
                y = point[0]*math.sin(angle)+point[1]*math.cos(angle)
                now_point = [x,y]
                if len(all_points) != 0 and _same_point(now_point, all_points[-1]):
                    continue
                if len(all_points) != 0 and _same_point(now_point, all_points[0]):
                    continue
                all_points.append(now_point)
        all_points.append(all_points[0])
        return all_points

    def _pick(self):
        unit_size = self.unit.size
        s3 = math.sqrt(3)
        if self.bend ==1:
            num = random.random()
            if self.branch == 2:
                point = [0,num*unit_size/2*s3]
            elif self.branch == 3:
                point = [num*unit_size/2*s3/2*s3,num*unit_size/2*s3/2]
            else:
                point = [num*unit_size/2,num*unit_size/2*s3]
            self.points.insert(1, point)
        elif self.bend == 2:
            if self.branch == 2:
                point1 = _random_pick([[0,0],[0,unit_size/2*s3],[-unit_size/2,unit_size/2*s3]])
                point2 = _random_pick([[0, 0], [0, unit_size / 2 * s3], [unit_size / 2, unit_size / 2 * s3]])
            elif self.branch == 3:
                point1 = _random_pick([[0,0],[unit_size/2,unit_size/2*s3],[unit_size/2*s3/2*s3,unit_size/2*s3/2]])
                point2 = _random_pick([[0,0],[unit_size,0],[unit_size/2*s3/2*s3,unit_size/2*s3/2]])
            else:
                point1 = _random_pick([[0,0],[0,unit_size/2*s3],[unit_size/2,unit_size/2*s3]])
                point2 = _random_pick([[0,0],[unit_size/2,unit_size/2*s3],[unit_size/2*s3/2*s3,unit_size/2*s3/2]])
            self.points.insert(1, point1)
            self.points.insert(1, point2)
        else:
            if self.branch == 2:
                point1 = _random_pick([[0,0],[-unit_size,0],[-unit_size/2,unit_size/2*s3]])
                point2 = _random_pick([[0,0],[-unit_size/2,unit_size/2*s3],[unit_size/2,unit_size/2*s3]])
                point3 = _random_pick([[0,0],[unit_size,0],[unit_size/2,unit_size/2*s3]])
            elif self.branch == 3:
                point1 = _random_pick([[0,0],[0,unit_size/2*s3],[unit_size/2,unit_size/2*s3]])
                point2 = _random_pick([[0,0],[unit_size/2,unit_size/2*s3],[unit_size,0]])
                point3 = _random_pick([[0,0],[unit_size,0],[unit_size/2*s3/2*s3,-unit_size/2*s3/2]])
            else:
                point1 = _random_pick([[0,0],[0,unit_size/2*s3],[unit_size/2,unit_size/2*s3]])
                point2 = _random_pick([[0,0],[unit_size/2,unit_size/2*s3],[unit_size/2*s3/2*s3,unit_size/2*s3/2]])
                point3 = _random_pick([[0,0],[unit_size/2*s3/2*s3,unit_size/2*s3/2],[unit_size,0]])
            self.points.insert(1, point1)
            self.points.insert(1, point2)
            self.points.insert(1, point3)

    def _catmull_rom(self, w: float):
        # catmull_rom 曲线插值算法
        points = self.points[:-1].copy()
        x_fun = []
        y_fun = []
        dx_fun = []
        dy_fun = []
        for idx in range(len(points)):
            P0 = points[idx-1]
            P1 = points[idx]
            P2 = points[(idx+1)%len(points)]
            P3 = points[(idx+2)%len(points)]

            x0, y0 = _fmt(P0[0]), _fmt(P0[1])
            x1, y1 = _fmt(P1[0]), _fmt(P1[1])
            x2, y2 = _fmt(P2[0]), _fmt(P2[1])
            x3, y3 = _fmt(P3[0]), _fmt(P3[1])
            t0 = _fmt(idx)
            t1 = _fmt(idx+1)

            xt = f"0.5*(2*{x1}+(-{x0}+{x2})*(t-{t0})+(2*{x0}-5*{x1}+4*{x2}-{x3})*(t-{t0})^2+(-{x0}+3*{x1}-3*{x2}+{x3})*(t-{t0})^3)"
            yt = f"0.5*(2*{y1}+(-{y0}+{y2})*(t-{t0})+(2*{y0}-5*{y1}+4*{y2}-{y3})*(t-{t0})^2+(-{y0}+3*{y1}-3*{y2}+{y3})*(t-{t0})^3)"
            dx = f"0.5*((-{x0}+{x2})+2*(2*{x0}-5*{x1}+4*{x2}-{x3})*(t-{t0})+3*(-{x0}+3*{x1}-3*{x2}+{x3})*(t-{t0})^2)"
            dy = f"0.5*((-{y0}+{y2})+2*(2*{y0}-5*{y1}+4*{y2}-{y3})*(t-{t0})+3*(-{y0}+3*{y1}-3*{y2}+{y3})*(t-{t0})^2)"

            if idx == len(points)-1:
                condition = f"((t>={t0})*(t<={t1}))"
            else:
                condition = f"((t>={t0})*(t<{t1}))"
            x_fun.append(f"{condition}*({xt})")
            y_fun.append(f"{condition}*({yt})")
            dx_fun.append(f"{condition}*({dx})")
            dy_fun.append(f"{condition}*({dy})")
        xt = "+".join(x_fun)
        yt = "+".join(y_fun)
        dx = "+".join(dx_fun)
        dy = "+".join(dy_fun)
        self.center_fun = [xt, yt]

        x_up = f"({xt})-{_fmt(w/2)}*({dy})/sqrt(({dx})^2+({dy})^2)"
        y_up = f"({yt})+{_fmt(w/2)}*({dx})/sqrt(({dx})^2+({dy})^2)"
        x_down = f"({xt})+{_fmt(w/2)}*({dy})/sqrt(({dx})^2+({dy})^2)"
        y_down = f"({yt})-{_fmt(w/2)}*({dx})/sqrt(({dx})^2+({dy})^2)"
        self.fun = [x_up, y_up, x_down, y_down]

    def _points(self):
        unit_size = self.unit.size
        s3 = math.sqrt(3)
        if self.branch == 2:
            self.points.append([unit_size/2,0])
            self.points.append([-unit_size/2,0])
        elif self.branch == 3:
            self.points.append([unit_size/2*s3/2/2*s3,-unit_size/2*s3/2/2])
            self.points.append([0, unit_size/2*s3/2])
        else:
            self.points.append([unit_size/2,0])
            self.points.append([0,unit_size/2])

# 三角形内随机选点
def _random_pick(points: list):
    r1 = random.random()
    r2 = random.random()

    u = math.sqrt(r1)
    v = r2
    A = points[0]
    B = points[1]
    C = points[2]

    x = (1 - u) * A[0] + u * (1 - v) * B[0] + u * v * C[0]
    y = (1 - u) * A[1] + u * (1 - v) * B[1] + u * v * C[1]

    return [x, y]
