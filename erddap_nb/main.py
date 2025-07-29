# erddap_nb/main.py

import ipywidgets as widgets
from IPython.display import display, clear_output
from functools import partial
from erddapy import servers 

def create_data_access_interface():
    """
    Creates a master interface that allows searching for datasets and then
    loading a full data exploration UI.
    """
    # --- WIDGETS ---
    server_list = {k: v.url for k, v in servers.items()}
    preset_options = ['--- Select a preset server ---'] + sorted(list(server_list.keys()))

    server_input = widgets.Text(
        placeholder='Select a preset or paste a custom URL',
        layout=widgets.Layout(width='400px')
    )
    server_presets_dd = widgets.Dropdown(
        options=preset_options,
        description="Search:",
        layout=widgets.Layout(width='auto')
    )
    
    search_mode_dd = widgets.Dropdown(
        options=['Keyword Search', 'Dataset ID'],
        value='Keyword Search',
        layout=widgets.Layout(width='150px')
    )
    search_query_input = widgets.Text(placeholder='e.g., temperature', layout=widgets.Layout(width='300px'))
    primary_button = widgets.Button(description="Search Datasets", button_style='primary')
    
    # Placeholders for dynamic content
    results_placeholder = widgets.VBox()
    explorer_placeholder = widgets.VBox()
    saved_dfs_placeholder = widgets.VBox() 
    output_area = widgets.Output()
    
    # Pagination widgets
    prev_button = widgets.Button(description="<< Prev", disabled=True)
    next_button = widgets.Button(description="Next >>", disabled=True)
    page_info_label = widgets.Label("")
    pagination_controls = widgets.HBox([prev_button, page_info_label, next_button], layout=widgets.Layout(justify_content='center'))
    pagination_controls.layout.display = 'none'

    # --- STATE MANAGEMENT ---
    app_state = {'search_page': 1, 'total_results': 0, 'dataframes': {}}
    ITEMS_PER_PAGE = 10
    
    # --- EVENT HANDLERS ---
    def on_server_select(change):
        """Populates the server URL text input when a preset is chosen."""
        server_name = change.get('new')
        if server_name in server_list:
            server_input.value = server_list[server_name]
            
    def load_dataset_explorer(dataset_id, button_obj=None):
        """Contains the logic to fetch metadata for one dataset and build the explorer UI."""
        from . import ui_builder
        from . import erddap_utils

        server = server_input.value
        with output_area:
            clear_output()
            results_placeholder.children = []
            pagination_controls.layout.display = 'none'
            print(f"Fetching metadata for {dataset_id}...")
            try:
                metadata = erddap_utils.get_dataset_metadata(server, dataset_id) #
                app_state['metadata'] = metadata
                protocol = metadata['protocol'] #
                
                # Display the determined protocol above the main explorer UI
                protocol_display = widgets.HTML(f"<h3><span style='color: #1E90FF;'>Protocol: {protocol.capitalize()}</span></h3>")
                
                builder_args = {
                    "metadata": metadata, "server": server, "dataset_id": dataset_id,
                    "output_area": output_area, "app_state": app_state, "saved_dfs_placeholder": saved_dfs_placeholder
                } #
                
                if protocol == 'griddap': #
                    ui = ui_builder.build_griddap_ui(**builder_args) #
                else:
                    ui = ui_builder.build_tabledap_ui(**builder_args) #
                
                explorer_placeholder.children = [protocol_display, ui]
                print(f"Success! Loaded explorer for {dataset_id}.")

            except Exception as e:
                print(f"Error fetching metadata for {dataset_id}: {e}")

    def run_keyword_search(b=None):
        """Handles the keyword search action and displays results."""
        from . import ui_builder
        from . import erddap_utils

        server = server_input.value
        query = search_query_input.value
        if not server or not query:
            with output_area:
                clear_output()
                print("Please provide a Server URL and a Search Query.")
            return

        with output_area:
            clear_output()
            explorer_placeholder.children = []
            print(f"Searching for '{query}' on {server}...")

            if app_state['search_page'] == 1:
                total = erddap_utils.get_total_count(server, query) #
                app_state['total_results'] = total
            
            total = app_state['total_results']
            results = erddap_utils.search_datasets(server, query, page=app_state['search_page'], items_per_page=ITEMS_PER_PAGE) #
            
            results_placeholder.children = [ui_builder.build_search_results(results, load_dataset_explorer)] #
            
            total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
            page_info_label.value = f"Page {app_state['search_page']} of {total_pages}"
            prev_button.disabled = (app_state['search_page'] <= 1)
            next_button.disabled = (app_state['search_page'] >= total_pages)
            pagination_controls.layout.display = 'flex' if total > 0 else 'none'
            print(f"Found {total} total datasets.")

    def on_prev_clicked(b):
        if app_state['search_page'] > 1:
            app_state['search_page'] -= 1
            run_keyword_search()

    def on_next_clicked(b):
        app_state['search_page'] += 1
        run_keyword_search()

    def on_primary_button_clicked(b):
        """Delegates action based on the selected search mode."""
        mode = search_mode_dd.value
        if mode == 'Keyword Search':
            app_state['search_page'] = 1
            run_keyword_search()
        elif mode == 'Dataset ID':
            dataset_id = search_query_input.value
            if not server_input.value or not dataset_id:
                with output_area:
                    clear_output()
                    print("Please provide a Server URL and a Dataset ID.")
                return
            load_dataset_explorer(dataset_id)

    def on_mode_change(change):
        """Updates the UI when the search mode changes."""
        new_mode = change.get('new')
        if new_mode == 'Keyword Search':
            primary_button.description = "Search Datasets"
            search_query_input.placeholder = 'e.g., temperature'
        elif new_mode == 'Dataset ID':
            primary_button.description = "Fetch Dataset"
            search_query_input.placeholder = 'Enter exact Dataset ID'
        
        results_placeholder.children = []
        explorer_placeholder.children = []
        pagination_controls.layout.display = 'none'

    # --- INITIAL LAYOUT & WIDGET EVENTS ---
    server_presets_dd.observe(on_server_select, names='value')
    primary_button.on_click(on_primary_button_clicked)
    prev_button.on_click(on_prev_clicked)
    next_button.on_click(on_next_clicked)
    search_mode_dd.observe(on_mode_change, names='value')

    search_bar = widgets.VBox([
        widgets.HBox([server_presets_dd, server_input, search_mode_dd, search_query_input, primary_button])
    ])
    
    display(widgets.VBox([
        search_bar,
        widgets.HTML("<hr>"),
        results_placeholder,
        pagination_controls,
        explorer_placeholder,
        saved_dfs_placeholder,
        output_area
    ]))
    
    return app_state