import pathlib
from uuid import uuid4

import ladybug_geometry.geometry3d
import streamlit as st
import honeybee
import ladybug
from ladybug.epw import EPW
from ladybug.wea import Wea
import ladybug_geometry
from honeybee.room import Room
from honeybee.model import Model, Face, Aperture
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



#### CONFIGURE PAGE
app_title = 'ROOMBOX - HACKSIMBUILD 2024'
st.set_page_config(page_title=app_title, layout='wide')

if 'analysis_models' not in st.session_state:
    st.session_state['analysis_models'] = []

model_name =[]
baseline_model = []
hor_num = 0
hor_depth = 0
# vert_depth = 0
# vert_num = 0


#### hide sidebar by default
st.markdown("""
    <style>
        section[data-testid="stSidebar"][aria-expanded="true"]{
            display: none;
        }
    </style>
    """, unsafe_allow_html=True)


#### login
api_key = st.sidebar.text_input(
    'Enter Pollination APIKEY', type='password', value='8B8AC8B0.13F7476390ECDE0F50F7ED05',
    help=':bulb: You only need an API Key to access private projects. '
    'If you do not have a key already go to the settings tab under your profile to '
    'generate one.'
) or None

owner = st.sidebar.text_input('Project Owner', value="justinshultz")
project = st.sidebar.text_input('Project Name', value="hacksimbuild-2024")


#### run pollination

api_client = ApiClient(api_token=api_key)

st.header('ROOMBOX')
tab1, tab2 = st.tabs(['| 1 Model Creation','| 2 Results Visualization'])

