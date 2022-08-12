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

import cv2
import geojson
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyproj
import requests
import xlrd
import xlsxwriter as xlw
from azure.storage.blob import (BlobClient, BlobServiceClient, ContainerClient,
                                __version__)
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
    self.connect_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

    # Get the blob service client
    self.blob_service_client = BlobServiceClient.from_connection_string(self.connect_str)
