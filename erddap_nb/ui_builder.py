# erddap_nb/ui_builder.py

import ipywidgets as widgets
from functools import partial
from . import event_handlers

def build_search_results(results, on_select_callback):
    """
    Creates a VBox containing buttons for each search result.
    """
    if not results:
        return widgets.Label("No datasets found for your query.")
    
    buttons = []
    for item in results:
        did = item.get("dataset_id", "N/A")
        title = item.get("title", "N/A")
        institution = item.get("institution", "N/A")
        
        button_text = f"Title: {title} | ID: {did} | Institution: {institution}"
        
        button = widgets.Button(
            description=button_text,
            layout=widgets.Layout(width='auto', height='auto'),
            style={'text_align': 'left'},
            button_style='info'
        )
        
        button.on_click(partial(on_select_callback, did))
        buttons.append(button)
        
    return widgets.VBox(buttons, layout=widgets.Layout(align_items='flex-start'))


def build_griddap_ui(metadata, server, dataset_id, output_area, app_state, saved_dfs_placeholder):
    title = metadata.get('global_attrs', {}).get('title', 'No Title Provided')
    summary = metadata.get('global_attrs', {}).get('summary', 'No Summary Provided.')
    spacing_info_parts = []
    for dim in metadata.get('dimensions', []):
        dim_name = dim.get('name', 'N/A')
        avg_spacing = dim.get('average_spacing', 'N/A')
        spacing_info_parts.append(f"<b>{dim_name}</b> - average spacing: {avg_spacing}")
    
    spacing_html = "<br>".join(spacing_info_parts)
    
    info_html = f"<h2>{title} ({dataset_id})</h2><p>{summary}</p><p>{spacing_html}</p>"
    info_widget = widgets.HTML(value=info_html)

    w = {'data_var_checkboxes': {}, 'constraint_widgets': {}}
    variable_rows = []
    variable_rows.append(widgets.HTML('<h4>Dimensions</h4>'))

    for dim in metadata['dimensions']:
        dim_name, range_str = dim['name'], dim.get('actual_range', '')
        range_parts = [p.strip() for p in str(range_str).split(',')]
        unit_str = ""
        if "time" in dim['name'].lower():
            unit_str = "(UTC)"
        else:
            units = dim.get('units')
            long_name = dim.get('long_name')
            if units and units != '1':
                unit_str = f"({units})"

        nu = f"{dim['name']} {unit_str}".strip()
        label = widgets.HBox([
            widgets.Label(value=nu, layout=widgets.Layout(width='200px')),
        ])
        filter_widget = None

        if "time" in dim_name.lower():
            start_w = widgets.Text(value=metadata.get('global_attrs', {}).get('time_coverage_start', ''), layout=widgets.Layout(width='150px'))
            stop_w = widgets.Text(value=metadata.get('global_attrs', {}).get('time_coverage_end', ''), layout=widgets.Layout(width='150px'))
            filter_widget = widgets.HBox([start_w, widgets.Label("to"), stop_w])
            w['constraint_widgets'][dim_name] = (start_w, stop_w)
        elif len(range_parts) == 2:
            try:
                min_v, max_v = float(range_parts[0]), float(range_parts[1])
                if min_v != max_v:
                    decimals = 4 if any(axis in dim_name.lower() for axis in ['lat', 'lon']) else 2
                    step = dim['average_spacing']
                    start_text = widgets.BoundedFloatText(value=round(min_v, decimals), min=min_v, max=max_v, step=step, layout=widgets.Layout(width='120px'))
                    stop_text = widgets.BoundedFloatText(value=round(max_v, decimals), min=min_v, max=max_v, step=step, layout=widgets.Layout(width='120px'))
                    slider = widgets.FloatRangeSlider(min=min_v, max=max_v, value=[min_v, max_v], step=step, description="", continuous_update=False, layout=widgets.Layout(width='260px'), readout=False)

                    def update_texts_from_slider(change, st=start_text, sp=stop_text, dec=decimals):
                        st.value, sp.value = round(change['new'][0], dec), round(change['new'][1], dec)
                    slider.observe(update_texts_from_slider, names='value')

                    def update_slider_from_texts(change, sl=slider, st=start_text, sp=stop_text):
                        sl.value = [st.value, sp.value]
                    start_text.observe(update_slider_from_texts, names='value')
                    stop_text.observe(update_slider_from_texts, names='value')

                    filter_widget = widgets.VBox([widgets.HBox([start_text, stop_text]), slider])
                    w['constraint_widgets'][dim_name] = (start_text, stop_text)
                else:
                    filter_widget = widgets.Label(value="No range in values")
            except ValueError:
                filter_widget = widgets.Label(value="Non-numeric range")
        
        if filter_widget:
             a_spacing = f"average spacing: {dim['average_spacing']}"
             row = widgets.HBox([widgets.Label(value="", layout=widgets.Layout(width='50px')), label, filter_widget])
             variable_rows.append(row)
    
    variable_rows.append(widgets.HTML('<hr style="margin-top:10px; margin-bottom:10px;"><h4>Variables</h4>'))

    for var in metadata['data_variables']:
        var_name = var['name']
        select_cb = widgets.Checkbox(value=False, description='', indent=False, layout=widgets.Layout(width='50px'))
        unit_str = ""
        if "time" in var['name'].lower():
            unit_str = "(UTC)"
        else:
            units = var.get('units')
            long_name = var.get('long_name')
            if units and units != '1':
                unit_str = f"({units})"

        nu = f"{var['name']} {unit_str}".strip()
        label = widgets.HBox([
            widgets.Label(value=nu, layout=widgets.Layout(width='200px')),
        ])
        filter_widget = widgets.Label(value="N/A (sliced by dimensions)")
        w['data_var_checkboxes'][var_name] = select_cb
        row = widgets.HBox([select_cb, label, filter_widget], layout=widgets.Layout(align_items='center'))
        variable_rows.append(row)

    constraints_placeholder = widgets.VBox(variable_rows)
    
    all_graph_opts = ([d['name'] for d in metadata['dimensions']] + [v['name'] for v in metadata['data_variables']])
    w.update({
        'graph_type': widgets.Dropdown(description="Graph Type:", options=['surface', 'lines', 'markers']), 'x_axis': widgets.Dropdown(description="X-Axis:", options=all_graph_opts),
        'y_axis': widgets.Dropdown(description="Y-Axis:", options=all_graph_opts), 'color_var': widgets.Dropdown(description="Color:", options=[None] + [v['name'] for v in metadata['data_variables']]),
        'palette': widgets.Dropdown(description='Palette:', options=['Default', 'Rainbow', 'ReverseRainbow']), 'reverse_x': widgets.Checkbox(value=False, description='Reverse X-Axis'),
        'reverse_y': widgets.Checkbox(value=False, description='Reverse Y-Axis'), 'graph_display': widgets.Image(value=b'', format='png', layout=widgets.Layout(max_height='400px')),
        'filetype_dd': widgets.Dropdown(options=[('NetCDF', 'nc'), ('CSV', 'csv'), ('JSON', 'json'), ('GeoTIFF', 'geotiff'), ('Parquet', 'parquet')], value='nc', description='File Type:', layout=widgets.Layout(width='150px'))
    })
    
    update_graph_button = widgets.Button(description="Update Graph")
    download_button = widgets.Button(description="Download Data", button_style='primary')
    df_name_input = widgets.Text(placeholder='df_name', description='Save as:')
    w['df_name_input'] = df_name_input

    update_graph_button.on_click(partial(event_handlers.on_griddap_graph_clicked, w, server, dataset_id, output_area))
    download_button.on_click(partial(event_handlers.on_griddap_download_clicked, w, server, dataset_id, output_area, app_state, saved_dfs_placeholder))
    
    variables_section = widgets.VBox([widgets.HTML("<h3>Define Subset & Select Variables</h3>"), constraints_placeholder], layout=widgets.Layout(margin='10px 250px 10px 0'))
    graphing_section = widgets.VBox([widgets.HTML("<h3>Create a Graph</h3>"), widgets.HBox([widgets.VBox([w['graph_type'], w['x_axis'], w['y_axis'], w['color_var'], w['palette'], w['reverse_x'], w['reverse_y'], update_graph_button], layout=widgets.Layout(width='100%', margin='15px 15px 50px 50px')), w['graph_display'] ])], layout=widgets.Layout(margin='10px 0 0 0'))
    
    download_section = widgets.VBox([
        widgets.HTML("<hr><h3>Download Data</h3>"),
        widgets.HBox([df_name_input, download_button, w['filetype_dd']])
    ])

    return widgets.VBox([info_widget, widgets.HBox([variables_section, graphing_section]), download_section])


