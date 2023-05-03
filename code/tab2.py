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

path = None
n_clicks = None
global_counts = 0
global cps_list

def show_tab2():

    datafolder = fn.get_path('data')
    # Get all filenames in data folder and its subfolders
    files = [os.path.relpath(file, datafolder).replace("\\", "/")
             for file in glob.glob(os.path.join(datafolder, "**", "*.json"), recursive=True)]
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

    database = fn.get_path('data.db')
    conn            = sql.connect(database)
    c               = conn.cursor()
    query           = "SELECT * FROM settings "
    c.execute(query) 

    settings        = c.fetchall()[0]

    filename        = settings[1]
    device          = settings[2]             
    sample_rate     = settings[3]
    chunk_size      = settings[4]
    threshold       = settings[5]
    tolerance       = settings[6]
    bins            = settings[7]
    bin_size        = settings[8]
    max_counts      = settings[9]
    shapestring     = settings[10]
    sample_length   = settings[11]

    calib_bin_1     = settings[12]
    calib_bin_2     = settings[13]
    calib_bin_3     = settings[14]

    calib_e_1       = settings[15]
    calib_e_2       = settings[16]
    calib_e_3       = settings[17]

    coeff_1         = settings[18]
    coeff_2         = settings[19]
    coeff_3         = settings[20]
    filename2       = settings[21]
    peakfinder      = settings[23]
    sigma           = settings[25]

    html_tab2 = html.Div(id='tab2', children=[
        html.Div(id='polynomial', children=''),
        html.Div(id='bar_chart_div', # Histogram Chart
            children=[
                dcc.Graph(id='bar-chart', figure={},),
                dcc.Interval(id='interval-component', interval=1000, n_intervals=0) # Refresh rate 1s.
            ]),

        html.Div(id='t2_filler_div', children=''),
        #Start button
        html.Div(id='t2_setting_div', children=[
            html.Button('START', id='start'),
            html.Div(id='counts', children= ''),
            html.Div('Counts'),
            html.Div(id='start_text' , children =''),

            ]),

        html.Div(id='t2_setting_div', children=[            
            html.Button('STOP', id='stop'),
            html.Div(id='elapsed', children= '' ),
            html.Div(id='cps', children=''),
            #html.Div('Seconds'),
            html.Div(id='stop_text', children= ''),
            ]),

        html.Div(id='t2_setting_div', children=[
            html.Div(['File name:', dcc.Input(id='filename' ,type='text' ,value=filename )]),
            html.Div(['Number of bins:', dcc.Input(id='bins'        ,type='number'  ,value=bins )]),
            html.Div(['bin size      :', dcc.Input(id='bin_size'    ,type='number'  ,value=bin_size )]),
            ]), 


        html.Div(id='t2_setting_div', children=[
            html.Div(['Stop at n counts', dcc.Input(id='max_counts', type='number', value=max_counts )]),
            html.Div(['LLD Threshold:', dcc.Input(id='threshold', type='number', value=threshold )]),
            html.Div(['Shape Tolerance:', dcc.Input(id='tolerance', type='number', value=tolerance )]),
            ]),

        html.Div(id='t2_setting_div', children=[
            html.Div('Select Comparison'),
            html.Div(dcc.Dropdown(
                    id='filename2',
                    options=options_sorted,
                    placeholder='Select acomparison',
                    value=filename2,
                    style={'font-family':'Arial', 'height':'32px', 'margin':'0px', 'padding':'0px','border':'None', 'text-align':'left'}
                    )),

            html.Div(['Show Comparison'      , daq.BooleanSwitch(id='compare_switch',on=False, color='purple',)]),
            html.Div(['Subtract Comparison'  , daq.BooleanSwitch(id='difference_switch',on=False, color='purple',)]),

            ]),

        html.Div(id='t2_setting_div'    , children=[
            html.Div(['Energy by bin'  , daq.BooleanSwitch(id='epb_switch',on=False, color='purple',)]),
            html.Div(['Show log(y)'     , daq.BooleanSwitch(id='log_switch',on=False, color='purple',)]),
            html.Div(['Calibration'    , daq.BooleanSwitch(id='cal_switch',on=False, color='purple',)]),
            ]), 

        html.Div(id='t2_setting_div'    , children=[
            html.Button('Gaussian Soundbyte <))', id='soundbyte'),
            html.Div(id='audio', children='Audio representartion of comparison sepectrum'),
            ]), 


        html.Div(id='t2_setting_div', children=[
            html.Div('Calibration Bins'),
            html.Div(dcc.Input(id='calib_bin_1', type='number', value=calib_bin_1)),
            html.Div(dcc.Input(id='calib_bin_2', type='number', value=calib_bin_2)),
            html.Div(dcc.Input(id='calib_bin_3', type='number', value=calib_bin_3)),
            html.Div('peakfinder'),
            html.Div(dcc.Slider(id='peakfinder', min=0 ,max=1, step=0.1, value= peakfinder, marks=['0','1'])),
            ]),

        html.Div(id='t2_setting_div', children=[
            html.Div('Energies'),
            html.Div(dcc.Input(id='calib_e_1', type='number', value=calib_e_1)),
            html.Div(dcc.Input(id='calib_e_2', type='number', value=calib_e_2)),
            html.Div(dcc.Input(id='calib_e_3', type='number', value=calib_e_3)),
            html.Div('Gaussian corr. (sigma)'),
            html.Div(dcc.Slider(id='sigma', min=0 ,max=3, step=0.25, value= sigma, marks=['0','1', '2', '3'])),
            
            ]),

        html.Div(children=[ html.Img(id='footer', src='https://www.gammaspectacular.com/steven/impulse/footer.gif')]),
        
        html.Div(id='subfooter', children=[
            ]),

    ]) # End of tab 2 render

    return html_tab2

