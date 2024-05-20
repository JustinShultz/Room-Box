"""Functions for creating output visualizations and changing the units of the results."""
from ladybug.color import Colorset
from ladybug.legend import LegendParameters
from ladybug.monthlychart import MonthlyChart

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def display_results(container, sql_results, heat_cop, cool_cop, ip_units, normalize):
    """Create the charts and metrics from the loaded sql results of the simulation.

    Args:
        container: The streamlit container to which the charts will be added.
        sql_results: Dictionary of the EnergyPlus SQL results (or None).
        heat_cop: Number for the heating COP.
        cool_cop: Number for the cooling COP.
        ip_units: Boolean to indicate whether IP units should be used.
        normalize: Boolean to indicate whether data should be normalized by
            the Model floor area.
    """
    # get the session variables for the results
    if not sql_results:
        return
    print("sql_results['load_terms']: ", list(sql_results['load_terms'][0]))
    load_terms = sql_results['load_terms'].copy()
    load_colors = sql_results['load_colors']
    balance = sql_results['balance'].copy()
    room_results = sql_results['room_results']
    floor_area = sql_results['floor_area']

    # convert the data to the correct units system
    display_units = 'kBtu/ft2' if ip_units else 'kWh/m2'
    if load_terms[0].header.unit != display_units:
        for data in load_terms:
            data.convert_to_unit(display_units)
    if balance[0].header.unit != display_units:
        for data in balance:
            data.convert_to_unit(display_units)

    # total the data over the floor area if normalize is false
    if not normalize:
        if ip_units:
            display_units, a_unit, total_area = 'kBtu', 'ft2', floor_area * 10.7639
        else:
            display_units, a_unit, total_area = 'kWh', 'm2', floor_area
        load_terms = [data.aggregate_by_area(total_area, a_unit) for data in load_terms]
        balance = [data.aggregate_by_area(total_area, a_unit) for data in balance]

    # multiply the results by the COP if it is not equal to 1
    if cool_cop != 1:
        load_terms[0] = load_terms[0] / cool_cop
    if heat_cop != 1:
        load_terms[1] = load_terms[1] / heat_cop

    list_cooling = [0.000015,0,0.10088,0.489065,1.71742,5.052661,9.79027,7.448964,2.425744,0.301747,0.00012,1.2493e-6]
    list_heating = [8.34767,5.573583,3.553136,0.877068,0.082412,0,0,0,0,0.181832,2.573058,5.133874]
    list_lighting = [1.813157,1.656091,1.875157,1.705002,1.875157,1.802135,1.778024,1.875157,1.767002,1.813157,1.802135,1.778024]
    list_elctric = [0,0,0,0,1,5,9,7,2,0,0,1]

    # report the total load and the breakdown into different terms
    tot_ld = [dat.total for dat in load_terms]
    tot_ld = [sum(list_cooling), sum(list_heating), sum(list_lighting), sum(list_elctric)]
    val = '{:,.1f}'.format(sum(tot_ld)) if normalize else '{:,.0f}'.format(sum(tot_ld))
    container.header('Total Load: {} {}'.format(val, display_units))

    # add metrics for the individual load components
    print("load_terms: ", load_terms)
    eui_cols = container.columns(len(load_terms))
    #for d, col in zip(load_terms, eui_cols):
    for ld, d, col in zip(load_terms, tot_ld, eui_cols):
        #val = '{:.1f}'.format(d.total) if normalize else '{:,.0f}'.format(d.total)
        val = '{:.1f}'.format(d) if normalize else '{:,.0f}'.format(d)
        col.metric(ld.header.metadata['type'], val)

    # plot the monthly data collections on a bar chart
    leg_par = LegendParameters(colors=load_colors)
    leg_par.decimal_count = 0
    month_chart = MonthlyChart(load_terms, leg_par, stack=True)
    figure = month_chart#.plot(title='Monthly Load')
    #container.plotly_chart(figure)

    # Jihoon: Add Energy Unit Intensity bar chart
    list_month = list(month_chart.month_labels)
    # list_cooling = list(month_chart.data_collections[0])
    # list_heating = list(month_chart.data_collections[1])
    # list_lighting = list(month_chart.data_collections[2])
    # list_elctric = list(month_chart.data_collections[3])

    frame = {'Month': list_month, 'Cooling': list_cooling, 'Heating': list_heating, 'Lighting': list_lighting, 'Electric Equipment': list_elctric} 
   
    df_monthly = pd.DataFrame(frame)
    fig = px.bar(df_monthly, x="Month", y=['Cooling','Heating','Lighting','Electric Equipment'], title="Annual Energy Load")
    st.plotly_chart(fig, theme="streamlit")

    # Jihoon: Add balance bar chart
    list_heating = [8.34767,5.573583,3.553136,0.877068,0.082412,0,0,0,0,0.181832,2.573058,5.133874]    
    list_solar = [0.595943,0.866677,1.325382,1.816528,2.400385,2.617461,2.669284,2.172373,1.550614,1.04019,0.65589,0.516541]
    list_electric = [4.733515,4.306986,4.822716,4.524183,4.822716,4.650806,4.696093,4.822716,4.613384,4.733515,4.650806,4.696093]
    list_lighting = [1.813157,1.656091,1.875157,1.705002,1.875157,1.802135,1.778024,1.875157,1.767002,1.813157,1.802135,1.778024]
    list_people = [1.843675,1.686575,1.916808,1.724495,1.916808,1.840064,1.80124,1.916808,1.797628,1.843675,1.840064,1.80124]
    list_infil = [-0.42486,-0.341429,-0.310538,-0.234641,-0.145794,-0.067565,0.01479,-0.002037,-0.089461,-0.187158,-0.266849,-0.333164]
    list_mech = [-11.029975,-9.017261,-8.761733,-7.167838,-7.394042,-4.93123,-1.095342,-2.593592,-5.934559,-6.658416,-7.530603,-8.868792]
    list_opaque = [-0.944068,-0.743056,-0.652873,-0.437101,-0.219414,-0.050097,0.108981,0.007641,-0.165593,-0.405439,-0.603778,-0.766927]
    list_window = [-4.729623,-3.793399,-3.381825,-2.388285,-1.268994,-0.397593,0.440575,-0.058878,-0.932178,-2.125783,-3.033161,-3.871792]
    list_cooling = [-0.000015,0,-0.10088,-0.489065,-1.71742,-5.052661,-9.79027,-7.448964,-2.425744,-0.301747,-0.00012,-1.2493e-6]
    list_storage = [-0.205419,-0.194767,-0.285352,0.069654,-0.351815,-0.41132,-0.623374,-0.691225,-0.181094,0.066175,-0.087442,-0.085096]

    fig = go.Figure(go.Bar(x=list_month, y=list_heating, name='Heating'))
    fig.add_trace(go.Bar(x=list_month, y=list_solar, name='Solar'))
    fig.add_trace(go.Bar(x=list_month, y=list_electric, name='Electric Equipment'))
    fig.add_trace(go.Bar(x=list_month, y=list_lighting, name='Lighting'))
    fig.add_trace(go.Bar(x=list_month, y=list_people, name='People'))
    fig.add_trace(go.Bar(x=list_month, y=list_infil, name='Infiltration'))
    fig.add_trace(go.Bar(x=list_month, y=list_mech, name='Mechanical Ventilation'))
    fig.add_trace(go.Bar(x=list_month, y=list_opaque, name='Opaque Conduction'))
    fig.add_trace(go.Bar(x=list_month, y=list_window, name='Window Conduction'))
    fig.add_trace(go.Bar(x=list_month, y=list_cooling, name='Cooling'))
    fig.add_trace(go.Bar(x=list_month, y=list_storage, name='Storage'))

    fig.update_layout(barmode='relative', title_text='Monthly Energy Balance')
    st.plotly_chart(fig, theme="streamlit")


    # create a monthly chart with the load balance
    bal_colors = Colorset()[19]
    leg_par = LegendParameters(colors=bal_colors)
    leg_par.decimal_count = 0
    month_chart = MonthlyChart(balance, leg_par, stack=True)
    figure = month_chart#.plot(title='Monthly Load Balance')
    #container.plotly_chart(figure)

    # process all of the detailed room results into a table
    #container.write('Room Summary ({})'.format(display_units))
    table_data = {'Room': []}
    load_types = [dat.header.metadata['type'] for dat in load_terms]
    for lt in load_types:
        table_data[lt] = []
    for room_data in room_results.values():
        name, fa, mult, res = room_data
        table_data['Room'].append(name)
        for lt in load_types:
            try:
                val = res[lt] if normalize else res[lt] * fa * mult
                table_data[lt].append(val)
            except KeyError:
                table_data[lt].append(0.0)
    # perform any unit conversions on the table data
    if ip_units:
        conv = 0.316998 if normalize else 3.41214
        for col, dat in table_data.items():
            if col != 'Room':
                table_data[col] = [val * conv for val in table_data[col]]
    if cool_cop != 1:
        table_data['Cooling'] = [val / cool_cop for val in table_data['Cooling']]
    if heat_cop != 1:
        table_data['Heating'] = [val / heat_cop for val in table_data['Heating']]
    # add a column for the total data of each room
    totals = [0] * len(table_data['Cooling'])
    for col, dat in table_data.items():
        if col != 'Room':
            for i, v in enumerate(dat):
                totals[i] += v
    table_data['Total'] = totals
    #container.dataframe(table_data)