def build_tabledap_ui(metadata, server, dataset_id, output_area, app_state, saved_dfs_placeholder):
    title = metadata.get('global_attrs', {}).get('title', 'No Title Provided')
    summary = metadata.get('global_attrs', {}).get('summary', 'No Summary Provided.')
    info_html = f"<h2>{title} ({dataset_id})</h2><p>{summary}</p>"
    info_widget = widgets.HTML(value=info_html)

    w = {}
    all_vars_map = metadata['all_variables_map']
    all_vars_names = list(all_vars_map.keys())
    variable_rows = []
    w['constraint_widgets'] = {}
    
    operator_options = ['=', '!=', '<=', '>=', '<', '>', '=~']

    for var_name in all_vars_names:
        var_info = all_vars_map.get(var_name, {})
        range_str = str(var_info.get('actual_range', ''))
        range_parts = [p.strip() for p in range_str.split(',')]
        select_cb = widgets.Checkbox(value=False, description='', indent=False, layout=widgets.Layout(width='30px'))
        unit_str = ""
        if "time" in var_name.lower():
            unit_str = "(UTC)"
        else:
            units = var_info.get('units')
            long_name = var_info.get('long_name')
            if units and units != 1:
                unit_str = f"({units})"

        nu = f"{var_name} {unit_str}".strip()
        label = widgets.HBox([
            widgets.Label(value=nu, layout=widgets.Layout(width='200px')),
        ])
        filter_widget = None

        if "time" in var_name.lower() or (len(range_parts) == 2 and range_str.lower() != "n/a"):
            is_time = "time" in var_name.lower()
            
            op_start_dd = widgets.Dropdown(options=operator_options, value='>=', layout=widgets.Layout(width='55px'))
            op_stop_dd = widgets.Dropdown(options=operator_options, value='<=', layout=widgets.Layout(width='55px'))
            
            if is_time:
                time_start = metadata.get('global_attrs', {}).get('time_coverage_start', '')
                time_end = metadata.get('global_attrs', {}).get('time_coverage_end', '')
                start_text = widgets.Text(value=time_start, layout=widgets.Layout(width='120px'))
                stop_text = widgets.Text(value=time_end, layout=widgets.Layout(width='120px'))
                slider = widgets.SelectionRangeSlider(options=[time_start, time_end], index=(0, 1), description='', layout=widgets.Layout(width='360px'), continuous_update=False, readout=False)
            else:
                try:
                    min_v, max_v = float(range_parts[0]), float(range_parts[1])
                    if min_v == max_v:
                        filter_widget = widgets.Label(value="No range, no constraint controls available")
                    else:
                        decimals = 4 if any(axis in var_name.lower() for axis in ['lat', 'lon']) else 2
                        start_text = widgets.BoundedFloatText(value=round(min_v, decimals), min=min_v, max=max_v, step=10**-decimals, layout=widgets.Layout(width='120px'))
                        stop_text = widgets.BoundedFloatText(value=round(max_v, decimals), min=min_v, max=max_v, step=10**-decimals, layout=widgets.Layout(width='120px'))
                        slider = widgets.FloatRangeSlider(min=min_v, max=max_v, value=[min_v, max_v], step=10**-decimals, description="", continuous_update=False, layout=widgets.Layout(width='360px'), readout=False)
                except (ValueError, IndexError):
                    filter_widget = widgets.Label(value="No range, no constraint controls available")

            # If we successfully created the widgets, set up the logic
            if filter_widget is None:
                # --- Link Sliders and Text Boxes ---
                def update_texts_from_slider(change, st=start_text, sp=stop_text):
                    st.value, sp.value = change['new'][0], change['new'][1]
                
                def update_slider_from_texts_numeric(change, sl=slider, st=start_text, sp=stop_text):
                    sl.value = [st.value, sp.value]

                if not is_time:
                    slider.observe(update_texts_from_slider, names='value')
                    start_text.observe(update_slider_from_texts_numeric, names='value')
                    stop_text.observe(update_slider_from_texts_numeric, names='value')
                else:
                    # For SelectionRangeSlider, only link slider to text to avoid errors
                    # if user types a date not in the slider's options.
                    slider.observe(update_texts_from_slider, names='value')

                # --- Logic for handling '=' operator ---
                def on_op_change(change, osd=op_start_dd, ssd=op_stop_dd, st=start_text, sp=stop_text, sl=slider):
                    is_start_eq = (osd.value == '=')
                    is_stop_eq = (ssd.value == '=')

                    # If start is '=', disable stop controls and clear its value
                    ssd.disabled = is_start_eq
                    sp.disabled = is_start_eq

                    # If stop is '=', disable start controls and clear its value
                    osd.disabled = is_stop_eq
                    st.disabled = is_stop_eq
                    
                    # Disable slider if either is '='
                    sl.disabled = is_start_eq or is_stop_eq

                op_start_dd.observe(on_op_change, names='value')
                op_stop_dd.observe(on_op_change, names='value')

                filter_controls = widgets.HBox([op_start_dd, start_text, op_stop_dd, stop_text])
                filter_widget = widgets.VBox([filter_controls, slider])
                w['constraint_widgets'][var_name] = {
                    'select': select_cb, 'start': start_text, 'stop': stop_text, 
                    'slider': slider, 'is_time': is_time, 'op_start': op_start_dd, 'op_stop': op_stop_dd
                }
            else:
                 w['constraint_widgets'][var_name] = {'select': select_cb}

        else: # This handles string-based inputs
            filter_widget = widgets.Label(value="No range, no constraint controls available") if not range_str or range_str.lower() == "n/a" else None
            if filter_widget:
                w['constraint_widgets'][var_name] = {'select': select_cb}
            else:
                op_dd = widgets.Dropdown(options=operator_options, value='=', layout=widgets.Layout(width='55px'))
                val_txt = widgets.Text(layout=widgets.Layout(width='120px'))
                filter_widget = widgets.HBox([op_dd, val_txt])
                w['constraint_widgets'][var_name] = {'select': select_cb, 'op': op_dd, 'val': val_txt}
        
        row = widgets.HBox([select_cb, label, filter_widget])
        variable_rows.append(row)

    header = widgets.HBox([widgets.HTML(value="<b>Variable</b>")])
    constraints_placeholder = widgets.VBox([header] + variable_rows)
    w.update({
        'graph_type': widgets.Dropdown(description="Graph Type:", options=['lines', 'markers', 'linesAndMarkers']), 'x_axis': widgets.Dropdown(description="X-Axis:", options=[None] + all_vars_names),
        'y_axis': widgets.Dropdown(description="Y-Axis:", options=[None] + all_vars_names), 'color_var': widgets.Dropdown(description="Color:", options=[None] + all_vars_names),
        'palette': widgets.Dropdown(description='Palette:', options=['Default', 'Rainbow', 'ReverseRainbow']), 'reverse_x': widgets.Checkbox(value=False, description='Reverse X-Axis'),
        'reverse_y': widgets.Checkbox(value=False, description='Reverse Y-Axis'), 'graph_display': widgets.Image(value=b'', format='png', layout=widgets.Layout(max_height='400px'))
    })
    update_graph_button = widgets.Button(description="Update Graph")
    download_button = widgets.Button(description="Download Data", button_style='primary')
    
    df_name_input = widgets.Text(placeholder='df_name', description='Save as:')
    w['df_name_input'] = df_name_input
    
    filetype_dd = widgets.Dropdown(options=[('CSV', 'csv'), ('NetCDF', 'nc'), ('JSON', 'json'), ('GeoTIFF', 'geotiff'), ('Parquet', 'parquet'), ('KML', 'kml')], value='csv', description='File Type:', layout=widgets.Layout(width='150px'))
    w['filetype_dd'] = filetype_dd

    update_graph_button.on_click(partial(event_handlers.on_tabledap_graph_clicked, w, server, dataset_id, output_area, metadata))
    
    download_button.on_click(partial(event_handlers.on_tabledap_download_clicked, w, server, dataset_id, output_area, app_state, saved_dfs_placeholder))

    variables_section = widgets.VBox([widgets.HTML("<h3>Columns & Filters</h3>"), constraints_placeholder], layout=widgets.Layout(margin='10px 250px 10px 0'))
    graphing_section = widgets.VBox([widgets.HTML("<h3>Graph</h3>"), widgets.HBox([widgets.VBox([w['graph_type'], w['x_axis'], w['y_axis'], w['color_var'], w['palette'], w['reverse_x'], w['reverse_y'], update_graph_button], layout=widgets.Layout(width='100%', margin='15px 15px 50px 50px')), w['graph_display'] ])], layout=widgets.Layout(margin='10px 0 0 0'))
    
    download_section = widgets.VBox([
        widgets.HTML("<hr><h3>Download Data</h3>"),
        widgets.HBox([df_name_input, download_button, filetype_dd])
    ])

    return widgets.VBox([info_widget, widgets.HBox([variables_section, graphing_section]), download_section])


