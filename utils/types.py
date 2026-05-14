from dataclasses import dataclass

@dataclass
class Control:
    switch: bool
    content: int

@dataclass
class Unit:
    size: int
    wire_width: float
    layer_num: int

@dataclass
class Config1:
    max_region: float
    branch: Control

@dataclass
class Config2:
    bend: Control
    strategy: Control
    branch: Control

@dataclass
class Config3:
    bend: Control
    strategy: Control
    branch: Control