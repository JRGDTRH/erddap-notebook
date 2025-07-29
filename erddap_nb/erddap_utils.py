# erddap_nb/erddap_utils.py

import pandas as pd
import re
from erddapy import ERDDAP
import urllib

def get_dataset_metadata(server_url: str, dataset_id: str) -> dict:
    """
    Fetches and parses the full dataset metadata from the info.csv endpoint.
    """
    e = ERDDAP(server=server_url)
    e.dataset_id = dataset_id
    info_url = e.get_info_url(response="csv")
    info_df = pd.read_csv(info_url)

    global_attrs_df = info_df[info_df["Variable Name"] == "NC_GLOBAL"]
    global_attrs = dict(zip(global_attrs_df["Attribute Name"], global_attrs_df["Value"]))
    cdm_type = global_attrs.get("cdm_data_type", "").lower()
    protocol = 'griddap' if cdm_type == 'grid' else 'tabledap'

    # Get dimension info first
    dims_df = info_df[info_df["Row Type"] == "dimension"]
    dimension_names = list(dims_df["Variable Name"].unique())
    dimensions = []
    for dim_name in dimension_names:
        dim_attrs_df = info_df[(info_df["Variable Name"] == dim_name) & (info_df["Row Type"] == "attribute")]
        dim_attrs = dict(zip(dim_attrs_df["Attribute Name"], dim_attrs_df["Value"]))
        
        spacing = "N/A"
        dim_row = dims_df[dims_df["Variable Name"] == dim_name].iloc[0]
        val_str = dim_row.get("Value", "")
        if "averageSpacing" in val_str:
            match = re.search(r"averageSpacing=([^,]+)", val_str)
            if match:
                spacing = match.group(1).strip()
        
        dimensions.append({
            'name': dim_name,
            'type': dim_attrs.get('type', 'string').lower(),
            'actual_range': dim_attrs.get("actual_range", "N/A"),
            'average_spacing': spacing,
            'units': dim_attrs.get("units"),
            'long_name': dim_attrs.get("long_name")
        })
        
    # Get data variable info (excluding dimensions)
    vars_df = info_df[info_df["Row Type"] == "variable"]
    data_variables = []
    for var_name in vars_df["Variable Name"].unique():
        if var_name in dimension_names: continue
        
        var_attrs_df = info_df[(info_df["Variable Name"] == var_name) & (info_df["Row Type"] == "attribute")]
        var_attrs = dict(zip(var_attrs_df["Attribute Name"], var_attrs_df["Value"]))
        
        data_variables.append({
            'name': var_name,
            'type': var_attrs.get('type', 'string').lower(),
            'actual_range': var_attrs.get("actual_range", "N/A"),
            'units': var_attrs.get("units"),
            'long_name': var_attrs.get("long_name")
        })

    # Create the map needed for the UI (contains everything)
    all_variables_map = {v['name']: v for v in data_variables + dimensions}

    return {
        "protocol": protocol,
        "data_variables": data_variables,
        "dimensions": dimensions,
        "all_variables_map": all_variables_map,
        "global_attrs": global_attrs
    }

def build_search_url(server, query, page=1, items_per_page=10, 
                     min_lon=None, max_lon=None, min_lat=None, max_lat=None,
                     min_time=None, max_time=None):
    """
    Build an ERDDAP advanced.csv search URL.
    """
    base_url = f"{server.rstrip('/')}/search/advanced.csv"
    params = [
        f"searchFor={urllib.parse.quote_plus(query)}",
        f"page={page}",
        f"itemsPerPage={items_per_page}",
        "protocol=(ANY)", "cdm_data_type=(ANY)", "institution=(ANY)", "ioos_category=(ANY)",
        "keywords=(ANY)", "long_name=(ANY)", "standard_name=(ANY)", "variableName=(ANY)",
        f"minLon={min_lon or ''}", f"maxLon={max_lon or ''}",
        f"minLat={min_lat or ''}", f"maxLat={max_lat or ''}",
        f"minTime={min_time or ''}", f"maxTime={max_time or ''}"
    ]
    query_string = "&".join(params)
    return f"{base_url}?{query_string}"


def search_datasets(server, query, page=1, items_per_page=10):
    """
    Fetch one page of search results as records. Returns a list of dictionaries.
    """
    url = build_search_url(server, query, page, items_per_page)
    try:
        df = pd.read_csv(url)
        # Standardize column names
        df.columns = [col.strip() for col in df.columns]
        rename_map = {
            "Dataset ID": "dataset_id", 
            "Title": "title", 
            "Institution": "institution"
        }
        df = df.rename(columns=rename_map)
        return df.to_dict(orient="records")
    except Exception:
        return []

def get_total_count(server, query):
    """
    Get total count by fetching a large page.
    """
    url = build_search_url(server, query, page=1, items_per_page=100000)
    try:
        df = pd.read_csv(url, comment='#')
        return len(df)
    except Exception:
        return 0