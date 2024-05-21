import pathlib
from uuid import uuid4

import os
import glob
import ladybug_geometry.geometry2d
import ladybug_geometry.geometry3d
import streamlit as st
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
from pollination_io.interactors import Job, NewJob, Recipe, Run
from queenbee.job.job import JobStatusEnum
from streamlit_autorefresh import st_autorefresh
import dload
import zipfile
from ladybug_vtk._extend_visualization_set import vs_to_vtkjs
from honeybee_display.model import VisualizationSet


#### CONFIGURE PAGE
app_title = 'ROOMBOX - HACKSIMBUILD 2024'
st.set_page_config(
    page_title=app_title, 
    layout='wide',
    page_icon='assets/240520_Roombox_Logo_v4.ico',
    initial_sidebar_state='collapsed'
    )

if 'model_names' not in st.session_state:
    st.session_state['model_names'] = []

if 'models' not in st.session_state:
    st.session_state['models'] = []

if 'study_inputs' not in st.session_state:
    st.session_state['study_inputs'] = []

if 'model_var' not in st.session_state:
    st.session_state['model_var'] = []

model_name = []
baseline_model = []
hor_num = 0
hor_depth = 0
run_simulation = []
vert_depth = 0
vert_num = 0
epw_data = 0
epw_filepath = ''
study_name = ''


#### hide sidebar by default
# st.markdown("""
#     <style>
#         section[data-testid="stSidebar"][aria-expanded="true"]{
#             display: none;
#         }
#     </style>
#     """, unsafe_allow_html=True)


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

