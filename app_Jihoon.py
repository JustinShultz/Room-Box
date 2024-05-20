import pathlib
from uuid import uuid4

import streamlit as st
import honeybee
import ladybug
from ladybug.epw import EPW
from ladybug.wea import Wea
from honeybee.room import Room
from honeybee.model import Model, Face
from honeybee_radiance.properties.model import ModelRadianceProperties
from honeybee_vtk.model import DisplayMode
from honeybee_vtk.model import Model as VTKModel
from honeybee_vtk.vtkjs.schema import SensorGridOptions
from honeybee_radiance.sensorgrid import SensorGrid
from visualize_model import generate_vtk_model
from streamlit_vtkjs import st_vtkjs
# from pollination_io.api.client import ApiClient
# from pollination_io.interactors import Job, NewJob, Recipe
# from queenbee.job.job import JobStatusEnum
from streamlit_autorefresh import st_autorefresh

# For adding construction set / HVAC properties
from honeybee_energy.lib.constructionsets import generic_construction_set
from honeybee_energy.hvac.idealair import IdealAirSystem

api_key = st.sidebar.text_input(
    'Enter Pollination APIKEY', type='password', value='8B8AC8B0.13F7476390ECDE0F50F7ED05',
    help=':bulb: You only need an API Key to access private projects. '
    'If you do not have a key already go to the settings tab under your profile to '
    'generate one.'
) or None

owner = st.sidebar.text_input('Project Owner', value="justinshultz")
project = st.sidebar.text_input('Project Name', value="hacksimbuild-2024")

run_simulation = st.sidebar.button('Run Simulation')
# api_client = ApiClient(api_token=api_key)


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



# Create a construction set
construction_set = generic_construction_set

# Assign the construction set to the room
room.properties.construction_set = construction_set

# Define an Ideal Air System (simple example, replace with actual HVAC system as needed)
hvac_system = IdealAirSystem("HVAC")

# Assign the HVAC system to the room
room.properties.hvac = hvac_system

grid = SensorGrid.from_mesh3d(str(uuid4()), room.generate_grid(x_dim=2, offset=2.5))
faces: Face = room.faces[1]
faces.apertures_by_ratio(wwr)
st.write(faces)


simple_model = Model.from_objects(f'model_{room_width}_{room_depth}_{room_height}_{wwr}',[room],units='Meters')

simple_model._properties._radiance = ModelRadianceProperties(simple_model, [grid])

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

col3.subheader('Analysis Models')

st.checkbox("Select Faces", room.faces)

# epw_data = st.file_uploader("EPW File", type=['epw'], key='epw_data')
# if epw_data:
#     epw_file = pathlib.Path(f'./data/{epw_data.name}')
#     st.write(epw_file)
#     epw_file.parent.mkdir(parents=True, exist_ok=True)
#     epw_file.write_bytes(epw_data.read())
# epw_obj = EPW(epw_file)
# wea_obj = Wea.from_epw_file(epw_file)
# wea_file = wea_obj.write(f'./data/weather_file.wea')
# st.write(wea_file)
# .to_wea(file_path=epw_file)

# if run_simulation:
#     job_id = None

#     recipe = Recipe('ladybug-tools', 'annual-daylight',
#                     'latest', api_client)
#     new_job = NewJob(owner, project, recipe, client=api_client)
#     model_project_path = new_job.upload_artifact(
#         pathlib.Path(model_path), 'streamlit-job')
#     wea_project_path = new_job.upload_artifact(
#         pathlib.Path(wea_file), 'streamlit-job'
#     )
#     new_job.arguments = [
#         {'model': model_project_path,
#          'wea': wea_project_path,
#          'width': room_width, 
#          'depth': room_depth, 
#          'height': room_height,
#          'glazing-ration': wwr, 
#          'VLT': vlt, 
#          'SHGC': shgc}
#     ]
#     job = new_job.create()

#     job_id = job.id

#     if job_id is not None and owner is not None and project is not None:

#         job = Job(owner, project, job_id, client=api_client)

#         st.write(
#             f'Checkout your job [here](https://app.pollination.cloud/{owner}/projects/{project}/jobs/{job_id})')