#------START---------------------------------

@app.callback( Output('start_text'  ,'children'),
                [Input('start'      ,'n_clicks')])

def update_output(n_clicks):
    if n_clicks is None:
        raise PreventUpdate
    else:       
        fn.clear_global_cps_list()
        pc.pulsecatcher()
        return " "
#----STOP------------------------------------------------------------

@app.callback( Output('stop_text'  ,'children'),
                [Input('stop'      ,'n_clicks')])

def update_output(n_clicks):
    if n_clicks is None:
        raise PreventUpdate
    else:
        fn.stop_recording()
        return " "
#----------------------------------------------------------------

@app.callback([ Output('bar-chart'          ,'figure'), 
                Output('counts'             ,'children'),
                Output('elapsed'            ,'children'),
                Output('cps'                ,'children')],
               [Input('interval-component'  ,'n_intervals'), 
                Input('filename'            ,'value'), 
                Input('epb_switch'          ,'on'),
                Input('log_switch'          ,'on'),
                Input('cal_switch'          ,'on'),
                Input('filename2'           ,'value'),
                Input('compare_switch'      ,'on'),
                Input('difference_switch'   ,'on'),
                Input('peakfinder'          ,'value'),
                Input('sigma'               ,'value'),
                Input('tabs'                ,'value')
                ])

