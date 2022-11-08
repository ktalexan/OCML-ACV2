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


connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

blob_service = BlobServiceClient.from_connection_string(connection_string)

