# erddap_nb/event_handlers.py

import pandas as pd
import requests
from IPython.display import display, clear_output
from erddapy import ERDDAP
from functools import partial
import ipywidgets as widgets
import xarray as xr

# --- Helper Functions to Read UI State ---

def get_griddap_selected_vars(widgets):
    """Helper to get selected data variables from the griddap UI."""
    return [name for name, cb in widgets.get('data_var_checkboxes', {}).items() if cb.value]

def get_griddap_constraints(widgets):
    """Reads constraints from the griddap UI widgets."""
    constraints = {}
    for name, widget_tuple in widgets['constraint_widgets'].items():
        start_val, stop_val = widget_tuple[0].value, widget_tuple[1].value
        if start_val is not None and str(start_val) != '':
            constraints[f'{name}>='] = start_val
        if stop_val is not None and str(stop_val) != '':
            constraints[f'{name}<='] = stop_val
    return constraints

def get_tabledap_selected_vars(widgets):
    """Helper to get selected data variables from the tabledap UI."""
    return [name for name, c in widgets['constraint_widgets'].items() if c.get('select') and c['select'].value]

def get_tabledap_constraints(widgets, metadata):
    """
    Builds a constraint dictionary for erddapy, using pre-encoded operators
    in the dictionary keys and skipping constraints for default values.
    """
    constraints = {}
    # This map provides the URL-encoded operators that erddapy expects in the dictionary key.
    op_map = {'=': '=', '>=': '>=', '<=': '<=', '>': '>', '<': '<', '!=': '!=', '=~': '=~'}
    
    all_variables_map = metadata.get('all_variables_map', {})
    global_attrs = metadata.get('global_attrs', {})

    for name, c_widget_map in widgets['constraint_widgets'].items():
        if not (c_widget_map.get('select') and c_widget_map['select'].value):
            continue

        # Case 1: Range-based controls with selectable operators
        if 'op_start' in c_widget_map:
            start_op = c_widget_map.get('op_start').value
            start_val = c_widget_map.get('start').value
            is_time = c_widget_map.get('is_time', False)
            
            default_min, default_max = None, None
            if is_time:
                default_min = global_attrs.get('time_coverage_start')
                default_max = global_attrs.get('time_coverage_end')
            else:
                var_info = all_variables_map.get(name, {})
                actual_range_str = str(var_info.get('actual_range', ''))
                range_parts = [p.strip() for p in actual_range_str.split(',')]
                if len(range_parts) == 2:
                    default_min, default_max = range_parts[0], range_parts[1]

            if start_val is not None and str(start_val).strip() != '':
                is_default_start = False
                if default_min is not None:
                    if not is_time:
                        try:
                            if float(start_val) == float(default_min): is_default_start = True
                        except (ValueError, TypeError): pass
                    elif start_val == default_min:
                        is_default_start = True
                
                if not is_default_start:
                    key = f"{name}{op_map.get(start_op, start_op)}"
                    constraints[key] = start_val
            
            if start_op == '=':
                continue
                
            stop_op = c_widget_map.get('op_stop').value
            stop_val = c_widget_map.get('stop').value

            if stop_val is not None and str(stop_val).strip() != '':
                is_default_stop = False
                if default_max is not None:
                    if not is_time:
                        try:
                            if float(stop_val) == float(default_max): is_default_stop = True
                        except (ValueError, TypeError): pass
                    elif stop_val == default_max:
                        is_default_stop = True
                
                if not is_default_stop:
                    key = f"{name}{op_map.get(stop_op, stop_op)}"
                    constraints[key] = stop_val
        
        # Case 2: Single value (string inputs)
        elif 'op' in c_widget_map and 'val' in c_widget_map and c_widget_map['val'].value:
            op = c_widget_map['op'].value
            raw_val = c_widget_map['val'].value
            final_val = raw_val

            # This correctly handles all number formats from the text box.
            try:
                num_val = float(raw_val)
                # If it's a whole number, store it as an integer.
                if num_val.is_integer():
                    final_val = int(num_val)
                else:
                    final_val = num_val
            except ValueError:
                # If conversion fails, it's a true string, so we pass it as-is.
                pass

            key = f"{name}{op_map.get(op, op)}"
            constraints[key] = final_val
            
    return constraints

# --- Graph and Download Button Handlers ---