def update_graph(n, filename, epb_switch, log_switch, cal_switch, filename2, compare_switch, difference_switch, peakfinder, sigma, active_tab):

    if active_tab != 'tab2':  # only update the chart when "tab2" is active
        raise PreventUpdate

    global global_counts
    histogram1 = fn.get_path(f'data/{filename}.json')
    histogram2 = fn.get_path(f'data/{filename2}.json')

    if os.path.exists(histogram1):
        with open(histogram1, "r") as f:

            data = json.load(f)
            numberOfChannels    = data["resultData"]["energySpectrum"]["numberOfChannels"]
            validPulseCount     = data["resultData"]["energySpectrum"]["validPulseCount"]
            elapsed             = data["resultData"]["energySpectrum"]["measurementTime"]
            polynomialOrder     = data["resultData"]["energySpectrum"]["energyCalibration"]["polynomialOrder"]
            coefficients        = data["resultData"]["energySpectrum"]["energyCalibration"]["coefficients"]
            spectrum            = data["resultData"]["energySpectrum"]["spectrum"]
            coefficients        = coefficients[::-1] # Revese order

            mu = 0
            prominence = 0.5

            if sigma == 0:
                gc = []
            else:    
                gc = fn.gaussian_correl(spectrum, sigma)
            

            if elapsed == 0:
                cps = 0  
            else:
                cps = validPulseCount - global_counts
                global_counts = validPulseCount  
     
            x = list(range(numberOfChannels))
            y = spectrum
            max_index = np.argmax(y)
            max_log_index = np.log10(max_index)+2

            if cal_switch == True:
                x = np.polyval(np.poly1d(coefficients), x)

            if epb_switch == True:
                y = [i * count for i, count in enumerate(spectrum)]
                gc= [i * count for i, count in enumerate(gc)]

            trace1 = go.Scatter(
                x=x, 
                y=y, 
                mode='lines+markers', 
                fill='tozeroy' ,  
                marker={'color': 'darkblue', 'size':3}, 
                line={'width':1})

  #-------------------annotations-----------------------------------------------          
            peaks, fwhm = fn.peakfinder(y, prominence, peakfinder)
            num_peaks   = len(peaks)
            annotations = []
            lines       = []

            for i in range(num_peaks):
                peak_value  = peaks[i]
                counts      = y[peaks[i]]
                x_pos       = peaks[i]
                y_pos       = y[peaks[i]]
                resolution  = (fwhm[i]/peaks[i])*100

                if cal_switch == True:
                    peak_value  = np.polyval(np.poly1d(coefficients), peak_value)
                    x_pos       = peak_value

                if log_switch == True:
                    y_pos = y_pos    

                if peakfinder != 0:
                    annotations.append(
                        dict(
                            x= x_pos,
                            y= y_pos + 10,
                            xref='x',
                            yref='y',
                            text=f'cts: {counts}<br>bin: {peak_value:.1f}<br>{resolution:.1f}%',
                            showarrow=True,
                            arrowhead=1,
                            ax=0,
                            ay=-40
                        )
                    )


                lines.append(
                    dict(
                        type='line',
                        x0=x_pos,
                        y0=0,
                        x1=x_pos,
                        y1=y_pos,
                        line=dict(
                            color='white',
                            width=1,
                            dash='dot'
                        )
                    )
                )

            layout = go.Layout(
                paper_bgcolor = 'white', 
                plot_bgcolor = 'white',
                title={
                'text': filename,
                'x': 0.5,
                'y': 0.9,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'family': 'Arial', 'size': 24, 'color': 'black'},
                },
                height  =450, 
                margin_t=0,
                margin_b=0,
                margin_l=0,
                margin_r=0,
                autosize=True,
                xaxis=dict(dtick=50, tickangle = 90, range =[0, max(x)]),
                yaxis=dict(autorange=True),
                annotations=annotations,
                shapes=lines,
                uirevision="Don't change",
                )
#---------------Histrogram2 ---------------------------------------------------------------------------

            if os.path.exists(histogram2):
                with open(histogram2, "r") as f:
                    data_2 = json.load(f)
                    numberOfChannels_2    = data_2["resultData"]["energySpectrum"]["numberOfChannels"]
                    elapsed_2             = data_2["resultData"]["energySpectrum"]["measurementTime"]
                    spectrum_2            = data_2["resultData"]["energySpectrum"]["spectrum"]
 
                    if elapsed > 0:
                        steps = (elapsed/elapsed_2)
                    else:
                        steps = 0.1    

                    x2 = list(range(numberOfChannels_2))
                    y2 = [int(n * steps) for n in spectrum_2]

                    if cal_switch == True:
                        x2 = np.polyval(np.poly1d(coefficients), x2)

                    if epb_switch == True:
                        y2 = [i * n * steps for i, n in enumerate(spectrum_2)]

                    if log_switch == True:
                        lin_log = 'log'

                    trace2 = go.Scatter(
                        x=x2, 
                        y=y2, 
                        mode='lines+markers',  
                        marker={'color': 'red', 'size':1}, 
                        line={'width':2})

        if sigma == 0:
            trace4 = {}
        else:    
            trace4 = go.Scatter(
                x=x, 
                y=gc, 
                mode='lines+markers',  
                marker={'color': 'yellow', 'size':1}, 
                line={'width':2})
    
        if compare_switch == False:
            fig = go.Figure(data=[trace1, trace4], layout=layout)

        if compare_switch == True: 
            fig = go.Figure(data=[trace1, trace2], layout=layout) 

        if difference_switch == True:
            y3 = [a - b for a, b in zip(y, y2)]
            trace3 = go.Scatter(
                            x=x, 
                            y=y3, 
                            mode='lines+markers', 
                            fill='tozeroy',  
                            marker={'color': 'green', 'size':3}, 
                            line={'width':1}
                            )

            fig = go.Figure(data=[trace3], layout=layout)

            fig.update_layout(yaxis=dict(autorange=False, range=[min(y3),max(y3)]))

        if difference_switch == False:
            fig.update_layout(yaxis=dict(autorange=True))

        if log_switch == True:
            fig.update_layout(yaxis=dict(autorange=False, type='log', range=[0, max_log_index]))
    
        return fig, f'{validPulseCount}', f'{elapsed}', f'cps {cps}'

    else:
        layout = go.Layout(
                paper_bgcolor = 'white', 
                plot_bgcolor = 'white',
                title={
                'text': filename,
                'x': 0.5,
                'y': 0.9,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'family': 'Arial', 'size': 24, 'color': 'black'}
                },
                height  =450, 
                autosize=True,
                xaxis=dict(dtick=50, tickangle = 90, range =[0, 100]),
                yaxis=dict(autorange=True),
                uirevision="Don't change",
                )
        return go.Figure(data=[], layout=layout), 0, 0, 0