with tab1:
    ##### establish layout

    col1, col2, col3= st.columns([1,2,1])
    col2_con = col2.container()

    

    with col1:


        #### room setup    
        col1_header, col2_header = st.columns([2,1])
        col1_header.subheader('Room Creation')

        units = col2_header.selectbox('UNITS', options=['Meter','Feet'], index=1, label_visibility='collapsed')


        #### room program
        with st.expander('1 - Bldg & Room Program', expanded=False):
            bldg_prog = st.selectbox('Bldg Program', options=['Select Bldg Program', 'Office','Lab','Higher Ed'], index=0, label_visibility='collapsed')
            room_prog = ''
            if bldg_prog != 'Select Bldg Program':
                room_prog = st.selectbox('Room Program', options=['Select Room Program', 'Open Office','Conference','Classroom'], index=0, label_visibility='collapsed')
        
        if bldg_prog != 'Select Bldg Program' and room_prog != 'Select Room Program':
            st.write(bldg_prog," :: ",room_prog)
        else:
            st.error('Select Bldg & Room Program')
        

        #### room geometry
        with st.expander('2 - Room Geometry', expanded=False):
            room_width = st.slider('Room Width', value=30, min_value=5, max_value=5)
            room_depth = st.slider('Room Depth', value=30, min_value=5, max_value=5)
            room_height = st.slider('Room Height', value=15, min_value=10, max_value=30)
            room_orient = st.slider('Room Orientation', value=180, step=5, min_value=0, max_value=355)
        st.write('Room Dimensions: ',str(room_width),' x ',str(room_depth),' x ',str(room_height),' @ ',str(room_orient),'°')


        #### room glazing
        with st.expander('3 - Glazing', expanded=False):
            wwr = st.slider("WWR", max_value=95, min_value=10, step=5, value=40)/100
            vlt = st.slider("VLT", max_value=90, min_value=10, step=5)/100
            shgc = st.slider("SHGC", max_value=90, min_value=10, step=5)/100
        st.write('WWR: ',str(wwr),"   - VLT: ",str(vlt),"   - SHGC",str(shgc))


        #### room shading
        with st.expander('4 - Shading', expanded=False):

            horizontal = st.checkbox('Horizontal Shading')
            if horizontal:
                hor_num = st.slider("Number of Overhangs", max_value=5, min_value=0, value=1)
                hor_depth = st.slider("Overhang Depth", max_value=6.0, min_value=0.0, step=.5, value=1.0)
                
                
            vertical = st.checkbox('Vertical Shading')
            if vertical:
                vert_num = st.slider("Number of Fins", max_value=5, min_value=0, value=1)
                vert_depth = st.slider("Fin Depth", max_value=6.0, min_value=0.0, step=.5, value=1.0)

        if horizontal:
            st.write(str(hor_num),' x  Horizontal Overhang: ',str(hor_depth)," deep")
        # if vertical:
        #     st.write(str(vert_num),' x  Vertical Overhang: ',str(vert_depth)," deep")

        save_model = ''

        #### save analysis model
        if bldg_prog != 'Select Bldg Program' and room_prog != 'Select Room Program':
            model_name = st.text_input('model name')




        #### create honeybee room
        room = Room.from_box(
            identifier=str(uuid4()),
            width=room_width,
            depth=room_depth,
            height=room_height)
        
        point_origin = ladybug_geometry.geometry3d.Point3D(x=room_width/2, y=room_depth/2 ,z=0)
        
        room.rotate_xy(-1*room_orient,point_origin)

        grid = SensorGrid.from_mesh3d(str(uuid4()), room.generate_grid(x_dim=2, offset=2.5))
        faces: Face = room.faces[1]

        faces.apertures_by_ratio(wwr)
        apertures: Aperture = faces.apertures[0]

        st.write(apertures)

        if hor_num >0:
            apertures.louvers_by_count(hor_num,hor_depth)


        simple_model = Model.from_objects(f'model_{room_width}_{room_depth}_{room_height}_{wwr}_{room_orient}_{hor_depth}_{hor_num}',[room],units='Feet')


        if model_name in st.session_state['analysis_models']:
            if bldg_prog != 'Select Bldg Program' and room_prog != 'Select Room Program':
                add_button = st.button("OVERRIDE: {}".format(model_name), key='add_button', type="primary")
                if add_button:
                    if len(model_name) > 0:
                        st.session_state['analysis_models'] += [model_name]
                        st.write(st.session_state['analysis_models'])
                    else:
                        st.warning("Enter text")

        else:
            if bldg_prog != 'Select Bldg Program' and room_prog != 'Select Room Program':
                add_button = st.button("SAVE ANALYSIS MODEL", key='add_button')
                if add_button:
                    if len(model_name) > 0:
                        st.session_state['analysis_models'] += [model_name]
                        st.write(st.session_state['analysis_models'])
                    else:
                        st.warning("Enter text")



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


    with col3:
        
        

        st.subheader('({}) Analysis Models'.format(len(st.session_state['analysis_models'])))
        col3_body1, col3_body2 = st.columns([2,1])

        if len(st.session_state['analysis_models']) >0:
            clear_models = col3_body2.button('X CLEAR')

            if clear_models:
                st.session_state['analysis_models']=[]


        

            baseline_model = col3_body1.radio('Select Baseline Model:', options=st.session_state['analysis_models'])

        with st.expander('5 - Project Location', expanded=False):
            url = "https://www.ladybug.tools/epwmap/"
            st.write("Launch [EPW Map](%s)" % url)
            epw_url = st.text_input('EPW URL')
            st.write('-- or --')
            epw_data = st.file_uploader("EPW File", type=['epw'], key='epw_data')

        if epw_data or epw_url:
            st.write('Project Location from EPW')
            run_simulation = st.button('Run Simulation')
        else:
            st.error('Add Project EPW file')




        



    if epw_data:
        epw_file = pathlib.Path(f'./data/{epw_data.name}')
        st.write(epw_file)
        epw_file.parent.mkdir(parents=True, exist_ok=True)
        epw_file.write_bytes(epw_data.read())

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
            wea_project_path = new_job.upload_artifact(
                pathlib.Path(wea_file), 'streamlit-job'
            )
            new_job.arguments = [
                {'model': model_project_path,
                'wea': wea_project_path,
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



with tab2:
    if baseline_model:
        st.write(baseline_model)