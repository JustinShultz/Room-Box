import pathlib
from uuid import uuid4

import streamlit as st
import honeybee
import ladybug
from honeybee.room import Room
from honeybee.model import Model, Face
from honeybee_radiance.properties.model import ModelRadianceProperties
from honeybee_vtk.model import DisplayMode
from honeybee_vtk.model import Model as VTKModel
from honeybee_vtk.vtkjs.schema import SensorGridOptions
from honeybee_radiance.sensorgrid import SensorGrid
from visualize_model import generate_vtk_model
from streamlit_vtkjs import st_vtkjs

from ladybug.epw import EPW


col1, col2, col3= st.columns([1,2,1])

col2_con = col2.container()


col1.header('ROOMBOX')

col1.subheader('Room Geometry')
room_width = col1.slider('Room Width', value=30, min_value=5, max_value=5)
room_depth = col1.slider('Room Depth', value=30, min_value=5, max_value=5)
room_height = col1.slider('Room Height', value=15, min_value=10, max_value=30)

col1.subheader('Glazing')
wwr = col1.slider("WWR", max_value=95, min_value=10, step=5)/100
vlt = col1.slider("VLT", max_value=90, min_value=10, step=5)/100
shgc = col1.slider("SHGC", max_value=90, min_value=10, step=5)/100

def create_room(width, depth, height):
    room = Room.from_box('room',width,depth,height)

    return room

room = Room.from_box(
    identifier=str(uuid4()),
    width=room_width,
    depth=room_depth,
    height=room_height)

grid = SensorGrid.from_mesh3d(str(uuid4()), room.generate_grid(x_dim=2))
faces: Face = room.faces[1]
faces.apertures_by_ratio(wwr)
st.write(faces)


simple_model = Model.from_objects(f'model_{room_width}_{room_depth}_{room_height}_{wwr}',[room],units='Feet')

simple_model._properties._radiance = ModelRadianceProperties(simple_model, [grid])

model_path = simple_model.to_hbjson(name=simple_model.identifier, folder='data')
vtk_path = pathlib.Path('data', f'{simple_model.identifier}.vtkjs')

# if not vtk_path.is_file():
VTKModel.from_hbjson(model_path, SensorGridOptions.Sensors).to_vtkjs(
    folder='data', name=simple_model.identifier)

with col2_con:
    st_vtkjs(
        content=vtk_path.read_bytes(),
        key=simple_model.identifier, subscribe=False
    )


st.write(room)

col3.subheader('Analysis Models')


st.checkbox("Select Faces", room.faces)

st.text_input("EPW Url")