st.image("assets/240520_Roombox_Logo_w.Name_w.PplName.png", width=700)
# if st.button('Clear Session State'):
#     st.session_state.clear()
#     st.success('Session state cleared!')

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
                hor_num = st.slider("Number of Overhangs", max_value=5, min_value=1, value=1)
                hor_depth = st.slider("Overhang Depth", max_value=6.0, min_value=0.0, step=.5, value=1.0)
                
                
            vertical = st.checkbox('Vertical Shading')
            if vertical:
                vert_num = st.slider("Number of Fins", max_value=5, min_value=1, value=1)
                vert_depth = st.slider("Fin Depth", max_value=6.0, min_value=0.0, step=.5, value=1.0)

        if horizontal:
            st.write(str(hor_num),' x  Horizontal Overhang: ',str(hor_depth)," deep")
        if vertical:
            st.write(str(vert_num),' x  Vertical Overhang: ',str(vert_depth)," deep")

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


        aperture_height = (apertures.max - apertures.min).z
        aperture_width = (apertures.max.x - apertures.min.x)


        if horizontal:
            apertures.louvers_by_distance_between(distance=aperture_height/hor_num, depth=hor_depth, base_name='shade_hor',contour_vector=ladybug_geometry.geometry2d.Vector2D(0, 1))
        if vertical:
            apertures.louvers_by_distance_between(distance=aperture_width/vert_num, depth=vert_depth, contour_vector=ladybug_geometry.geometry2d.Vector2D(1, 0), base_name='shade_vert')


        simple_model = Model.from_objects(
            identifier=f'model_{room_width}_{room_depth}_{room_height}_{wwr}_{room_orient}_{hor_depth}_{hor_num}_{vert_depth}_{vert_num}',
            objects=[room],
            units=units)
        
        # st.write(simple_model)
        simple_model._properties._radiance = ModelRadianceProperties(simple_model, [grid])

        model_path = simple_model.to_hbjson(name=simple_model.identifier, folder='data')
        vtk_path = pathlib.Path('data', f'{simple_model.identifier}.vtkjs')


        if model_name in st.session_state['model_names']:
            if bldg_prog != 'Select Bldg Program' and room_prog != 'Select Room Program':
                over_button = st.button("OVERRIDE: {}".format(model_name), key='over_button', type="primary")
                if over_button:
                    if len(model_name) > 0:
                        st.session_state['model_names'].append(model_name)
                        # st.write(st.session_state['model_names'])

                        # st.write(model_path)

                        # st.session_state['models'].append(model_path)
                        # st.write(st.session_state['models'])

                        # st.session_state['models_varialbles'].append({
                        #     'width': room_width, 
                        #     'depth': room_depth, 
                        #     'height': room_height,
                        #     'orientation': room_orient,
                        #     'glazing-ration': wwr, 
                        #     'VLT': vlt, 
                        #     'SHGC': shgc
                        # })

                    else:
                        st.warning("Enter text")

        else:
            if bldg_prog != 'Select Bldg Program' and room_prog != 'Select Room Program':
                add_button = st.button("SAVE ANALYSIS MODEL", key='add_button')
                if add_button:
                    if len(model_name) > 0:
                        st.session_state['model_names'] += [model_name]
                        # st.write(st.session_state['model_names'])

                        # st.write(model_path)

                        st.session_state['models'].append(model_path)
                        # st.write(st.session_state['models'])

                        st.session_state['model_var'].append({
                            'width': room_width, 
                            'depth': room_depth, 
                            'height': room_height,
                            'orientation': room_orient,
                            'glazing-ration': wwr, 
                            'VLT': vlt, 
                            'SHGC': shgc
                        })
                        # st.write(st.session_state['model_var'])

                    else:
                        st.warning("Enter text")


    if not vtk_path.is_file():
        VTKModel.from_hbjson(model_path, SensorGridOptions.Sensors).to_vtkjs(
            folder='data', name=simple_model.identifier)

    with col2_con:
        st_vtkjs(
            content=vtk_path.read_bytes(),
            key=simple_model.identifier, subscribe=False
        )


    with col3:

        st.subheader('({}) Analysis Models'.format(len(st.session_state['model_names'])))
        col3_body1, col3_body2 = st.columns([2,1])

        if len(st.session_state['model_names']) >0:
            clear_models = col3_body2.button('X CLEAR')

            if clear_models:
                st.session_state['model_names']=[]

            baseline_model = col3_body1.radio('Select Baseline Model:', options=st.session_state['model_names'])
            st.write(baseline_model)

        with st.expander('5 - Project Location', expanded=False):
            url = "https://www.ladybug.tools/epwmap/"
            st.write("Launch [EPW Map](%s)" % url)
            epw_url = st.text_input('EPW URL')

            files = glob.glob('data/epw/*')
            for f in files:
                os.remove(f)

            dload.save_unzip(epw_url, 'data/epw/', delete_after=True,)


            
            for file_name in os.listdir('data/epw/'):
                if file_name.endswith(".epw"):
                    epw_urlfile = 'data/epw/' + file_name

                    epw_filepath = epw_urlfile
            
                    st.write(epw_filepath)



            st.write('-- or --')
            epw_upload =  st.file_uploader("EPW File", type=['epw'], key='epw_upload', accept_multiple_files=False)
            # st.write(epw_upload)

            if epw_upload:
                epw_filepath = pathlib.Path(f'./data/{epw_upload.name}')
                # st.write(epw_filepath)

            if epw_filepath:
                epw_data = EPW(epw_filepath)

        # st.write(epw_data)
        if epw_data != 0:
            st.write('Project Location:',str(epw_data.location).split(',')[1])
            study_name = st.text_input('Study Name')
            run_simulation = st.button('Run Study')
        else:
            st.error('Add Project EPW file')


        if epw_data:
            # epw_file = pathlib.Path(f'./data/{epw_data.name}')
            # st.write(epw_file)
            # epw_file.parent.mkdir(parents=True, exist_ok=True)
            # epw_file.write_bytes(epw_data.read())

            # epw_obj = EPW(epw_file)
            wea_obj = Wea.from_epw_file(epw_filepath)
            wea_file = wea_obj.write(f'./data/weather_file.wea')
            # st.write(wea_file)
            # .to_wea(file_path=epw_file)

            if run_simulation:
                job_id = None

                recipe = Recipe(
                    owner = 'ladybug-tools',
                    name = 'annual-daylight',
                    tag = 'latest', 
                    client = api_client
                    )
                
                new_job = NewJob(
                    owner=owner, 
                    project=project, 
                    recipe=recipe, 
                    name=study_name,
                    client=api_client)
                wea_project_path = new_job.upload_artifact(pathlib.Path(wea_file), 'streamlit-job')
                
                recipe_inputs = {
                    'wea': wea_project_path
                }

                index = 0
                for mod in st.session_state['models']:
                    # st.write(mod)
                    model_project_path = new_job.upload_artifact(
                        pathlib.Path(mod), 'streamlit-job')
                    
                    inputs = dict(recipe_inputs)

                    inputs['model'] = model_project_path
                    inputs.update(st.session_state['model_var'][index])
                    
                    index += 1

                    # st.session_state['inputs']['model'] = model_project_path

                    # inputs= [
                    #     {'model': model_project_path,
                    #     'wea': wea_project_path,
                    #     # 'width': room_width, 
                    #     # 'depth': room_depth, 
                    #     # 'height': room_height,
                    #     # 'glazing-ration': wwr, 
                    #     # 'VLT': vlt, 
                    #     # 'SHGC': shgc
                    #     }
                    # ]

                    # st.session_state['study_inputs'].append(st.session_state['inputs'])
                    st.session_state['study_inputs'].append(inputs)

                st.write(st.session_state['study_inputs'])
                new_job.arguments = st.session_state['study_inputs']

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
                    # else:
                    #     job.runs_dataframe.parameters
                    #     res_model_path = view_results(
                    #         owner, project, job_id, api_key)
                    #     st_vtkjs(
                    #         content=pathlib.Path(res_model_path).read_bytes(), key='results',
                    #         subscribe=False
                    #     )