def on_griddap_graph_clicked(widgets, server, dataset_id, output_area, b):
    with output_area:
        clear_output(); print("Generating griddap graph...")
        try:
            e = ERDDAP(server=server, protocol='griddap')
            e.dataset_id = dataset_id
            constraints = get_griddap_constraints(widgets)
            if widgets['graph_type'].value == 'surface' and 'time>=' in constraints:
                constraints['time<='] = constraints['time>=']
            e.griddap_initialize(); e.constraints.update(constraints)
            primary_var = widgets['color_var'].value if widgets['color_var'].value else widgets['y_axis'].value
            if not primary_var:
                print("Please select a Y-Axis or Color variable to plot."); return
            e.variables = [primary_var]
            graph_url = e.get_download_url(response="png")
            graph_url += f"&.draw={widgets['graph_type'].value}"
            vars_list = [widgets['x_axis'].value, widgets['y_axis'].value]
            if widgets['color_var'].value: vars_list.append(widgets['color_var'].value)
            graph_url += f"&.vars={'|'.join(vars_list)}"
            if widgets['palette'].value != 'Default': graph_url += f"&.colorBar={widgets['palette'].value}"
            if widgets['reverse_x'].value: graph_url += '&.xRange=||false'
            if widgets['reverse_y'].value: graph_url += '&.yRange=||false'
            response = requests.get(graph_url); response.raise_for_status()
            widgets['graph_display'].value = response.content; print("Graph updated.")
        except Exception as ex:
            print(f"Failed to generate graph: {ex}")

def on_tabledap_graph_clicked(widgets, server, dataset_id, output_area, metadata, b):
    with output_area:
        clear_output(); print("Generating tabledap graph...")
        try:
            e = ERDDAP(server=server, protocol='tabledap')
            e.dataset_id = dataset_id
            plot_vars = [v for v in [widgets['x_axis'].value, widgets['y_axis'].value, widgets['color_var'].value] if v]
            if not plot_vars:
                print("Please select at least an X-Axis variable."); return
            e.variables = plot_vars
            e.constraints = get_tabledap_constraints(widgets, metadata)
            
            graph_url = e.get_download_url(response="png")
            graph_url += f"&.draw={widgets['graph_type'].value}"
            if widgets['palette'].value != 'Default': graph_url += f"&.colorBar={widgets['palette'].value}"
            if widgets['reverse_x'].value: graph_url += '&.xRange=||false'
            if widgets['reverse_y'].value: graph_url += '&.yRange=||false'
            
            response = requests.get(graph_url); response.raise_for_status()
            widgets['graph_display'].value = response.content; print("Graph updated.")
        except Exception as ex:
            print(f"Failed to generate graph: {ex}")

def on_griddap_download_clicked(widgets, server, dataset_id, output_area, app_state, saved_dfs_placeholder, b):
    from . import ui_builder
    with output_area:
        clear_output(); print("Building query and fetching griddap data...")
        try:
            e = ERDDAP(server=server, protocol='griddap')
            e.dataset_id = dataset_id
            selected_vars = get_griddap_selected_vars(widgets)
            if not selected_vars:
                print("Please select at least one data variable to download."); return

            e.griddap_initialize()
            e.variables = selected_vars
            e.constraints.update(get_griddap_constraints(widgets))

            filetype = widgets.get('filetype_dd').value
            df_name = widgets['df_name_input'].value
            if not df_name:
                df_name = f"{dataset_id}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"

            if filetype == 'csv' or filetype == 'parquet':
                if filetype == 'csv':
                    df = e.to_pandas(skiprows=(1,))
                else:
                    url = e.get_download_url(response='parquet')
                    df = pd.read_parquet(url)

                app_state['dataframes'][df_name] = {'data': df, 'source_format': filetype}
                clear_output()
                print(f"Success! DataFrame from {filetype.upper()} saved as '{df_name}'.")
                display(df.head())
                print("--- Summary Statistics ---")
                display(df.describe())

            elif filetype == 'nc':
                ds = e.to_xarray()
                app_state['dataframes'][df_name] = {'data': ds, 'source_format': 'netcdf'}
                clear_output()
                print(f"Success! Xarray Dataset saved as '{df_name}'.")
                display(ds)

            else: # json, geotiff, etc.
                url = e.get_download_url(response=filetype)
                clear_output()
                print(f"Success! Non-ingestable format requested. Download data directly from this link:\n{url}")
                return

            ui_builder.update_saved_dfs_display(app_state, saved_dfs_placeholder, output_area)

        except Exception as err:
            print(f"Failed to fetch data: {err}")

