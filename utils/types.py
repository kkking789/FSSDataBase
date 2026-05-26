from dataclasses import dataclass

@dataclass
class Control:
    switch: bool
    content: int

@dataclass
class Unit:
    size: int
    wire_width: float

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

@dataclass
class Material:
    name: str
    permittivity: float
    permeability: float
    dielectric_loss_tangent: float

@dataclass
class Substrate:
    material: Material | str
    h: float