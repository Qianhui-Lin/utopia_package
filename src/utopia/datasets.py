from importlib import resources

def get_config_data():
    """Get path to example "default_config" [1]_ json file.

    Returns
    -------
    pathlib.PosixPath
        Path to file.

    
    """
    with resources.path("utopia.data", "default_config.json") as f:
        data_file_path = f
    return data_file_path

get_config_data()