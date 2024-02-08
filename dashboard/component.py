import os
import streamlit.components.v1 as components
from typing import List, Dict, Any
import numpy as np

_RELEASE = True

if not _RELEASE:
    _component_func = components.declare_component(
        "map_component",
        url="http://localhost:3001",
    )
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "map_component/frontend/build")
    _component_func = components.declare_component("map_component", path=build_dir)

GeoJSON = Dict[str, Any]
np2darray = np.ndarray
def map_component(risks: Dict[str, GeoJSON],
                  grid: GeoJSON,
                  zipcodes: GeoJSON,
                  service_areas: GeoJSON,
                  icons: Dict[str, GeoJSON],
                  map_bg: np2darray,
                  key=None):
    component_value = _component_func(risks=risks,
                                      grid=grid,
                                      zipcodes=zipcodes,
                                      service_areas=service_areas,
                                      icons=icons,
                                      map_bg=map_bg,
                                      key=key,
                                      default={'id':'','name':'','type':''})

    return component_value