def update_saved_dfs_display(app_state, placeholder, output_area):
    """
    Updates the list of saved DataFrames visible in the UI, now with save and delete buttons.
    """
    if not app_state.get('dataframes'):
        placeholder.children = []
        return
        
    header = widgets.HTML("<h4>DataFrames in Memory:</h4>")
    
    items = []
    for df_name in app_state['dataframes'].keys():
        # A placeholder for this row's save UI
        save_options_placeholder = widgets.VBox()
        
        df_label = widgets.Label(df_name, layout=widgets.Layout(flex='1 1 auto'))
        
        # Create a "Save to file..." button
        save_button = widgets.Button(
            description="Save...", 
            button_style='success',
            layout=widgets.Layout(width='auto')
        )
        save_button.on_click(
            partial(
                event_handlers.on_save_requested, 
                df_name=df_name, 
                app_state=app_state, 
                save_options_placeholder=save_options_placeholder,
                output_area=output_area
            )
        )
        
        delete_button = widgets.Button(
            description="Delete",
            button_style='danger',
            layout=widgets.Layout(width='auto')
        )
        delete_button.on_click(
            partial(
                event_handlers.on_delete_df_clicked,
                df_name=df_name,
                app_state=app_state,
                placeholder=placeholder,
                output_area=output_area
            )
        )
        
        # A row for each DataFrame: its name, save/delete buttons, and the placeholder for save options
        item_row = widgets.HBox([df_label, save_button, delete_button, save_options_placeholder])
        items.append(item_row)

    placeholder.children = [widgets.VBox([header] + items, layout=widgets.Layout(border='1px solid #cccccc', padding='10px', width='auto'))]