def on_tabledap_download_clicked(widgets, server, dataset_id, output_area, app_state, saved_dfs_placeholder, b):
    from . import ui_builder
    with output_area:
        clear_output(); print("Building query and fetching tabledap data...")
        try:
            e = ERDDAP(server=server, protocol='tabledap')
            e.dataset_id = dataset_id
            selected_vars = get_tabledap_selected_vars(widgets)
            if not selected_vars:
                print("Please select at least one variable to download."); return
            e.variables = selected_vars
            e.constraints = get_tabledap_constraints(widgets, app_state['metadata'])

            filetype = widgets.get('filetype_dd').value
            df_name = widgets['df_name_input'].value
            if not df_name:
                df_name = f"{dataset_id}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"

            if filetype == 'csv':
                df = e.to_pandas()
                app_state['dataframes'][df_name] = {'data': df, 'source_format': 'csv'}
            elif filetype == 'parquet':
                url = e.get_download_url(response='parquet')
                df = pd.read_parquet(url)
                app_state['dataframes'][df_name] = {'data': df, 'source_format': 'parquet'}
            elif filetype == 'nc':
                ds = e.to_xarray()
                app_state['dataframes'][df_name] = {'data': ds, 'source_format': 'netcdf'}
            else:
                url = e.get_download_url(response=filetype)
                clear_output()
                print(f"Success! Non-ingestable format requested. Download data directly from this link:\n{url}")
                return

            clear_output()
            print(f"Success! Data saved to memory as '{df_name}'.")
            if 'data' in app_state['dataframes'][df_name]:
                 display(app_state['dataframes'][df_name]['data'].head() if filetype != 'nc' else app_state['dataframes'][df_name]['data'])
                 print("--- Summary Statistics ---")
                 display(app_state['dataframes'][df_name]['data'].describe() if filetype != 'nc' else app_state['dataframes'][df_name]['data'])

            ui_builder.update_saved_dfs_display(app_state, saved_dfs_placeholder, output_area)

        except Exception as err:
            print(f"Failed to fetch data: {err}")

# --- Handlers for Saving and Deleting DataFrames ---
def on_confirm_save_clicked(b, df_name, app_state, filename_input, output_area):
    filename = filename_input.value
    if not filename:
        with output_area:
            clear_output(); print("Error: Please provide a filename.")
        return

    try:
        data_to_save = app_state['dataframes'][df_name]['data']
        source_format = app_state['dataframes'][df_name]['source_format']
        if source_format == 'csv': data_to_save.to_csv(filename, index=False)
        elif source_format == 'parquet': data_to_save.to_parquet(filename)
        elif source_format == 'netcdf': data_to_save.to_netcdf(filename)
        
        b.description = "Saved!"; b.button_style = ''; b.disabled = True
        filename_input.disabled = True
    except Exception as e:
        with output_area:
            clear_output(); print(f"Failed to save file: {e}")

def on_save_requested(b, df_name, app_state, save_options_placeholder, output_area):
    save_options_placeholder.children = []
    source_format = app_state['dataframes'].get(df_name, {}).get('source_format', 'bin')
    default_filename = f"{df_name}.{source_format if source_format != 'bin' else 'nc'}"
    filename_input = widgets.Text(value=default_filename, description="Filename:", layout=widgets.Layout(width='auto'))
    confirm_button = widgets.Button(description="Confirm Save", button_style='primary')
    confirm_button.on_click(partial(on_confirm_save_clicked, df_name=df_name, app_state=app_state, filename_input=filename_input, output_area=output_area))
    save_options_placeholder.children = [widgets.HBox([filename_input, confirm_button])]

def on_delete_df_clicked(b, df_name, app_state, placeholder, output_area):
    from . import ui_builder
    if df_name in app_state['dataframes']:
        del app_state['dataframes'][df_name]
        ui_builder.update_saved_dfs_display(app_state, placeholder, output_area)
        with output_area:
            clear_output(); print(f"Object '{df_name}' removed from memory.")