with tab2:
    from pollination_streamlit.selectors import get_api_client
    from pollination_streamlit_io import (select_account, select_cloud_artifact,
                                        select_project, select_study, select_run)
    from pollination_streamlit_viewer import viewer

    # in this tutorial, the api_client is taken from app.py
    # typically you would create the api_client as shown below
    
    api_client = get_api_client()

    account = select_account('select-account', api_client)
    study = None
    if account:
        # if it is an organization it uses account_name otherwise username
        project_owner = account.get('username') or account.get('account_name')
        st.subheader(f'Hi {project_owner}! Select a project:')

        pcol1, pcol2 = st.columns(2)

        with pcol1:
            project = select_project(
                'select-project',
                api_client,
                project_owner=project_owner
            )
        with pcol2:
            st.json(project or '{}', expanded=False)

        if project:
            # get project name
            project_name = project.get('name')
            st.subheader('Select a study:')

            scol1, scol2 = st.columns(2)

            with scol1:
                study = select_study(
                    'select-study',
                    api_client,
                    project_name=project_name,
                    project_owner=project_owner,
                )
            with scol2:
                st.json(study or '{}', expanded=False)
        
        if study: 
            #get run name
            study_name = study.get('name')
            # st.write(study.get('id'))
            st.subheader('Select a run:')

            scol1, scol2 = st.columns(2)

            with scol1:
                run = select_run(
                    'select-run',
                    api_client,
                    project_name=project_name,
                    project_owner=project_owner,
                    job_id=study.get('id'),
                )
                # print(run.keys())

                # assert False, run['owner']['name']
                    # project = project_name, 
                    # job_id = study.get('id'), 
                    # id = run.get('id'), 
                    # client = api_client)
                
                run_io = Run(
                    owner = run['owner']['name'], 
                    project = project_name, 
                    job_id = study.get('id'), 
                    id = run.get('id'), 
                    client = api_client)
                data = run_io.download_zipped_output('visualization')
                out_file = pathlib.Path('data', 'results', 'visualization.vsf')
                with zipfile.ZipFile(data) as zip_folder:
                    zip_folder.extractall(out_file.parent)
                
                vs = VisualizationSet.from_file(out_file.as_posix())
                vtkjs_file = out_file.parent.joinpath(f'{run.get("id")}.vtkjs')

            with scol2:
                st.json(run or '{}', expanded=False)
        
            if not vtkjs_file.is_file():
                vs_to_vtkjs(vs, out_file.parent, run.get('id'))
            viewer('results_viewer', content=vtkjs_file.read_bytes())

        # if study:
        #     study_id = study.get('id')
        #     st.subheader('Select an artifact:')
        #     st.info('It returns the name of the file \
        #             and the binary data to save.')

        #     acol1, acol2 = st.columns(2)

        #     with acol1:
        #         artifact = select_cloud_artifact(
        #             'sel-artifact',
        #             api_client,
        #             project_name=project_name,
        #             project_owner=project_owner,
        #             study_id=study_id,
        #             file_name_match=".*"
        #         )
        #     with acol2:
        #         st.json(artifact or {}, expanded=False)
        
        # name, value, type = artifact


        # st.write(name)

        # if artifact:
        #     st.info('Click on visualization card.')
        #     if name and name.endswith('vtkjs'):
        #         viewer(key='my-vsf', content=value)

        # st.write(artifact.file)
        # if artifact:
        #     dload.save_unzip(artifact[0], './data/results/', delete_after=False,)

            # with zipfile.ZipFile(artifact) as zip_folder:
            #     zip_folder.extractall('./data/results/')
            
            # vtkjs_path = pathlib.Path(out.target_folder + out.output_name)
        #         viewer(content=vtkjs_path.read_bytes(), key='df')

        # if run and run.progress == 100:
        #     if name and name.endswith('vtkjs'):
        #         viewer(key='my-vsf', content=value)

        # def download_output(api_key: str, owner: str, project: str, job_id: str, run_index: int,
        #         output_name: str, target_folder: str) -> None:
        #     """Download output from a job on Pollination.

        #     Args:
        #         api_key: The API key of the Pollination account.
        #         owner: The owner of the Pollination account.
        #         project: The name of the project inside which the job was created.
        #         job_id: The id of the job.
        #         run_index: The index of the run inside the job.
        #         output_name: The name of the output you wish to download. You can find the names
        #             of all the outputs either on the job page or on the recipe page.
        #         target_folder: The folder where the output will be downloaded.
        #     """
        #     out_job = Job(owner, project, job_id, client=api_client)
        #     out_run = out_job.runs[run_index]
        #     output = out_run.download_zipped_output(output_name)

        #     with zipfile.ZipFile(output) as zip_folder:
        #         zip_folder.extractall(target_folder)
        
        # if study is not None and project_owner is not None and project_name is not None and run is not None:
        #     out = download_output(
        #         owner= project_owner,
        #         project= project_name,
        #         job_id= study.get('id'),
        #         run_index= 1,
        #         output_name='visualization.vtkjs',
        #         target_folder='./data/results',
        #         api_key=api_key
        #     )

        #     st.write(out)

        #     if out is not None:
        #         vtkjs_path = pathlib.Path(out.target_folder + out.output_name)
        #         viewer(content=vtkjs_path.read_bytes(), key='df')