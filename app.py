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
from pollination_io.api.client import ApiClient
from pollination_io.interactors import Job, NewJob, Recipe
from queenbee.job.job import JobStatusEnum
from streamlit_autorefresh import st_autorefresh


api_key = st.sidebar.text_input(
    'Enter Pollination APIKEY', type='password', value='8B8AC8B0.13F7476390ECDE0F50F7ED05',
    help=':bulb: You only need an API Key to access private projects. '
    'If you do not have a key already go to the settings tab under your profile to '
    'generate one.'
) or None

owner = st.sidebar.text_input('Project Owner', value="justinshultz")
project = st.sidebar.text_input('Project Name', value="hacksimbuild-2024")

run_simulation = st.sidebar.button('Run Simulation')
api_client = ApiClient(api_token=api_key)


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

epw_data = st.file_uploader("EPW File", type=['epw'], key='epw_data')
if epw_data:
    epw_file = pathlib.Path(f'./data/{epw_data.name}')
    st.write(epw_file)
    # epw_file.parent.mkdir(parents=True, exist_ok=True)
    # epw_file.write_bytes(epw_data.read())
epw_obj = EPW(epw_file)
wea_obj = Wea.from_epw_file(epw_file)
wea_file = wea_obj.write(f'./data/weather_file.wea')
st.write(wea_file)
# .to_wea(file_path=epw_file)

if run_simulation:
    job_id = None

    recipe = Recipe('ladybug-tools', 'annual-daylight',
                    'latest', api_client)
    new_job = NewJob(owner, project, recipe, client=api_client)
    model_project_path = new_job.upload_artifact(
        pathlib.Path(model_path), 'streamlit-job')
    new_job.arguments = [
        {'model': model_project_path,
         'wea': wea_file,
         'width': room_width, 
         'depth': room_depth, 
         'height': room_height,
         'glazing-ration': wwr, 
         'VLT': vlt, 
         'SHGC': shgc}
    ]
    job = new_job.create()

    job_id = job.id

    if job_id is not None and owner is not None and project is not None:

        job = Job(owner, project, job_id, client=api_client)

        st.write(
            f'Checkout your job [here](https://app.pollination.cloud/{owner}/projects/{project}/jobs/{job_id})')

        if job.status.status in [
                JobStatusEnum.pre_processing,
                JobStatusEnum.running,
                JobStatusEnum.created,
                JobStatusEnum.unknown]:
            with st.spinner(text="Simulation in Progres..."):
                st.warning(f'Simulation is {job.status.status.value}...')
                # st_autorefresh(interval=2000, limit=100)

        elif job.status.status in [JobStatusEnum.failed, JobStatusEnum.cancelled]:
            st.warning(f'Simulation is {job.status.status.value}')
        else:
            job.runs_dataframe.parameters
            # res_model_path = view_results(
            #     query.owner, query.project, query.job_id, api_key)
            # st_vtkjs(
            #     content=pathlib.Path(res_model_path).read_bytes(), key='results',
            #     subscribe=False
            # )