#         if job.status.status in [
#                 JobStatusEnum.pre_processing,
#                 JobStatusEnum.running,
#                 JobStatusEnum.created,
#                 JobStatusEnum.unknown]:
#             with st.spinner(text="Simulation in Progres..."):
#                 st.warning(f'Simulation is {job.status.status.value}...')
#                 st_autorefresh(interval=2000, limit=100)

#         elif job.status.status in [JobStatusEnum.failed, JobStatusEnum.cancelled]:
#             st.warning(f'Simulation is {job.status.status.value}')
#         else:
#             job.runs_dataframe.parameters
#             # res_model_path = view_results(
#             #     query.owner, query.project, query.job_id, api_key)
#             # st_vtkjs(
#             #     content=pathlib.Path(res_model_path).read_bytes(), key='results',
#             #     subscribe=False
#             # )



# Jihoon
from inputs import initialize
from simulation import run_energy_simulation
from outputs import display_results
from pathlib import Path

# Run simulation
# initialize the app and load up all of the inputs
initialize()

epw_data = st.file_uploader("EPW File", type=['epw'], key='epw_data')
if epw_data:
    epw_file = pathlib.Path(f'./data/{epw_data.name}')
    st.write(epw_file)
    epw_file.parent.mkdir(parents=True, exist_ok=True)
    epw_file.write_bytes(epw_data.read())

# if epw_file:
    # save EPW in data folder
    # epw_path = Path(f'./data/{epw_filename}')
    # epw_path.parent.mkdir(parents=True, exist_ok=True)
    # epw_path.write_bytes(epw_path.read())
    # create a DDY file from the EPW
    ddy_file = epw_file.as_posix().replace('.epw', '.ddy')
    epw_obj = EPW(epw_file.as_posix())
    epw_obj.to_ddy(ddy_file)
    ddy_path = Path(ddy_file)
    # set the session state variables
    st.session_state.epw_path = epw_file
    st.session_state.ddy_path = ddy_path

    # epw_filename = 'boston'
    # epw_file = f'./data/{epw_filename}.epw'
    # #epw_obj = EPW(epw_file)
    wea_obj = Wea.from_epw_file(epw_file)
    wea_file = wea_obj.write(f'./data/weather_file.wea')
    st.write(wea_file)
else:
    st.session_state.epw_path = None
    st.session_state.ddy_path = None



# Jihoon: Can we visualize the direction of geometry on the viewer?
room_orient = col1.slider(label='North', min_value=0, max_value=360, value=0)
if room_orient != st.session_state.north:
    st.session_state.north = room_orient
    st.session_state.sql_results = None  # reset to have results recomputed

# get the inputs that only affect the display and do not require re-simulation
in_heat_cop = col1.number_input(
    label='Heating COP', min_value=0.0, max_value=6.0, value=1.0, step=0.05)
if in_heat_cop != st.session_state.heat_cop:
    st.session_state.heat_cop = in_heat_cop
in_cool_cop = col1.number_input(
    label='Cooling COP', min_value=0.0, max_value=6.0, value=1.0, step=0.05)
if in_cool_cop != st.session_state.cool_cop:
    st.session_state.cool_cop = in_cool_cop
ip_help = 'Display output units in kBtu and ft2 instead of kWh and m2.'
in_ip_units = col2.checkbox(label='IP Units', value=False, help=ip_help)
if in_ip_units != st.session_state.ip_units:
    st.session_state.ip_units = in_ip_units
norm_help = 'Normalize all energy values by the gross floor area.'
in_normalize = col2.checkbox(label='Floor Normalize', value=True, help=norm_help)
if in_normalize != st.session_state.normalize:
    st.session_state.normalize = in_normalize

st.markdown("""---""")  # horizontal divider line between input and output
out_container = st.container()  # container to eventually hold the results

#if button_energy_simulation:
# preview the model and/or run the simulation

st.session_state.hb_model = simple_model

run_energy_simulation(
    st.session_state.target_folder,
    st.session_state.hb_model,
    st.session_state.epw_path, st.session_state.ddy_path, st.session_state.north
)

# create the resulting charts
display_results(
    out_container, st.session_state.sql_results,
    st.session_state.heat_cop, st.session_state.cool_cop,
    st.session_state.ip_units, st.session_state.normalize
)
