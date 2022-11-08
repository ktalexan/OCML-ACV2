# Importing the required libraries into the project directory

import glob
import http.client
import io
import json
import math
import os
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import cv2
import geojson
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyproj
import requests
import xlrd
import xlsxwriter as xlw
from azure.storage.blob import (BlobClient, BlobServiceClient, ContainerClient,__version__)
from GPSPhoto import gpsphoto
from IPython.display import display
from pandas.io.json import json_normalize
from PIL import Image, ImageDraw, ImageFont
from pytz import timezone
from tqdm import tqdm

# Set the maximum number of http requests
http.client._MAXHEADERS = 10000


# Get the blob service client (see the development notes file for information on how to setup the connection string in the computer's environmental variables)
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

# Get the blob service client
blob_service = BlobServiceClient.from_connection_string(connection_string)

# Get the list of the parent (root) containers (albeit not to be used):
#container_list = {}
#allContainers = blobService.list_containers(include_metadata=True)
# for container in all_containers:
#    container_list[container["name"]] = container["metadata"]
# container_list

container_list = []
all_containers = blob_service.list_containers(include_metadata=False)
for container in all_containers:
    container_list.append(container.name)
container_list


# Working on the original photosphere data. Obtaining a list of virtual folders inside the original container:
if "originaldata" in container_list:
    vfolders_original = []
    vfolders_root = []

    container_client = ContainerClient.from_connection_string(connection_string, "originaldata")
    for c in container_client.walk_blobs():
        vfolders_original.append(c.name.split("/")[0])
        vfolders_root.append(c.name.split("/")[0].replace("_imagery", ""))
else:
    raise Exception("Original Blob Folder not in Containers List")


# Obtaining the list of original metadata for original data containers:
if "originaldata" in container_list:
    metadata_original = []
    container_client = ContainerClient.from_connection_string(connection_string, "originalmetadata")
    metadata_blob_list = container_client.list_blobs()
    for blob in metadata_blob_list:
        metadata_original.append(blob.name)
    print(metadata_original)
else:
    raise Exception("Original Blob Folder not in Containers List")


# Get the blob list for a given folder:
def get_blob_list(folder, type):
    blob_list = []
    if type == "original":
        generator = container_client.list_blobs(folder, prefix="originaldata/")
    elif type == "cardinal":
        generator = container_client.list_blobs(folder, prefix="cardinaldata/")
    elif type == "metadata":
        generator = container_client.list_blobs(folder, prefix="metadata/")
    for g in generator:
        blob_list.append(g.name)
    print(f"A total of {len(blob_list)} {type} data blobs added to the list for the {folder} container")
    return blob_list


# Loop through all the original subfolders, and add them to a python dictionary variable
for folder in vfolders_original:
    print(folder)

vfolder_blob_list = {}
for folder in vfolders_original:
    vfolder_blob_list[folder] = get_blob_list(folder, "original")


def CheckBlobMetadata():
    containerList = get_blob_list()


def GetBlobList(container_name=None):
    if container_name is None:
        container = self.container_name
    else:
        container = container_name
    blob_list = []
    generator = blobService.list_blobs(container)
