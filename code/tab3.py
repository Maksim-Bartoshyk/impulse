import dash

import plotly.graph_objs as go

import pulsecatcher as pc
import functions as fn
import os
import json
import glob
import numpy as np
import sqlite3 as sql
import dash_daq as daq
import audio_spectrum as asp
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
from server import app
from dash.exceptions import PreventUpdate
from datetime import datetime


global_counts = 0
global cps_list

def show_tab3():
    fn.log_info('tab3 render start')

    # Get all filenames in data folder and its subfolders
    files = [os.path.relpath(file, fn.get_data_dir()).replace("\\", "/")
             for file in glob.glob(os.path.join(fn.get_data_dir(), "**", "*.json"), recursive=True)]
    # Add "i/" prefix to subfolder filenames for label and keep the original filename for value
    options = [{'label': "~ " + os.path.basename(file), 'value': file} if "i/" in file and file.endswith(".json") 
                else {'label': os.path.basename(file), 'value': file} for file in files]
    # Filter out filenames ending with "-cps"
    options = [opt for opt in options if not opt['value'].endswith("-cps.json")]
    # Sort options alphabetically by label
    options_sorted = sorted(options, key=lambda x: x['label'])

    for file in options_sorted:
        file['label'] = file['label'].replace('.json', '')
        file['value'] = file['value'].replace('.json', '')

    settings        = fn.load_settings()

    spectrum_name   = settings[1]
    max_counts      = settings[9]
    max_seconds     = settings[26]
    t_interval      = settings[27]

    refresh_rate = t_interval * 1000

    html_tab3 = html.Div(id='tab3', children=[
        html.Div(id='polynomial_3d', children=''),
        html.Div(id='bar_chart_div_3d', children=[
            dcc.Graph(id='chart_3d', figure={},),
            dcc.Interval(id='interval-component', interval=refresh_rate, n_intervals=0)
            ]),

        html.Div(id='t2_filler_div', children=''),
        html.Div(id='t2_setting_div', children=[
            html.Button('START', id='start_3d', disabled=pc.is_capturing()),
            html.Div(id='counts_3d', children= '', style={'font-size': '24px'}),
            html.Div(id='start_text_3d' , children =''),
            html.Div(['Max Counts', dcc.Input(id='max_counts', type='number', step=1000, readOnly=False, value=max_counts )]),
            ]),

        html.Div(id='t2_setting_div', children=[            
            html.Button('STOP', id='stop_3d', disabled=not pc.is_capturing()),
            html.Div(id='elapsed_3d', children= '', style={'font-size': '24px'}),
            html.Div(['Max Seconds', dcc.Input(id='max_seconds', type='number', step=60,  readOnly=False, value=max_seconds )]),
            html.Div(id='cps_3d', children=''),
            html.Div(id='status_3d', children=get_capturing_status()),
            ]),

        html.Div(id='t2_setting_div3', children=[
            html.Div(['File name:', dcc.Input(id='spectrum_name' ,type='text' ,value=spectrum_name )]),
            ]), 

        html.Div(id='t2_setting_div4', children=[
            html.Div(['Update Interval(s)', dcc.Input(id='t_interval', type='number', step=1,  readOnly=False, value=t_interval )]),
            ]),

        html.Div(id='t2_setting_div5', children=[
            ]),

        html.Div(id='t2_setting_div6'    , children=[
            html.Div(['Energy by bin'  , daq.BooleanSwitch(id='epb_switch',on=False, color='purple',)]),
            html.Div(['Show log(y)'     , daq.BooleanSwitch(id='log_switch',on=False, color='purple',)]),
            html.Div(['Calibration'    , daq.BooleanSwitch(id='cal_switch',on=False, color='purple',)]),
            ]), 
            
        html.Div(children=[ html.Img(id='footer', src='https://www.gammaspectacular.com/steven/impulse/footer.gif')]),
        
        html.Div(id='subfooter', children=[
            ]),

        ]) # End of tab 3 render

    fn.log_info('tab3 render end')
    return html_tab3

#------START---------------------------------

@app.callback([ 
                Output('start_3d'            ,'disabled', allow_duplicate=True),
                Output('stop_3d'             ,'disabled', allow_duplicate=True),
                Output('status_3d'           ,'children', allow_duplicate=True)
              ],
              [ 
                Input('start_3d'             ,'n_clicks')
              ],
                prevent_initial_call=True)

def update_output(n_clicks):
    if n_clicks is None:
        raise PreventUpdate

    else:
        mode = 3       
        fn.clear_global_cps_list()
        pc.start_capture(mode, False)

        return pc.is_capturing(), not pc.is_capturing(), get_capturing_status()
        
        
#----STOP------------------------------------------------------------

