# ERDDAP Notebook

An interactive Jupyter/IPython widget for searching, exploring, and downloading data from any public ERDDAP server.

This tool provides a rich, user-friendly graphical interface directly within your notebook, streamlining the process of finding and accessing scientific datasets without having to write complex `erddapy` queries by hand. It automatically detects the dataset type (`griddap` or `tabledap`) and builds a tailored UI for subsetting and downloading the data.

Notes:

This served as a personal project to explore ipywidgets in jupyter notebooks. While it doesn't have every single feature available through web access, it streamlines and contains the notable features, such as, searching, graphing, and data downloading. Think of it as an ERDDAP-lite in a notebook environment.

Known Bugs/Issues:

It's hard to account for every variations between data types/servers etc... and preferred syntax in the URL requests when using constraints. Thus, some data downloads may result in errors (400, 404, 500, etc...). For example, CSV in griddap and tabledap requests seem reliable, Parquet requests with tabledap may throw errors between servers. There are just too many servers/datasets to test and troubleshoot for.

Visual errors appear in graphs when using the full range of selected variables, this is due to the logic for applying constraints to variables, if the full range of values is used, it does not apply to the URL request, for brevity. Something about this logic impacts the visuals of the graph. Slightly adjust the min/max values to fix this.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

<img width="1407" height="821" alt="image" src="https://github.com/user-attachments/assets/e189cc2a-5d81-4753-a909-6ddb493442ca" />

<img width="1472" height="572" alt="image" src="https://github.com/user-attachments/assets/6834ef0c-9e2b-4453-97dc-02b1c32a7992" />

---

## Features

*   **Server Discovery**: Includes a pre-populated list of common ERDDAP servers from erddapy and the ability to use any custom server URL.
*   **Powerful Search**:
    *   Search for datasets in a specific server using keywords.
    *   Fetch a dataset directly by its `Dataset ID`.
    *   Paginated results for easy browsing.
*   **Intelligent UI Generation**:
    *   Automatically detects whether a dataset is `griddap` (grid-based) or `tabledap` (tabular).
    *   Builds a specific user interface tailored to the dataset's variables and dimensions.
*   **Interactive Subsetting and Filtering**:
    *   For `griddap` datasets: Use sliders and text inputs to define dimension ranges (latitude, longitude, time, etc.).
    *   For `tabledap` datasets: Use dropdowns and text inputs to build complex filter queries on any variable (e.g., `time >= '2020-01-01'`, `sea_surface_temperature < 15`, `station_id = 'station_A'`).
*   **In-Notebook Visualization**: Generate quick-look plots (surface, lines, markers) of your selected data and constraints without having to download it first.
*   **Flexible Downloading**:
    *   Download data directly into memory as a Pandas DataFrame or an Xarray Dataset.
    *   Provides download links for other common file formats (`.json`, `.nc`, `.geotiff`, etc.).
*   **In-Memory Data Management**:
    *   View all in-memory DataFrames and Datasets downloaded during your session.
    *   Save any object from memory to a local file (`.csv`, `.parquet`, `.nc`).
    *   Delete objects from memory to free up resources.

## Requirements

The tool is built on the standard scientific Python stack. You can install all dependencies using pip:

```bash
pip install erddapy pandas xarray ipywidgets requests netCDF4 pyarrow
```
It is recommended to run this tool in a Jupyter Notebook or JupyterLab environment to ensure the `ipywidgets` render correctly.

## Installation

1.  Clone this repository to your local machine.

## Quick Start

Using the ERDDAP Explorer is designed to be as simple as possible. The following cells demonstrate the ideal workflow in a Jupyter Notebook.

**1. Launch the ERDDAP Notebook**

This cell imports and runs the interface. The UI will appear below the cell once executed. Template ipynb provided in repository.

```python
# Import the main function from the erddap_nb package
from erddap_nb import create_data_access_interface

# Run the function to display the UI. 
# The 'app' variable will hold the application's state, including any data you download.
app = create_data_access_interface()
```

*(After running the cell above, use the UI to find and download a dataset. The following cell shows you how to access the data you've saved to memory.)*

**2. Access and Analyze Your Downloaded Data**

Once you have downloaded data using the UI, you can access it programmatically from the `app` object.

```python
# Check if any dataframes have been downloaded yet
import pandas as pd

if not app['dataframes']:
    print("No data has been downloaded yet. Please use the UI above to download a dataset.")
else:
    # See all available in-memory data objects (DataFrames or Datasets)
    print("Available data keys:", list(app['dataframes'].keys()))
    
    # --- IMPORTANT ---
    # Replace 'your_data_key_here' with the actual key from the list printed above.
    data_key = 'your_data_key_here' 
    
    # Safely access your data
    if data_key in app['dataframes']:
        # The 'data' item holds your object (e.g., a Pandas DataFrame)
        data_object = app['dataframes'][data_key]['data']
        source_format = app['dataframes'][data_key]['source_format']
        
        print(f"\nSuccessfully accessed '{data_key}' (format: {source_format}).")

        # Display the first few rows for DataFrames
        if isinstance(data_object, pd.DataFrame):
            print("\n--- Data Head ---")
            display(data_object.head())
            print("\n--- Summary Statistics ---")
            display(data_object.describe())
        else:
            # Display the Xarray object
            display(data_object)
            
    else:
        print(f"\nError: The key '{data_key}' was not found. Please choose a valid key from the list above.")
```

## Project Structure

*   `main.py`: Contains the primary entry point (`create_data_access_interface`) and manages the top-level application state and layout.
*   `erddap_utils.py`: A set of helper functions for interacting with the ERDDAP REST API (searching, fetching metadata).
*   `ui_builder.py`: Responsible for dynamically constructing the `griddap` and `tabledap` `ipywidgets` interfaces based on dataset metadata.
*   `event_handlers.py`: Contains all the callback functions that give the UI its interactivity (e.g., what happens when a button is clicked).

## Contributing

Contributions are welcome! If you have ideas for improvements or find a bug, please feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
