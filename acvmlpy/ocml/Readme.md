# OCML Class Development Notes

## Python Development Documentation

> ### OCML Class version Information

The current working _OCML_ class version is v.3.0.

</br>

> ### Instantiation Libraries Notes

##### Virtual Python Environment

This version introduced a virtual python environment (venv) associated with the project. While the environment itself is not included in the _Github_ repository distribution, the included [requirements.txt](../../requirements.txt) file was generated using the following command: `pip freeze > requirements.txt`

```python
   pip freeze > requirements.txt
```

In some instances, the python library _geojson_ does not work properly. It does not load even when it is installed via conda or pip.

There is an update similar package called _geopandas_ (see [here](https://anaconda.org/conda-forge/geopandas) for the package, and also [read the guide](https://geopandas.org/en/stable/docs/user_guide/io.html)).

##### New **azure-storage-blob** python library (v12 SDK)

* [Documentation](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python?tabs=environment-variable-windows)
* Storing and using credentials:
a. Copy Connection String from Azure portal (under Key1)
b. Using command line (windows), store the connection string as an environmental variable, after which restart programs.

    ```python
    setx AZURE_STORAGE_CONNECTION_STRING "<your connection string>"
    ```

  * Initiate the libraries:

  ```python
    import os, uuid
    from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, __version__
  ```

  * Obtain the connection string:

  ```python
    # Obtain the connection string
    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
  ```

  * Get the blob service client:

  ```python
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
  ```

  * Get the list of the parent (root) containers:

  ```python
    container_list = {}
    all_containers = blob_service_client.list_containers(include_metadata=True)
    for container in all_containers:
        container_list[container["name"]] = container["metadata"]
    container_list
  ```

  * Get the list of virtual folders (subcontainers) in the original data container:
  
  ```python
    original_vfolders = []
    container_client = ContainerClient.from_connection_string(connect_str, "originaldata")
    for c in container_client.walk_blobs():
        original_vfolders.append(c.name)
    original_vfolders
  ```
