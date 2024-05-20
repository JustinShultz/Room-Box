import streamlit as st
from room_geometry import create_room
from visualize_model import generate_vtk_model
from honeybee.model import Model
import pathlib
from streamlit_vtkjs import st_vtkjs
from honeybee_vtk.model import DisplayMode
from honeybee_vtk.model import Model as VTKModel
from honeybee_vtk.vtkjs.schema import SensorGridOptions

if 'vtk_path' not in st.session_state:
    st.session_state.vtk_path = None
if 'target_folder' not in st.session_state:
    st.session_state.target_folder = None


st.header('ROOMBOX')

col1, col2 = st.columns([1,2])

col2_con = col2.container()


col1.subheader('Room Geometry')
room_width = col1.slider('Room Width', value=30)
room_length = col1.slider('Room Length', value=30)
room_height = col1.slider('Room Height', value=15)

room = create_room(room_width,room_length,room_height)

simple_model = Model.from_objects('model1',[room])

model_path = simple_model.to_hbjson(name=simple_model.identifier, folder='data')
vtk_path = pathlib.Path('data', f'{simple_model.identifier}.vtkjs')

if not vtk_path.is_file():
    VTKModel.from_hbjson(model_path, SensorGridOptions.Sensors).to_vtkjs(
        folder='data', name=simple_model.identifier)

with col2_con:
    st_vtkjs(
        content=vtk_path.read_bytes(),
        key=simple_model.identifier, subscribe=False
    )


st.write(room)
st.write(room.faces)

st.checkbox("Select Faces", room.faces)

col2.subheader('Viewer here')
generate_vtk_model(simple_model,col2_con)

st.text_input("EPW Url") 