######################################################
# AZURE COGNITIVE VISION: PHOTOSPHERE IMAGE ANALYSIS #
######################################################


# ----------------------------#
# Preliminaries and Libraries #
#-----------------------------#

import glob
import http.client
import io
import json
import math
# Importing the required libraries into the project
import os
import time
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
from azure.storage.blob import BlockBlobService
from GPSPhoto import gpsphoto
#from tqdm.auto import tqdm
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

    def __init__(self, blobAccount, blobKey, apiRegion, apiKey, containerName, metadata):
        """Function Class Initialization
        Returns an Azure Cognitive Services Computer Vision object (REST API) using a region and key.

        Attributes
            blobAccount: the name of the Azure blob storage account
            blobKey: the API key of the Azure blob storage account
            apiRegion: the azure region of the Azure Cognitive Services Computer Vision API (e.g., 'westus')
            apiKey: the Azure Cognitive Services Computer Vision API key (from azure)
            containerName: the base container name of the Azure blob storage account containing the photosphere images

        Returns
            client: A ComputerVisionAPI object

        Notes
            This function runs on instantiation of class
        """

        # Setup account and key for the Azure blob storage, containing the photosphere images
        self.blobAccount = blobAccount
        self.blobKey = blobKey
        self.blobService = BlockBlobService(self.blobAccount, self.blobKey)

        # Setup region and key for the Azure vision client API
        self.apiRegion = apiRegion
        self.subscriptionKey = apiKey
        assert self.subscriptionKey

        # Setup base URL for Azure Cognitive Services Computer vision
        self.visionBaseUrl = 'https://{}.api.cognitive.microsoft.com/vision/v2.0/'.format(self.apiRegion)

        # Setup the global headers configuration
        self.headers = {'Ocp-Apim-Subscription-Key': self.subscriptionKey, 'Content-Type': 'application/octet-stream'}

        # Setup the Azure blob container name
        self.containerName = containerName
        self.metadata = metadata
        self.cardinalName = '{}-cardinal'.format(containerName)
        self.blobBaseUrl = 'https://{}.blob.core.windows.net'.format(self.blobAccount)
        self.blobBaseUrl_photospheres = '{}/{}'.format(self.blobBaseUrl, self.containerName)
        self.blobBaseUrl_cardinal = '{}/{}'.format(self.blobBaseUrl, self.cardinalName)

        # Get Dataset Info
        AnaheimList = ['anaheim2018337p1', 'anaheim2018338p1', 'anaheim2018ee8p2']
        NTustinList = ['ntustin2019088p2', 'ntustin2019089p1', 'ntustin2019090p1', 'ntustin2019090p2', 'ntustin2019090p3',
                       'ntustin2019091p1', 'ntustin2019091p2', 'ntustin2019092p1', 'ntustin2019093p1']
        self.collectionArea = 'None'
        self.datasetID = 0

        for i, a in enumerate(AnaheimList, start=1):
            if a in self.containerName:
                self.collectionArea = 'Anaheim'
                self.datasetID = i

        for i, a in enumerate(NTustinList, start=4):
            if a in self.containerName:
                self.collectionArea = 'North Tustin'
                self.datasetID = i
        return

    #========================================================================#
    # PRELIMINARY DATA TRANSFORMATION FUNCTIONS (NEEDED FOR OTHER FUNCTIONS) #
    #========================================================================#

    #---------- Class Function: CheckDegrees ----------#

    def CheckDegrees(self, x, y):
        """Checks and obtains degrees based on addition
        This function cycles degrees from 0 to 360 based on mathematical addition.
        Given an initial starting degree (x), we calculate the sum between x and y.
        If x + y exceeds 360 degrees, the function resets the value to accomodate radial consistency.

        Arguments
            x: initial (starting) degrees
            y: degrees to be added.

        Output
            sumdeg: returns the sum of degrees between 0 and 360
        """

        sumdeg = x + y
        if sumdeg > 360:
            sumdeg = sumdeg - 360

        return sumdeg

    #---------- Class Function: CheckCardinality ----------#

    def CheckCardinality(self, value):
        """Returns a cardinal direction from a dictionary
        This function checks a direction value (in degrees) against a cardinal direction dictionary.
        It returns a cardinal direction class in which the direction value belongs to.

        Arguments
            value: the direction value in degrees

        Output
            direction: the cardinal direction class label.
        """

        # Defining a cardinal directions dictionary to be used in the next function
        cardinalDictionary = {
            'N0': [0, 5.625], 'NbE': [5.625, 16.875], 'NNE': [16.875, 28.125],
            'NEbN': [28.125, 39.375], 'NE': [39.375, 50.625], 'NEbE': [50.625, 61.875],
            'ENE': [61.875, 73.125], 'EbN': [73.125, 84.375], 'E': [84.375, 95.625],
            'EbS': [95.625, 106.875], 'ESE': [106.875, 118.125], 'SEbE': [118.125, 129.375],
            'SE': [129.375, 140.625], 'SEbS': [140.625, 151.875], 'SSE': [151.875, 163.125],
            'SbE': [163.125, 174.375], 'S': [174.375, 185.625], 'SbW': [185.625, 196.875],
            'SSW': [196.875, 208.125], 'SWbS': [208.125, 219.375], 'SW': [219.375, 230.625],
            'SWbW': [230.625, 241.875], 'WSW': [241.875, 253.125], 'WbS': [253.125, 264.375],
            'W': [264.375, 275.625], 'WbN': [275.625, 286.875], 'WNW': [286.875, 298.125],
            'NWbW': [298.125, 309.375], 'NW': [309.375, 320.625], 'NWbN': [320.625, 331.875],
            'NNW': [331.875, 343.125], 'NbW': [343.125, 354.375], 'N1': [354.375, 360.000001]
        }

        # Loop direction ranges to find the appropriate range
        for direction in cardinalDictionary:
            if cardinalDictionary[direction][0] <= round(value, 3) < cardinalDictionary[direction][1]:
                if direction == 'N0' or direction == 'N1':
                    cardinalDir = 'N'
                else:
                    cardinalDir = direction

        return cardinalDir

    #---------- Class Function: GetDirection ----------#

    def GetDirection(self, x, y):
        """Calculates direction from State Plane coordinates
        This function calculates the direction (angle in degrees) from Easting and Northing
        coordinates expressed in State Plane, California Zone 6 (NAD84) system.

        Arguments
            x: Easting coordinate value in NAD84
            y: Northing coordinate value in NAD84

        Output
            degout: direction in degrees (always positive, reverses if negative)
        """

        deg = math.degrees(math.atan2(x, y))
        degout = deg

        if deg < 0:
            degout = (deg + 360) % 360

        return degout

    #---------- Class Function: ConvertStatePlane ----------#

    def ConvertStatePlane(self, xin, yin, zin):
        """Converts State Plane coordinates (NAD84) to Lat Lon degrees (WGS84)
        This function converts coordinates from State Plane coordinate system, CA zone 6 (NAD84, espg:2230)
        to default ESRI and ArcGIS online Lat-Lon degrees (WGS84, espg:4326)

        Arguments
            xin: Easting coordinates in NAD84
            yin: Northing coordinates in NAD84
            zin: Elevation coordinates in NAD84

        Output
            xout: Longitude coordinates in WGS84
            yout: Latitude coordinates in WGS84
            zout: Elevation coordinates in WGS84
        """

        # Setting preserve_units as True ensures we preserve the original coordinate units in feet.
        inProj = pyproj.Proj(init='epsg:2230', preserve_units=True)
        outProj = pyproj.Proj(init='epsg:4326')
        xout, yout, zout = pyproj.transform(inProj, outProj, xin, yin, zin)

        return (xout, yout, zout)

    #---------- Class Function: TimestampConvert ----------#

    def TimestampConvert(self, imgname, timestamp):
        """Converts image timestamp string to native datetime format
        This function takes as input the string timestamps from metadata and converts them
        to a native datetime format. The results are used in the json formatting where they
        are converted to different strings.

        Arguments
            imgname: the name of the image to be converted
            timestamp: the string timestamp input to be converted

        Output
            dtobjpst: a datetime object (PST)
        """

        # Take the initial input string and split it into components
        namesplit = imgname.split('_')[0]
        # The 4-digit year part
        YYYY = '20' + namesplit[:2]
        # The 2-digit month part
        MM = namesplit[2:4]
        # The 2-digit month day part
        DD = namesplit[4:]
        # The day of the week
        day = timestamp / 86400
        # The hours, minutes, seconds, and mili-seconds parts
        hours = Decimal(str(day)) % 1 * 86400 / 3600
        minutes = Decimal(str(hours)) % 1 * 3600 / 60
        seconds = Decimal(str(minutes)) % 1 * 60
        msecs = Decimal(str(seconds)) % 1 * 10
        hh, mm, ss, s = int(hours), int(minutes), int(seconds), int(msecs)

        # Construct the new datetime object (UTC)
        dtobj = datetime(int(YYYY), int(MM), int(DD), int(hh), int(mm), int(ss), 100000*int(s))
        dtobjutc = dtobj.replace(tzinfo=timezone('UTC'))
        dtobjpst = dtobjutc.astimezone(timezone('US/Pacific'))

        return dtobjpst

    #---------- Class Function: CheckBlobContainer ----------#

    def CheckBlobContainer(self, containerName=None, create=True, publicAccess='blob'):
        """Check for the presence of a blob container in the account
        This function checks the Azure storage account whether or not a blob container (folder) exists or not.
        If the container exists, the program makes sure the publicAccess is set to the value of the function.
        If the container does not exist, if create=True, then the folder is created and publicAccess is set.
        If the container does not exist, and create=False (default), nothing is done.

        Arguments
            containerName: the name of the blob container (folder) to be checked (optional, otherwise it checks the main)
            create (=False by default): whether or not to create a new container if it doesn't exist.
            publicAccess (='blob' by default): level of public access to URL ('blob', 'container', etc)

        Returns
            Nothing. Performs operations in Microsoft Azure Storage on the cloud.
        """

        # Check if the container is provided:
        if containerName is None:
            container = self.containerName  # if empty, revert to the default class container
        else:
            container = containerName

        # Check if the container exist:
        if self.blobService.exists(container):
            # Making sure it has public blob-only access
            self.blobService.set_container_acl(container, public_access=publicAccess)
            print('Container {} exists. Public access is set to {}'.format(container, publicAccess))
        elif create == True:
            # If the user indicated that create argument is true, then create a new container
            self.blobService.create_container(container, public_access=publicAccess)
            assert self.blobService.exists(container)
            print('Container {} does not exist. A new container is created with public_access set to {}'.format(container, publicAccess))
        else:
            # Just exits otherwise
            print('Container {} does not exist. No changes are requested. Program is exiting.')

        return

    #---------- Class Function: CheckBlobMetadata ----------#

    def CheckBlobMetadata(self):
        """Checks the metadata of the blob container
        This function checks and ensures that the original metadata in the excel file corresponds exactly
        to the photospheres contained in the blob container (matching them, image-by-image).

        Arguments
            None. Uses the default container of the class initialization

        Output
            Just a statement containing how many photospheres are matched.
        """
        # Obtain the list of blobs in the container
        containerList = self.get_blob_list()
        # Check if the blob container exists, and it has the right permissions
        self.CheckBlobContainer(self.containerName)
        noImg = len(containerList)  # Total number of images in blob container
        j = 0

        # Get the excel metadata from the first excel sheet
        if self.metadata is not None:
            xlMetadata = pd.read_excel(self.metadata, sheet_name=0)
            # Do the matching
            for i, img in enumerate(tqdm(containerList)):
                imgName = img.name
                xlMetaImg = xlMetadata.loc[xlMetadata['Filename'] == imgName].iloc[0]['Filename']
                if imgName == xlMetaImg:
                    j += 1

        print('Matched {} out of {} images in container'.format(j, noImg))

        return

    #=======================================#
    # PHOTOSPHERE IMAGE OPERATION FUNCTIONS #
    #=======================================#

    #---------- Class Function: GetBlobList ----------#

    def GetBlobList(self, containerName=None):
        """List all blobs in Azure storage blob
        This function gets a list of all files in an Azure storage blob (by container folder name)

        Arguments
            containerName (optional): 
                if containerName is None: Uses the Azure storage blob container name (from class initialization)
                if containerName is not None: Uses the defined Azure storage blob container

        Output
            blobList: the list of all files in the container
        """

        # List the blobs in the container (from class initialization)
        if containerName is None:
            container = self.containerName
        else:
            container = containerName

        blobList = []
        generator = self.blobService.list_blobs(container)

        for blob in generator:
            blobList.append(blob)

        print('Blob list for container {} created with {} blobs'.format(container, len(blobList)))

        return blobList

    #---------- Class Function: GetObjectBounds ----------#

    def GetObjectBounds(self, jsonstring):
        """Get detected object bounds from bounding box coordinates
        This function returns bounding coordinates for an object in detected Azure cognitive vision
        json string.

        Arguments
            jsonstring: the json detection response containing the object

        Output
            bounds: the set of bounds expressed in bounding box coordinates (x, y, w, h)
        """

        bounds = []
        nobj = jsonstring['NumberOfObjects']

        # Loop for every object and append the bounds list
        for i in range(0, nobj):
            bounds.append({
                'object': jsonstring['Object{}'.format(i+1)],
                'vertices': [
                    {'x': jsonstring['x{}'.format(i+1)]},
                    {'y': jsonstring['y{}'.format(i+1)]},
                    {'w': jsonstring['w{}'.format(i+1)]},
                    {'h': jsonstring['h{}'.format(i+1)]}]
            })

        return bounds

    #---------- Class Function: DrawBoundingBoxes ----------#

    def DrawBoundingBoxes(self, image, bounds):
        """Draws annotation boxes in image
        This function uses the bound coordinates to draw annotation boxes around photosphere images

        Arguments
            image: the photosphere image to be annotated (cardinal)
            bounds: the bounding box coordinates of the detected objects

        Output
            image: the annotated image
        """

        # Instantiate an ImageDraw object to draw the annotations
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('arial.ttf', 18)

        # Loop through the bounds list (from the get_object_bounds function) and draw the bounds as rectangles with annotations
        for bound in bounds:
            draw.rectangle([
                bound['vertices'][0]['x'],
                bound['vertices'][1]['y'],
                bound['vertices'][0]['x'] + bound['vertices'][2]['w'],
                bound['vertices'][1]['y'] + bound['vertices'][3]['h']
            ], None, 'red')
            draw.text((bound['vertices'][0]['x'] + 5, bound['vertices'][1]['y'] + 5),
                      bound['object'], fill='red', font=font)

        return image

    #---------- Class Function: WriteJSONFile ----------#

    def WriteJSONFile(self, name, data):
        """Writes detection output into a jsonfile
        This function outputs the processed results of the Azure cognitive vision detection process
        into a json file.

        Arguments
            name: the name of the json file to be saved
            data: the json string response data to be included

        Output
            Nothing, the json file is saved using the name provided
        """

        filename = name + '.json'
        with open(filename, 'w') as fp:
            json.dump(data, fp)

        return

    #=========================================================================#
    # MAIN FEATURE FUNCTIONS FOR IMAGE PROCESSING AND CLASSIFICATION ANALYSIS #
    #=========================================================================#

    #---------- Class Function: UpdateBlobMetadata ----------#

    def UpdateBlobMetadata(self):
        """Uploads and updates blob metadata from excel file metadata
        This function will upload and update the blob metadata, based on
        the metadata file stored in image.

        Arguments
            metadatafile: the metadata filename

        Output
            Nothing; performs operation in the blob container
        """

        try:
            # Obtain the blob list of the container
            containerList = self.GetBlobList()
            # Check the container and it's permissions
            self.CheckBlobContainer(self.containerName)
            noImg = len(containerList)  # number of images in blob list
            print('Number of blobs in container: {}'.format(noImg))

            # Get the metadata from the excel table
            if self.metadata is not None:
                xlMetadata = pd.read_excel(self.metadata, sheet_name=0)

                # Assign and extract the data variables
                for i, img in enumerate(tqdm(containerList)):
                    imgName = img.name
                    xlMetaImg = xlMetadata.loc[xlMetadata['Filename'] == imgName]
                    xlcols = xlMetaImg.iloc[0]

                    # Convert the State Plane to Lat-Lon coordinates
                    lon, lat, alt = self.ConvertStatePlane(
                        xlcols['OriginEasting'],
                        xlcols['OriginNorthing'],
                        xlcols['OriginHeight']
                    )
                    # GPS sensor in the middle of the photosphere
                    dirsensor = self.GetDirection(xlcols['DirectionEasting'], xlcols['DirectionNorthing'])
                    # Get the direction from the edge of the photosphere (adding 180 degrees)
                    dirmov = self.CheckDegrees(dirsensor, 180)

                    # Create an empty json string to hold the image metadata
                    jsonimg = {}
                    jsonimg['DatasetName'] = self.containerName
                    jsonimg['DatasetID'] = self.datasetID
                    jsonimg['CollectionArea'] = self.collectionArea
                    jsonimg['PhotosphereImageName'] = xlcols['Filename']
                    imgdt = self.TimestampConvert(xlcols['Filename'], xlcols['Timestamp'])
                    jsonimg['DateTimeDisplay'] = imgdt.strftime('%m/%d/%Y %H:%M:%S.%f').rstrip('0')
                    jsonimg['DateTimeString'] = imgdt.strftime('%Y%m%d%H%M%S.%f').rstrip('0')
                    jsonimg['PhotosphereResolution'] = '8000 x 4000'
                    jsonimg['PhotosphereURL'] = '{}/{}'.format(self.blobBaseUrl_photospheres, xlcols['Filename'])
                    jsonimg['GooglePhotosphere'] = 'https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={},{}&heading={}'.format(str(lat), str(lon), str(dirmov))
                    jsonimg['Longitude'] = lon
                    jsonimg['Latitude'] = lat
                    jsonimg['Altitude'] = alt
                    jsonimg['Direction'] = dirmov
                    jsonimg['Easting'] = xlcols['OriginEasting']
                    jsonimg['Northing'] = xlcols['OriginNorthing']
                    jsonimg['Height'] = xlcols['OriginHeight']
                    jsonimg['DirectionEasting'] = xlcols['DirectionEasting']
                    jsonimg['DirectionNorthing'] = xlcols['DirectionNorthing']
                    jsonimg['DirectionHeight'] = xlcols['DirectionHeight']
                    jsonimg['UpEasting'] = xlcols['UpEasting']
                    jsonimg['UpNorthing'] = xlcols['UpNorthing']
                    jsonimg['UpHeight'] = xlcols['UpHeight']
                    jsonimg['Roll'] = xlcols['Roll']
                    jsonimg['Pitch'] = xlcols['Pitch']
                    jsonimg['Yaw'] = xlcols['Yaw']
                    jsonimg['Omega'] = xlcols['Omega']
                    jsonimg['Phi'] = xlcols['Phi']
                    jsonimg['Kappa'] = xlcols['Kappa']

                    # populate the metadata dictionary
                    metastring = {}
                    for key in jsonimg.keys():
                        metastring[key] = str(jsonimg[key])

                    # Set the metadata dictionary as the Azure blob image's metadata
                    self.blobService.set_blob_metadata(self.containerName, imgName, metastring)

            return

        except Exception as ex:
            print(ex.args[0])

    #---------- Class Function: ProcessCardinalImages ----------#

    def ProcessCardinalImages(self, blob):
        """Processes cardinal images from original photospheres
        This function crops and obtains 8 cardinal images (1000 x 1000) from the original photospheres,
        by cropping a region between 1550 and 2550 pixels, i.e., from (x1 = 0, y1 = 1550) to (x2 = 8000, 
        y2 = 2550) vertically. The function returns a list with 8 cardinal images, from left to right, 
        each image covering a 45 degrees vision span.

        Arguments
            blob: the blob object (photosphere image) to be processed
            containerIn: the name of the blob storage container containing the blob
            containerOut: the name of the blob storage container for the cardinal images to be saved

        Output
            Nothing; the results are processed and saved in containerOut storage blob.
        """

        try:

            imageName = blob.name

            # Getting the photosphere image metadata
            metaString = {}

            if self.blobService.get_blob_metadata(self.containerName, imageName) is not {}:
                metaString = self.blobService.get_blob_metadata(self.containerName, imageName)
                fields = ['Direction', 'Longitude', 'Latitude', 'Altitude', 'Easting',
                          'Northing', 'Height', 'DirectionEasting', 'DirectionNorthing',
                          'DirectionHeight', 'UpEasting', 'UpNorthing', 'UpHeight', 'Roll',
                          'Pitch', 'Yaw', 'Omega', 'Phi', 'Kappa']

                for field in fields:
                    metaString[field] = float(metaString[field])

                # Getting the photosphere image from azure blob storage and convert it to bytes
                content = self.blobService.get_blob_to_bytes(self.containerName, imageName).content
                img = Image.open(io.BytesIO(content))

                # Creating the areas of the cardinal images
                areas = []
                step = 1000
                for i in range(0, 8000, step):
                    coor = (i, 1550, i+step, 2550)
                    areas.append(coor)

                # This is the loop for the 8 cardinal areas
                for ncard, area in enumerate(areas):
                    cmeta = {}
                    cmeta = metaString
                    cardinalImg = img.crop(area)
                    cardinalArray = io.BytesIO()
                    cardinalImg.save(cardinalArray, format='JPEG')
                    cardinalArray = cardinalArray.getvalue()
                    cardinalDir = self.CheckDegrees(cmeta['Direction'], 22.5)
                    cardinalDir = self.CheckDegrees(cardinalDir, ncard * 45.0)
                    cardinalLabel = self.CheckCardinality(cardinalDir)
                    cardinalImgName = '{}_{}_{}.jpg'.format(imageName.split('.jpg')[0], ncard + 1, cardinalLabel)
                    cmeta['CardinalImageName'] = cardinalImgName
                    cmeta['CardinalImageURL'] = '{}/{}'.format(self.blobBaseUrl_cardinal, cardinalImgName)
                    cmeta['GoogleCardinal'] = 'https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={},{}&heading={}'.format(str(cmeta['Latitude']), str(cmeta['Longitude']), str(cardinalDir))
                    cmeta['CardinalNumber'] = ncard + 1
                    cmeta['CardinalDirection'] = cardinalDir
                    cmeta['CardinalDirectionLabel'] = cardinalLabel

                    # Set up the Computer Vision analysis parameter
                    url = self.visionBaseUrl + 'analyze'
                    headers = self.headers
                    params = {"visualFeatures": "Categories,Tags,Description,ImageType,Color,Objects"}
                    response = requests.post(url, headers=headers, params=params, data=cardinalArray)
                    response.raise_for_status()
                    responsejson = response.json()

                    # Create and populate json response captions fields
                    if 'captions' in responsejson['description']:
                        if responsejson['description']['captions']:
                            cmeta['Caption'] = responsejson['description']['captions'][0]['text']
                            cmeta['CaptionConfidence'] = responsejson['description']['captions'][0]['confidence']

                    # Create and populate json response metadata fields
                    if 'metadata' in responsejson:
                        cmeta['ImageWidth'] = responsejson['metadata']['width']
                        cmeta['ImageHeight'] = responsejson['metadata']['height']
                        cmeta['ImageFormat'] = responsejson['metadata']['format']
                    if 'imageType' in responsejson:
                        cmeta['ClipArtType'] = responsejson['imageType']['clipArtType']
                        cmeta['LineDrawingType'] = responsejson['imageType']['lineDrawingType']
                    if 'color' in responsejson:
                        cmeta['DominantColorForeground'] = responsejson['color']['dominantColorForeground']
                        cmeta['DominantColorBackground'] = responsejson['color']['dominantColorBackground']
                        if len(responsejson['color']['dominantColors']) > 1:
                            cmeta['DominantColors'] = ','.join(responsejson['color']['dominantColors'])
                        elif len(responsejson['color']['dominantColors']) == 1:
                            cmeta['DominantColors'] = responsejson['color']['dominantColors'][0]
                        elif responsejson['color']['dominantColors'] is None:
                            cmeta['DominantColors'] = ''

                    # Create and populate json response number of categories fields
                    if 'categories' in responsejson:
                        lcat = len(responsejson['categories'])
                        cmeta['NumberOfCategories'] = lcat
                        for ncat, obj in enumerate(responsejson['categories']):
                            for cat in obj:
                                catName = 'Category{}{}'.format(cat.capitalize(), str(ncat + 1))
                                cmeta[catName] = obj[cat]

                    # Populate the tags fields from the cognitive vision response
                    if 'tags' in responsejson:
                        ltags = len(responsejson['tags'])
                        cmeta['NumberOfTags'] = ltags
                        for ntag, obj in enumerate(responsejson['tags']):
                            cmeta['TagName{}'.format(str(ntag + 1))] = obj['name']
                            cmeta['TagConfidence{}'.format(str(ntag + 1))] = obj['confidence']
                            for tag in obj:
                                tagName = 'Tag{}{}'.format(tag.capitalize(), str(ntag + 1))
                                cmeta[tagName] = obj[tag]
                    if 'tags' in responsejson['description']:
                        dtagsjoin = ','.join(responsejson['description']['tags'])
                        if dtagsjoin:
                            cmeta['DescriptionTags'] = dtagsjoin

                    # Populate the objects fields from the cognitive vision response
                    if 'objects' in responsejson:
                        lobj = len(responsejson['objects'])
                        cmeta['NumberOfObjects'] = lobj
                        for nobj, obj in enumerate(responsejson['objects']):
                            centerX = obj['rectangle']['x'] + (obj['rectangle']['w'] / 2)
                            centerY = obj['rectangle']['y'] + (obj['rectangle']['h'] / 2)
                            centerDir = cardinalDir - 22.5 + (centerX * 0.045)
                            cmeta['Object{}'.format(nobj + 1)] = obj['object']
                            cmeta['Object{}Confidence'.format(nobj + 1)] = obj['confidence']
                            cmeta['Object{}Direction'.format(nobj + 1)] = centerDir
                            cmeta['Object{}Longitude'.format(nobj + 1)] = 0.00
                            cmeta['Object{}Latitude'.format(nobj + 1)] = 0.00
                            cmeta['x{}'.format(nobj + 1)] = obj['rectangle']['x']
                            cmeta['y{}'.format(nobj + 1)] = obj['rectangle']['y']
                            cmeta['w{}'.format(nobj + 1)] = obj['rectangle']['w']
                            cmeta['h{}'.format(nobj + 1)] = obj['rectangle']['h']
                            cmeta['cx{}'.format(nobj + 1)] = centerX
                            cmeta['cy{}'.format(nobj + 1)] = centerY
                            if 'parent' in obj:
                                lpar = len(obj['parent'])
                                if lpar == 0:
                                    nparents = 0
                                else:
                                    nparents = lpar - 1
                                    k = 1
                                    cmeta['Object{}Parent{}'.format(nobj + 1, k)] = obj['parent']['object']
                                    cmeta['Object{}Parent{}Confidence'.format(nobj + 1, k)] = obj['parent']['confidence']
                                    if 'parent' in obj['parent']:
                                        k += 1
                                        cmeta['Object{}Parent{}'.format(nobj + 1, k)] = obj['parent']['parent']['object']
                                        cmeta['Object{}Parent{}Confidence'.format(nobj + 1, k)] = obj['parent']['parent']['confidence']
                                        if 'parent' in obj['parent']['parent']:
                                            k += 1
                                            cmeta['Object{}Parent{}'.format(nobj + 1, k)] = obj['parent']['parent']['parent']['object']
                                            cmeta['Object{}Parent{}Confidence'.format(nobj + 1, k)] = obj['parent']['parent']['parent']['confidence']
                                            if 'parent' in obj['parent']['parent']['parent']:
                                                k += 1
                                                cmeta['Object{}Parent_{}'.format(nobj + 1, k)] = obj['parent']['parent']['parent']['parent']['object']
                                                cmeta['Object{}Parent{}Confidence'.format(nobj + 1, k)] = obj['parent']['parent']['parent']['parent']['confidence']

                    bounds = self.GetObjectBounds(cmeta)
                    taggedImg = self.DrawBoundingBoxes(cardinalImg, bounds)
                    taggedArray = io.BytesIO()
                    taggedImg.save(taggedArray, format='JPEG')
                    taggedArray = taggedArray.getvalue()

                    cardinalMetaBlob = {}
                    for key in cmeta.keys():
                        cardinalMetaBlob[key] = str(cmeta[key])

                    self.blobService.create_blob_from_bytes(
                        container_name=self.cardinalName,
                        blob_name=cardinalImgName,
                        blob=taggedArray,
                        metadata=cardinalMetaBlob
                    )

            return

        except Exception as ex:
            # Print the exception message
            print(ex.args[0])

    #---------- Class Function: GeoJSONFromCardinals ----------#

    def GeoJSONFromCardinals(self):
        """Generates a GeoJSON String from cardinal photosphere image analysis
        This function follows the process_cardinal_images function after the cardinal images are generated,
        their object detection process from Azure cognitive services computer vision is completed, and the 
        cardinal images have been annotated and tagged.

        Arguments
            container: the Azure blob storage container that holds the cardinal images (analyzed)

        Returns
            fcresponse: a GeoJSON Feature Collection containing all GeoJSON features and geopoints with all analyses.
        """
        try:

            featList = []
            self.CheckBlobContainer(self.cardinalName)
            blobList = self.GetBlobList(self.cardinalName)

            # Loop through the blob list and populate the dictionary json string
            for blob in tqdm(blobList, desc='Processing Cardinals:', unit=' blobs'):
                if self.blobService.get_blob_metadata(self.cardinalName, blob.name) is not {}:
                    metaString = self.blobService.get_blob_metadata(self.cardinalName, blob.name)
                    # All original fields in the Azure blob metadata are stored as strings. Some manipulations are required.

                    # Fields that need to be converted to float numbers
                    fieldsFloat = ['Direction', 'Longitude', 'Latitude', 'Altitude', 'Easting', 'Northing',
                                   'Height', 'DirectionEasting', 'DirectionNorthing', 'DirectionHeight',
                                   'UpEasting', 'UpNorthing', 'UpHeight', 'Roll', 'Pitch', 'Yaw', 'Omega',
                                   'Phi', 'Kappa', 'CardinalDirection', 'CaptionConfidence']
                    for fieldFloat in fieldsFloat:
                        if fieldFloat in metaString:
                            metaString[fieldFloat] = float(metaString[fieldFloat])
                        else:
                            metaString[fieldFloat] = 0.0

                    # Fields that need to be converted to integers
                    fieldsInt = ['CardinalNumber', 'ImageWidth', 'ImageHeight',
                                 'NumberOfCategories', 'NumberOfTags', 'NumberOfObjects']
                    for fieldInt in fieldsInt:
                        if fieldInt in metaString:
                            metaString[fieldInt] = int(metaString[fieldInt])
                        else:
                            metaString[fieldInt] = 0

                    # Fields that must be strings
                    fieldsStr = ['Caption', 'CaptionConfidence', 'ImageWidth', 'ImageHeight', 'ImageFormat',
                                 'ClipArtType', 'LineDrawingType', 'DominantColorForeground',
                                 'DominantColorBackground', 'DominantColors', 'DescriptionTags']
                    for fieldStr in fieldsStr:
                        if fieldStr not in metaString:
                            metaString[fieldStr] = ''

                    # Loop through all detected categories (N=30) and populate fields
                    maxcats = 30
                    for mcat in range(maxcats):
                        catName = 'CategoryName{}'.format(mcat + 1)
                        catScore = 'CategoryScore{}'.format(mcat + 1)
                        if catName not in metaString:
                            metaString[catName] = ''
                            metaString[catScore] = 0.0

                    # Loop through all detection tags (N=30) and populate fields
                    maxtags = 30
                    for mtag in range(maxtags):
                        tagName = 'TagName{}'.format(mtag + 1)
                        tagConf = 'TagConfidence{}'.format(mtag + 1)
                        if tagName not in metaString:
                            metaString[tagName] = ''
                            metaString[tagConf] = 0.0

                    # Loop through all detected objects (N=30) and populate fields
                    maxobj = 30
                    for mobj in range(maxobj):
                        objName = 'Object{}'.format(mobj + 1)
                        objConf = 'Object{}Confidence'.format(mobj + 1)
                        objDir = 'Object{}Direction'.format(mobj + 1)
                        objLon = 'Object{}Longitude'.format(mobj + 1)
                        objLat = 'Object{}Latitude'.format(mobj + 1)
                        objX = 'x{}'.format(mobj + 1)
                        objY = 'y{}'.format(mobj + 1)
                        objW = 'w{}'.format(mobj + 1)
                        objH = 'h{}'.format(mobj + 1)
                        objCX = 'cx{}'.format(mobj + 1)
                        objCY = 'cy{}'.format(mobj + 1)
                        if objName not in metaString:
                            metaString[objName] = ''
                            metaString[objConf] = 0.0
                            metaString[objDir] = 0.0
                            metaString[objLon] = 0.0
                            metaString[objLat] = 0.0
                            metaString[objX] = 0
                            metaString[objY] = 0
                            metaString[objW] = 0
                            metaString[objH] = 0
                            metaString[objCX] = 0
                            metaString[objCY] = 0

                    # Populate scores, confidence, and object bounds
                    if metaString['NumberOfCategories'] >= 1:
                        for i in range(1, metaString['NumberOfCategories'] + 1):
                            metaString['CategoryScore{}'.format(i)] = float(metaString['CategoryScore{}'.format(i)])
                    if metaString['NumberOfTags'] >= 1:
                        for j in range(1, metaString['NumberOfTags'] + 1):
                            metaString['TagConfidence{}'.format(j)] = float(metaString['TagConfidence{}'.format(j)])
                    if metaString['NumberOfObjects'] >= 1:
                        for k in range(1, metaString['NumberOfObjects'] + 1):
                            metaString['Object{}Confidence'.format(k)] = float(metaString['Object{}Confidence'.format(k)])
                            metaString['Object{}Direction'.format(k)] = float(metaString['Object{}Direction'.format(k)])
                            metaString['Object{}Longitude'.format(k)] = float(0.0)
                            metaString['Object{}Latitude'.format(k)] = float(0.0)
                            metaString['x{}'.format(k)] = int(metaString['x{}'.format(k)])
                            metaString['y{}'.format(k)] = int(metaString['y{}'.format(k)])
                            metaString['w{}'.format(k)] = int(metaString['w{}'.format(k)])
                            metaString['h{}'.format(k)] = int(metaString['h{}'.format(k)])
                            metaString['cx{}'.format(k)] = float(metaString['cx{}'.format(k)])
                            metaString['cy{}'.format(k)] = float(metaString['cy{}'.format(k)])

                    # Create each geopoint for the geojson
                    gpoint = geojson.Point((metaString['Longitude'], metaString['Latitude']))
                    # Assemble each feature of the geojson
                    gfeature = geojson.Feature(geometry=gpoint, properties=metaString)
                    # Append the feature to the feature list
                    featList.append(gfeature)
            # Once all features are assembled and populated, create the final feature class geojson
            fcresponse = geojson.FeatureCollection(featList)

            return fcresponse

        except Exception as ex:
            # Print the exception message
            print(ex.args[0])
