import pathlib
from uuid import uuid4

import streamlit as st
import honeybee
from honeybee.room import Room
from honeybee.model import Model, Face
from honeybee_radiance.properties.model import ModelRadianceProperties
from honeybee_vtk.model import DisplayMode
from honeybee_vtk.model import Model as VTKModel
from honeybee_vtk.vtkjs.schema import SensorGridOptions
from honeybee_radiance.sensorgrid import SensorGrid
from visualize_model import generate_vtk_model
from streamlit_vtkjs import st_vtkjs
from query import Query
from pollination_streamlit.api.client import ApiClient
from pollination_streamlit.interactors import Job, NewJob, Recipe
from queenbee.job.job import JobStatusEnum


query = Query()

api_key = st.sidebar.text_input(
    'Enter Pollination APIKEY', type='password',
    help=':bulb: You only need an API Key to access private projects. '
    'If you do not have a key already go to the settings tab under your profile to '
    'generate one.'
) or None

query.owner = st.sidebar.text_input('Project Owner', value=query.owner)
query.project = st.sidebar.text_input('Project Name', value=query.project)

run_simulation = st.sidebar.button('Run Simulation')
api_client = ApiClient(api_token=api_key)


col1, col2, col3= st.columns([1,2,1])

col2_con = col2.container()


col1.header('ROOMBOX')
room_width = col1.slider('Room Width', value=30, min_value=5, max_value=5)
room_depth = col1.slider('Room Depth', value=30, min_value=5, max_value=5)
room_height = col1.slider('Room Height', value=15, min_value=10, max_value=30)

wwr = col1.slider("WWR",max_value=95,min_value=10, step=5)/100

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

if run_simulation:
    query.job_id = None

    recipe = Recipe('ladybug-tools', 'daylight-factor',
                    'latest', api_client)
    new_job = NewJob(query.owner, query.project, recipe, client=api_client)
    model_project_path = new_job.upload_artifact(
        pathlib.Path(model_path), 'streamlit-job')
    # new_job.arguments = [
    #     {'width': query.width, 'depth': query.depth,
    #         'glazing-ration': query.glazing_ratio, 'model': model_project_path}
    # ]
    job = new_job.create()

    query.job_id = job.id

    if query.job_id is not None and query.owner is not None and query.project is not None:

        job = Job(query.owner, query.project, query.job_id, client=api_client)

        st.write(
            f'Checkout your job [here](https://app.pollination.cloud/projects/{query.owner}/{query.project}/jobs/{query.job_id})')

        if job.status.status in [
                JobStatusEnum.pre_processing,
                JobStatusEnum.running,
                JobStatusEnum.created,
                JobStatusEnum.unknown]:
            with st.spinner(text="Simulation in Progres..."):
                st.warning(f'Simulation is {job.status.status.value}...')
                st_autorefresh(interval=2000, limit=100)

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