#--------UPDATE SETTINGS------------------------------------------------------------------------------------------
@app.callback( Output('polynomial'        ,'children'),
                [Input('bins'           ,'value'),
                Input('bin_size'        ,'value'),
                Input('max_counts'      ,'value'),
                Input('filename'        ,'value'),
                Input('filename2'       ,'value'),
                Input('threshold'       ,'value'),
                Input('tolerance'       ,'value'),
                Input('calib_bin_1'     ,'value'),
                Input('calib_bin_2'     ,'value'),
                Input('calib_bin_3'     ,'value'),
                Input('calib_e_1'       ,'value'),
                Input('calib_e_2'       ,'value'),
                Input('calib_e_3'       ,'value'),
                Input('peakfinder'      ,'value'),
                Input('sigma'           ,'value')
                ])  

def save_settings(bins, bin_size, max_counts, filename, filename2, threshold, tolerance, calib_bin_1, calib_bin_2, calib_bin_3, calib_e_1, calib_e_2, calib_e_3, peakfinder, sigma):
    
    database = fn.get_path('data.db')

    conn = sql.connect(database)
    c = conn.cursor()

    query = f"""UPDATE settings SET 
                    bins={bins}, 
                    bin_size={bin_size}, 
                    max_counts={max_counts}, 
                    name='{filename}', 
                    comparison='{filename2}',
                    threshold={threshold}, 
                    tolerance={tolerance}, 
                    calib_bin_1={calib_bin_1},
                    calib_bin_2={calib_bin_2},
                    calib_bin_3={calib_bin_3},
                    calib_e_1={calib_e_1},
                    calib_e_2={calib_e_2},
                    calib_e_3={calib_e_3},
                    peakfinder={peakfinder},
                    sigma={sigma}
                    WHERE id=0;"""

    c.execute(query)
    conn.commit()

    x_bins        = [calib_bin_1, calib_bin_2, calib_bin_3]
    x_energies    = [calib_e_1, calib_e_2, calib_e_3]

    coefficients  = np.polyfit(x_bins, x_energies, 2)
    polynomial_fn = np.poly1d(coefficients)


    conn  = sql.connect(database)
    c     = conn.cursor()

    query = f"""UPDATE settings SET 
                    coeff_1={float(coefficients[0])},
                    coeff_2={float(coefficients[1])},
                    coeff_3={float(coefficients[2])}
                    WHERE id=0;"""
    
    c.execute(query)
    conn.commit()

    return f'Polynomial (ax^2 + bx + c) = ({polynomial_fn})'

@app.callback( Output('audio'       ,'children'),
                [Input('soundbyte'  ,'n_clicks'),
                Input('filename2'   ,'value')])    


def play_sound(n_clicks, filename2):

    if n_clicks != None:
        spectrum_2 = []
        histogram2 = fn.get_path(f'data/{filename2}.json')

        if os.path.exists(histogram2):
                with open(histogram2, "r") as f:
                    data_2     = json.load(f)
                    spectrum_2 = data_2["resultData"]["energySpectrum"]["spectrum"]

        gc = fn.gaussian_correl(spectrum_2, 1)

        asp.make_wav_file(filename2, gc)

        asp.play_wav_file(filename2)
    
    return 