@app.callback([ 
                Output('start_3d'            ,'disabled', allow_duplicate=True),
                Output('stop_3d'             ,'disabled', allow_duplicate=True),
                Output('status_3d'           ,'children', allow_duplicate=True)
              ],
              [ 
                Input('stop_3d'              ,'n_clicks')
              ],
                prevent_initial_call=True)

def update_output(n_clicks):

    if n_clicks is None:
        raise PreventUpdate

    else:
        pc.stop_capture()

        return pc.is_capturing(), not pc.is_capturing(), get_capturing_status()
        

#-----RENDER CHART-----------------------------------------------------------

@app.callback([ 
                Output('chart_3d'           ,'figure'), 
                Output('counts_3d'          ,'children'),
                Output('elapsed_3d'         ,'children'),
                Output('cps_3d'             ,'children'),
                Output('start_3d'           ,'disabled'),
                Output('stop_3d'            ,'disabled'),
                Output('status_3d'          ,'children')
              ],
              [
                Input('interval-component'  ,'n_intervals'), 
                Input('spectrum_name'       ,'value'), 
                Input('epb_switch'          ,'on'),
                Input('log_switch'          ,'on'),
                Input('cal_switch'          ,'on'),
                Input('tabs'                ,'value'),
                Input('t_interval'          ,'value')
              ])


def update_graph(n, spectrum_name, epb_switch, log_switch, cal_switch, active_tab, t_interval):

    if active_tab != 'tab3':
        raise PreventUpdate
    
    if n is None:
        raise PreventUpdate

    if log_switch == True:
        axis_type = 'log'

    else:
        axis_type = 'linear'        
    
    global global_counts
    
    histogram3 = fn.get_file_path(f'{spectrum_name}_3d.json')

    now = datetime.now()
    time = now.strftime("%A %d %B %Y")

    title_text = "<b>{}</b><br><span style='font-size: 12px'>{}</span>".format(spectrum_name, time)

    if os.path.exists(histogram3):
        with open(histogram3, "r") as f:
            data = json.load(f)

            numberOfChannels = data["resultData"]["energySpectrum"]["numberOfChannels"]
            validPulseCount = data["resultData"]["energySpectrum"]["validPulseCount"]
            elapsed = data["resultData"]["energySpectrum"]["measurementTime"]
            polynomialOrder = data["resultData"]["energySpectrum"]["energyCalibration"]["polynomialOrder"]
            coefficients = data["resultData"]["energySpectrum"]["energyCalibration"]["coefficients"]
            spectra = data["resultData"]["energySpectrum"]["spectrum"]
            coefficients = coefficients[::-1]  # Reverse order

        if elapsed == 0:
            global_cps = 0  
        else:
            global_cps = int((validPulseCount - global_counts)/t_interval)
            global_counts = validPulseCount 

        x = list(range(numberOfChannels))
        y = list(range(len(spectra)))
        z = spectra
        scale = [[0, 'blue'], [0.33, 'green'], [0.66, 'yellow'], [1, 'red']]
        
        if log_switch:
            scale = [[0, 'blue'], [0.01, 'green'], [0.1, 'yellow'], [1, 'red']]
            
        data = go.Heatmap(x = x, y = y, z = z, colorscale = scale)
        fig = go.Figure(data = data)

        return fig, f'{validPulseCount}', f'{elapsed}', f'cps {global_cps}', pc.is_capturing(), not pc.is_capturing(), get_capturing_status()

    else:
        x = []
        y = []
        z = []
        scale = [[0, 'blue'], [0.33, 'green'], [0.66, 'yellow'], [1, 'red']]
        
        if log_switch:
            scale = [[0, 'blue'], [0.01, 'green'], [0.1, 'yellow'], [1, 'red']]
            
        data = go.Heatmap(x = x, y = y, z = z, colorscale = scale)
        fig = go.Figure(data = data)

        return fig, 0, 0, 0, pc.is_capturing(), not pc.is_capturing(), get_capturing_status()

#--------UPDATE SETTINGS------------------------------------------------------------------------------------------
@app.callback( Output('polynomial_3d'   ,'children'),
               [Input('max_counts'      ,'value'),
                Input('max_seconds'     ,'value'),
                Input('t_interval'      ,'value'),
                Input('spectrum_name'   ,'value'),
                ])  

def save_settings(max_counts, max_seconds, t_interval, spectrum_name):
    
    database = fn.get_file_path('.data.db')

    conn = sql.connect(database)
    c = conn.cursor()

    query = f"""UPDATE settings SET 
                    max_counts={max_counts},
                    max_seconds={max_seconds}, 
                    name='{spectrum_name}', 
                    t_interval={t_interval}
                    WHERE id=0;"""

    c.execute(query)
    conn.commit()

    return ''
    
def get_capturing_status():
    status = 'stopped'
    if pc.is_capturing():
        status = 'capturing'
        
    return status
