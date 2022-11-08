###########################################################
# AZURE COGNITIVE VISION: PHOTOSPHERE IMAGE ANALYSIS (v3) #
###########################################################


# ----------------------------#
# Preliminaries and Libraries #
#-----------------------------#

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
from re import L

import cv2
import geojson
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyproj
import requests
import xlrd
import xlsxwriter as xlw
from azure.storage.blob import (BlobClient, BlobServiceClient, ContainerClient, __version__)
from GPSPhoto import gpsphoto
from IPython.display import display
from pandas.io.json import json_normalize
from PIL import Image, ImageDraw, ImageFont
from pytz import timezone
from tqdm import tqdm

# Set maximum number of http requests
http.client._MAXHEADERS = 10000


#===================#
# MAIN CLASS: acvml #
#===================#

class acvml(object):

    """Class acvml:
    This class contains a number of functions, methods and processes for ML object classification analysis
    using the Azure Cognitive Services Computer Vision API.

    Global Attributes
        blobAccount: the name of the Azure blob storage account
        blobKey: the API key of the Azure blob storage account
        apiRegion: the azure region of the Azure Cognitive Services Computer Vision API (e.g., 'westus')
        apiKey: the Azure Cognitive Services Computer Vision API key (from azure)
        containerName: the base container name of the Azure blob storage account containing the photosphere images
    Example Class initialization:
        az = acvml(blobAccount, blobKey, apiRegion, apiKey, containerName)
    """

    #---------- CLASS INITIAlIZATION FUNCTION ----------#

    def __init__(self, )
    """Function Class initialization
        Returns an Azure Cognitive Services Computer Vision object (REST API)

        Attributes
            blobaccount:

        Returns
            Client: A ComputerVisionAPI object

        Notes
            This function runs on instantiation of class
        """

    # Get the blob services client (see development notes file for information on how to setup the connection string in the computer's environmental variables)
    self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

    # Get the blob service client
    self.blob_service = BlobServiceClient.from_connection_string(self.connection_string)

     # Get the list of the parent(root) containers
     self.container_list = []
      self.all_containers = self.blob_service.list_containers(include_metadata=False)
       for container in self.all_containers:
            self.container_list.append(container.name)

        # Working on the original photosphere data. Obtaining a list of virtual folders inside the original container:
        if "originaldata" in self.container_list:
            self.vfolders_original = []
            self.vfolders_root = []
            self.container_client = ContainerClient.from_connection_string(self.connection_string, "originaldata")
            for c in self.container_client.walk_blobs():
                self.vfolders_original.append(c.name.split("/")[0])
                self.vfolders_root.append(c.name.split("/")[0].replace("_imagery", ""))
        else:
            raise Exception("Original Blob Folder not in Containers List")

        # Obtaining the list of original metadata for original data containers:
        if "originaldata" in self.container_list:
            self.metadata_original = []
            self.container_client = ContainerClient.from_connection_string(self.connection_string, "originalmetadata")
            self.metadata_blob_list = self.container_client.list_blobs()
            for blob in self.metadata_blob_list:
                self.metadata_original.append(blob.name)
        else:
            raise Exception("Original Blob Folder not in Containers List")

        # Get the blob list for a given folder:
        def get_blob_list(folder, type):
            self.blob_list = []
            if type == "original":
                generator = self.container_client.list_blobs(folder, prefix="originaldata/")
            elif type == "cardinal":
                generator = self.container_client.list_blobs(folder, prefix="cardinaldata/")
            elif type == "metadata":
                generator = self.container_client.list_blobs(folder, prefix="metadata/")
            for g in generator:
                self.blob_list.append(g.name)
            print(f"A total of {len(self.blob_list)} {type} data blobs added to the list for the {folder} container")
            return self.blob_list

        # Loop through all the original subfolders, and add them to a python dictionary variable:
        for folder in self.vfolders_original:
            print(folder)

        self.vfolder_blob_list = {}
        for folder in self.vfolders_original:
            self.vfolder_blob_list[folder] = get_blob_list(folder, "original")

        def CheckBlobMetadata():
            self.containerList = get_blob_list().

        def GetBlobList(self.container_name=None):
            if self.container_name is None:
                self.container = self.container_name
            else:
                self.container = self_container_name
            self.blob_list = []
            generator = self.blobService.list_blobs(self.container)
