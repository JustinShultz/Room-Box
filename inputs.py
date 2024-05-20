"""Functions for initializing inputs and formatting them for simulation"""
import os
import uuid
from pathlib import Path

import streamlit as st

from ladybug.epw import EPW
from honeybee.model import Model
from honeybee_vtk.model import Model as VTKModel

from pollination_streamlit_viewer import viewer
# from pollination_streamlit_io import get_hbjson


def initialize():
    """Initialize any of the session state variables if they don't already exist."""
    # user session
    # if 'user_id' not in st.session_state:
    #     st.session_state.user_id = str(uuid.uuid4())[:8]
    if 'target_folder' not in st.session_state:
        st.session_state.target_folder = Path(__file__).parent
    # sim session
    if 'hb_model' not in st.session_state:
        st.session_state.hb_model = None
    if 'vtk_path' not in st.session_state:
        st.session_state.vtk_path = None
    if 'valid_report' not in st.session_state:
        st.session_state.valid_report = None
    if 'epw_path' not in st.session_state:
        st.session_state.epw_path = None
    if 'ddy_path' not in st.session_state:
        st.session_state.ddy_path = None
    if 'north' not in st.session_state:
        st.session_state.north = None
    # output session
    if 'heat_cop' not in st.session_state:
        st.session_state.heat_cop = None
    if 'cool_cop' not in st.session_state:
        st.session_state.cool_cop = None
    if 'ip_units' not in st.session_state:
        st.session_state.ip_units = False
    if 'normalize' not in st.session_state:
        st.session_state.normalize = True
    if 'sql_results' not in st.session_state:
        st.session_state.sql_results = None


def new_weather_file():
    """Process a newly-uploaded EPW file."""
    # reset the simulation results and get the file data
    st.session_state.sql_results = None
    epw_file = st.session_state.epw_data
    if epw_file:
        # save EPW in data folder
        epw_path = Path(
            f'./{st.session_state.target_folder}/data/'
            f'{epw_file.name}'
        )
        epw_path.parent.mkdir(parents=True, exist_ok=True)
        epw_path.write_bytes(epw_file.read())
        # create a DDY file from the EPW
        ddy_file = epw_path.as_posix().replace('.epw', '.ddy')
        epw_obj = EPW(epw_path.as_posix())
        epw_obj.to_ddy(ddy_file)
        ddy_path = Path(ddy_file)
        # set the session state variables
        st.session_state.epw_path = epw_path
        st.session_state.ddy_path = ddy_path
    else:
        st.session_state.epw_path = None
        st.session_state.ddy_path = None


def get_weather_file(column):
    """Get the EPW weather file from the App input."""
    # upload weather file
    column.file_uploader(
        'Weather file (EPW)', type=['epw'],
        on_change=new_weather_file, key='epw_data',
        help='Select an EPW weather file to be used in the simulation.'
    )


def new_model():
    """Process a newly-uploaded Honeybee Model file."""
    # reset the simulation results and get the file data
    st.session_state.vtk_path = None
    st.session_state.valid_report = None
    st.session_state.sql_results = None
    # load the model object from the file data
    if 'hbjson' in st.session_state['hbjson_data']:
        hbjson_data = st.session_state['hbjson_data']['hbjson']
        st.session_state.hb_model = Model.from_dict(hbjson_data)


# def get_model(column):
#     """Get the Model input from the App input."""
#     # load the model object from the file data
#     with column:
#         hbjson_data = get_hbjson(key='hbjson_data', on_change=new_model)
#     if st.session_state.hb_model is None and hbjson_data is not None \
#             and 'hbjson' in hbjson_data:
#         st.session_state.hb_model = Model.from_dict(hbjson_data['hbjson'])


def generate_vtk_model(hb_model: Model, container):
    """Generate a VTK preview of an input model."""
    if not st.session_state.vtk_path:
        directory = os.path.join(
            st.session_state.target_folder.as_posix(),
            'data'#, st.session_state.user_id
        )
        if not os.path.isdir(directory):
            os.makedirs(directory)
        hbjson_path = hb_model.to_hbjson(hb_model.identifier, directory)
        vtk_model = VTKModel.from_hbjson(hbjson_path)
        vtk_path = vtk_model.to_vtkjs(folder=directory, name=hb_model.identifier)
        st.session_state.vtk_path = vtk_path
    vtk_path = st.session_state.vtk_path
    with container:
        viewer(content=Path(vtk_path).read_bytes(), key='vtk_preview_model')


def generate_model_validation(hb_model: Model, container):
    """Generate a Model validation report from an input model."""
    if not st.session_state.valid_report:
        report = hb_model.check_all(raise_exception=False, detailed=False)
        st.session_state.valid_report = report
    report = st.session_state.valid_report
    if report == '':
        container.success('Congratulations! Your Model is valid!')
    else:
        container.warning('Your Model is invalid for the following reasons:')
        container.code(report, language='console')


def get_inputs(host: str, container):
    """Get all of the inputs for the simulation."""
    # get the input model
    m_col_1, m_col_2 = container.columns([2, 1])
    get_model(m_col_1)
    # add options to preview the model in 3D and validate it
    if st.session_state.hb_model:
        if m_col_2.checkbox(label='Preview Model', value=False):
            generate_vtk_model(st.session_state.hb_model, container)
        if m_col_2.checkbox(label='Validate Model', value=False):
            generate_model_validation(st.session_state.hb_model, container)

    # get the input EPW and DDY files
    w_col_1, w_col_2 = container.columns([2, 1])
    get_weather_file(w_col_1)

    # set up inputs for north
    in_north = w_col_2.slider(label='North', min_value=0, max_value=360, value=0)
    if in_north != st.session_state.north:
        st.session_state.north = in_north
        st.session_state.sql_results = None  # reset to have results recomputed

    # get the inputs that only affect the display and do not require re-simulation
    col1, col2, col3 = container.columns(3)
    in_heat_cop = col1.number_input(
        label='Heating COP', min_value=0.0, max_value=6.0, value=1.0, step=0.05)
    if in_heat_cop != st.session_state.heat_cop:
        st.session_state.heat_cop = in_heat_cop
    in_cool_cop = col2.number_input(
        label='Cooling COP', min_value=0.0, max_value=6.0, value=1.0, step=0.05)
    if in_cool_cop != st.session_state.cool_cop:
        st.session_state.cool_cop = in_cool_cop
    ip_help = 'Display output units in kBtu and ft2 instead of kWh and m2.'
    in_ip_units = col3.checkbox(label='IP Units', value=False, help=ip_help)
    if in_ip_units != st.session_state.ip_units:
        st.session_state.ip_units = in_ip_units
    norm_help = 'Normalize all energy values by the gross floor area.'
    in_normalize = col3.checkbox(label='Floor Normalize', value=True, help=norm_help)
    if in_normalize != st.session_state.normalize:
        st.session_state.normalize = in_normalize