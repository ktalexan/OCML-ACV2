
#############################################################
#         ArcGIS Analysis for Azure 360 Photospheres        #
# v.3 for ArcGIS Pro (arcpy) and ArcGIS Python API (arcgis) #
#############################################################




#=============================================#
# Reference definitions and project libraries #
#=============================================#


import arcpy, os, glob, sys, uuid, math, statistics, json
from itertools import combinations
#from itertools import permutations, combinations
from tqdm import tqdm
from pyproj import Proj,  transform
#import numpy as np
#import matplotlib.pyplot as plt

# Secondary function printing ArcGIS Pro geoprocessing messages (with optional label/title)
def agpmsg(extramsg=None):
    if extramsg is not None:
        print(extramsg)
    for i in range(0, arcpy.GetMessageCount()):
        print('\t{}'.format(arcpy.GetMessage(i)))
    print()
    return



#=======================#
# Class 1: acvstructure #
#=======================#


class acvstructure(object):
    """Class acvstructure:
    This class performs basic functions in the ArcGIS Pro project, including setting up domains and datasets

    Global Attributes
        prjagp: the folder path containing the ArcGIS Pro project structure (e.g., ACVML)
        agpname: the name of the ArcGIS Pro project
        projection: the projection file location (WGS84) to be used

    Example class initialization
        ast = acvstructure(prjagp, agpname, projection)
    """
    #--------- Initialize class ---------#
    def __init__(self, prjagp, agpname, projection):
        """Class initalization function
        Creates a set of class-wide variables for processing
        """
        self.prjagp = prjagp
        self.prjaprx = '{}.aprx'.format(agpname)
        self.prjgdb = '{}.gdb'.format(agpname)
        self.pathgdb = os.path.join(self.prjagp, self.prjgdb)
        self.projection = projection



    #--------- Function: create domains ---------#

    def create_domains(self):
        """Function: create_domains
        This function create baseline coded value domains for the project's geodatabase.
        """
        arcpy.env.workspace = self.prjagp
        arcpy.env.overwriteOutput = True

        # Define coded value domains and their coded key values
        domains = {'Detection': 'Object Detection', 'Accuracy': 'Detection Accuracy'}
        domDictDetection = {0:'Not Detected', 1:'Detected'}
        domDictAccuracy = {-1:'Not Assessed', 0:'False', 1:'True'}

        # Create coded value domains for the data collection areas, object detection, and detection accuracy fields:
        gdbdomains = arcpy.Describe(self.prjgdb).Domains
        for dom in domains:
            if dom in gdbdomains:
                arcpy.DeleteDomain_management(self.prjgdb, dom)
            arcpy.CreateDomain_management(self.prjgdb, dom, domains[dom], 'LONG', 'CODED')
            agpmsg('Creating domain {}'.format(dom))

        # Assign the coded domain keys from each dictionary
        for code in domDictDetection:
            arcpy.AddCodedValueToDomain_management(self.prjgdb, 'Detection', code, domDictDetection[code])
            agpmsg('Adding coded values for detection')
        for code in domDictAccuracy:
            arcpy.AddCodedValueToDomain_management(self.prjgdb, 'Accuracy', code, domDictAccuracy[code])
            agpmsg('Adding coded values for accuracy')

        return


    #--------- Function: create_datasets ---------#

    def create_datasets(self):
        """Function: create_datasets
        This function creates necessary feature datasets in the project's geodatabase to be populated with the analysis data
        """
        # Create feature dataset in geodatabase
        arcpy.env.workspace = self.prjgdb
        arcpy.env.overwriteOutput = True
        prjdatasets = arcpy.ListDatasets('*', 'Feature')

        arcpy.env.workspace = self.prjagp
        arcpy.env.overwriteOutput = True

        # List of feature dataset names
        dlist = ['Photospheres', 'Cardinals', 'StopSigns', 'FireHydrants']

        # For each of the feature dataset, check if it already exists. If it does, it deletes it and creates a new (deletes data too - be careful)
        for d in dlist:
            if prjdatasets is None:
                print('Dataset {} does not exist in geodatabase.'.format(d))
            elif d in prjdatasets:
                print('Dataset {} already exist in geodatabase. Deleting...'.format(d))
                arcpy.Delete_management(os.path.join(self.prjgdb, d))
            arcpy.CreateFeatureDataset_management(self.prjgdb, d, self.projection)
            agpmsg('\nCreating dataset: {}'.format(d))

        return






#========================#
# Class 2: acvgeoprocess #
#========================#


class acvgeoprocess(object):
    """Class acvgeoprocess:
    This class contains a number of functions, methods and processes for post-processing ML object classification analysis using ArcGIS Pro (arcpy) and ArcGIS Python API (arcgis) operations.

    Global Attributes
        fcname: the name of the feature class (e.g., anaheim2018337p1)
        prjdata: the folder path containing the project data and the geoJSON files (e.g., ML-Vision-Photospheres)
        prjagp: the folder path containing the ArcGIS Pro project structure (e.g., ACVML)
        agpname: the name of the ArcGIS Pro project
    
    Example class initialization
        agp = acvgeoprocess(fcname, prjdata, prjagp, agpname)
    """
    #--------- Initialize class ---------#
    def __init__(self, fcname, prjdata, prjagp, agpname):
        """Class initalization function
        Creates a set of class-wide variables for processing
        """
        self.fcname = fcname
        self.prjdata = prjdata
        self.prjagp = prjagp
        self.prjaprx = '{}.aprx'.format(agpname)
        self.prjgdb = '{}.gdb'.format(agpname)
        self.pathgdb = os.path.join(self.prjagp, self.prjgdb)
    
      

    #--------- Function: add_geojson ---------#

    def add_geojson(self):
        """Function: add_geojson
        This function adds the geoJSON data to the project's geodatabase and creates feature class in the Photospheres feature dataset
        """
        arcpy.env.workspace = self.prjagp
        arcpy.env.overwriteOutput = True

        # Read the geoJSON from Azure Cognitive Vision Detection Process
        gj = 'fcjson_{}.json'.format(self.fcname)
        gjpath = os.path.join(self.prjdata, gj)

        # Create a feature class from the geoJSON file
        arcpy.JSONToFeatures_conversion(gjpath, os.path.join(self.prjgdb, 'Photospheres', self.fcname))
        agpmsg('Adding geoJSON: {}'.format(gj))

        return


    #--------- Function: process_feature ---------#

    def process_feature(self):
        """Function: process_feature
        This function performs basic processing operations to the newly added feature class (from the add_geojson function), 
        i.e, adding alias names, adding extra fields, and assign coded domain values to fields.
        """
        arcpy.env.workspace = self.pathgdb
        arcpy.env.overwriteOutput = True

        # Changing Alias name
        if 'anaheim' in self.fcname:
            fcalias = self.fcname.replace('anaheim', 'Anaheim ', 1)
        elif 'ntustin' in self.fcname:
            fcalias = self.fcname.replace('ntustin', 'North Tustin ', 1)

        arcpy.AlterAliasName(os.path.join(self.prjagp, self.prjgdb, 'Photospheres', self.fcname), fcalias)
        agpmsg('Adding Alias: {}'.format(fcalias))



        # Add fields to the feature class in the 'Photospheres' feature collection
        arcpy.AddField_management(self.fcname, 'ObjectList','TEXT','','','','Detected Objects List','NULLABLE','')
        agpmsg('Adding Field: ObjectList')       
        arcpy.AddField_management(self.fcname, 'StopSign','LONG','','','','Stop Sign Detection','NULLABLE','','Detection')
        agpmsg('Adding Field: StopSign')
        arcpy.AddField_management(self.fcname, 'StopSignAccuracy','LONG','','','','Stop Sign Detection Accuracy','NULLABLE','','Accuracy')
        agpmsg('Adding Field: StopSignAccuracy')
        arcpy.AddField_management(self.fcname, 'FireHydrant','LONG','','','','Fire Hydrant Detection','NULLABLE','','Detection')
        agpmsg('Adding Field: FireHydrant')
        arcpy.AddField_management(self.fcname, 'FireHydrantAccuracy','LONG','','','','Fire Hydrant Detection Accuracy','NULLABLE','','Accuracy')
        agpmsg('Adding Field: FireHydrantAccuracy')

        return



    #--------- Function: calculate_object_list ---------#

    def calculate_object_list(self):
        """Function: calculate_object_list
        This function calculates and populates all rows in certain fields based on queries (using UpdateCursor)
        """
        arcpy.env.workspace = self.pathgdb
        arcpy.env.overwriteOutput = True
        fc = self.fcname #name of the feature class

        # The list of fields to be updated
        objlist = ['OBJECTID','ObjectList', 'StopSign', 'StopSignAccuracy','FireHydrant','FireHydrantAccuracy'] + ['Object{}'.format(i+1) for i in range(30)]

        # Loop through the rows and update data
        with arcpy.da.UpdateCursor(fc, objlist) as cursor:
            for row in tqdm(cursor, desc='Processing {}:'.format(fc)):
                row[2] = 0
                row[3] = -1
                row[4] = 0
                row[5] = -1
                detected = []
                for f in row[6:]:
                    if f is not '' and f not in detected:
                        detected.append(f)
                row[1] = ','.join(detected)
            
                if 'stop sign' in detected:
                    row[2] = 1
                if 'fire hydrant' in detected:
                    row[4] = 1
                cursor.updateRow(row)
        agpmsg('Updating Rows')

        return


    #--------- Function: calculate_cardinal1 ---------#

    def calculate_cardinal1(self):
        """Function: calculate_cardinal1
        This function creates new feature classes for cardinal direction 1 from photosphere feature class (in the Cardinal feature dataset)
        """
        # Create cardinal subset for first cardinal direction of all photosphere feature classes
        arcpy.env.workspace = self.prjagp
        arcpy.env.overwriteOutput = True
        
        # Basic variables for processing
        fc = self.fcname
        fcpath = os.path.join(self.prjgdb, 'Photospheres', fc)
        fclyr = 'lyr_{}'.format(fc)
        fcCardinal = '{}c1'.format(fc)
        fcout = os.path.join(self.pathgdb, 'Cardinals', fcCardinal)
        sqlCardinals = """CardinalNumber = 1"""
        
        # Create new feature layer to hold temporary results
        arcpy.MakeFeatureLayer_management(fcpath, fclyr)
        agpmsg('Making Temporary Layer: {}'.format(fclyr))

        # Perform query selecting only the 1st cardinal direction
        arcpy.SelectLayerByAttribute_management(fclyr, 'NEW_SELECTION', sqlCardinals)
        agpmsg('Select Layer by Attribute: {}'.format(sqlCardinals))
        
        # Copy the selected layer features to a new feature class in the geodatabase (in the Cardinals feature dataset)
        arcpy.CopyFeatures_management(fclyr, fcout)
        agpmsg('Copying Selected Attributes for layer: {}'.format(fclyr))
        
        # Delete the temporary layer
        arcpy.Delete_management(fclyr)
        agpmsg('Deleting temporary layer: {}'.format(fclyr))

        # Changing Alias name of the new cardinal feature class
        if 'anaheim' in fc:
            fcalias = 'Anaheim {} Cardinal Direction 1'.format(fcCardinal.split('anaheim')[1].split('c1')[0])
        elif 'ntustin' in fc:
            fcalias = 'North Tustin {} Cardinal Direction 1'.format(fcCardinal.split('ntustin')[1].split('c1')[0])
        arcpy.AlterAliasName(os.path.join(self.prjagp, self.prjgdb, 'Cardinals', fcCardinal), fcalias)
        agpmsg('Changing Alias name: {}'.format(fcalias))

        # Assign Domains to fields in the new cardinal feature class
        arcpy.AssignDomainToField_management(fcout, 'StopSign', 'Detection')
        agpmsg('Asigning domain Detection for StopSign')
        arcpy.AssignDomainToField_management(fcout, 'StopSignAccuracy', 'Accuracy')
        agpmsg('Asigning domain Accuracy for StopSignAccuracy')
        arcpy.AssignDomainToField_management(fcout, 'FireHydrant', 'Detection')
        agpmsg('Asigning domain Detection for FireHydrant')
        arcpy.AssignDomainToField_management(fcout, 'FireHydrantAccuracy', 'Accuracy')
        agpmsg('Asigning domain Accuracy for FireHydrantAccuracy')

        return






#===================#
# Class 3: avcmerge #
#===================#


class acvmerge(object):
    """Class acvmerge:
    This class contains a number of functions, methods and processes for merging feature classes and performing object detection analysis for selected objects.

    Global Attributes
        fclist: the list of the feature classes to be merged
        prjagp: the folder path containing the ArcGIS Pro project structure (e.g., ACVML)
        agpname: the name of the ArcGIS Pro project
    
    Example class initialization
        amg = acvmerge(fclist, prjagp, agpname)
    """
    #--------- Initialize class ---------#
    def __init__(self, fclist, prjagp, agpname):
        """Class initalization function
        Creates a set of class-wide variables for processing
        """
        self.fclist = fclist
        self.prjagp = prjagp
        self.prjaprx = '{}.aprx'.format(agpname)
        self.prjgdb = '{}.gdb'.format(agpname)
        self.pathgdb = os.path.join(self.prjagp, self.prjgdb)


    #--------- Function: merge_list ---------#

    def merge_list(self):
        """Function: merge_list
        This function uses all the photosphere and cardinal area groups of feature classes to generate merged feature classes (one per area)
        """
        arcpy.env.workspace = self.prjagp
        arcpy.env.overwriteOutput = True


        # Merge cardinals for all the feature classes

        # Define the photosphere and cardinals input lists of feature classes
        fcPhotospheresIn = [os.path.join(self.pathgdb, 'Photospheres', fc) for fc in self.fclist]
        fcCardinalsIn = [os.path.join(self.pathgdb, 'Cardinals', '{}c1'.format(fc)) for fc in self.fclist]

        # If all the feature classes in the list have anaheim or north tustin in their name, define respective out-reference attributes
        if all('anaheim' in fc for fc in fcPhotospheresIn):
            fcName = 'Anaheim'
            fcPhotospheresOut = os.path.join(self.pathgdb, 'Photospheres', 'anaheim2018')
            fcCardinalsOut = os.path.join(self.pathgdb, 'Cardinals', 'anaheim2018c1')
        elif all('ntustin' in fc for fc in fcPhotospheresIn):
            fcName = 'North Tustin'
            fcPhotospheresOut = os.path.join(self.pathgdb, 'Photospheres', 'ntustin2019')
            fcCardinalsOut = os.path.join(self.pathgdb, 'Cardinals', 'ntustin2019c1')

        # Once in- and out- attributes are defined, perform merge, and post-processing operations for new feature classes.

        # Merging photosphere feature classes
        arcpy.Merge_management(fcPhotospheresIn, fcPhotospheresOut)
        agpmsg('Merging {} Photospheres'.format(fcName))
        arcpy.AlterAliasName(fcPhotospheresOut, '{} Photospheres'.format(fcName))
        agpmsg('Changing alias: {} Photospheres'.format(fcName))
        arcpy.AssignDomainToField_management(fcPhotospheresOut, 'StopSign', 'Detection')
        agpmsg('Assigning domain to StopSign')
        arcpy.AssignDomainToField_management(fcPhotospheresOut, 'StopSignAccuracy', 'Accuracy')
        agpmsg('Assigning domain to StopSignAccuracy')
        arcpy.AssignDomainToField_management(fcPhotospheresOut, 'FireHydrant', 'Detection')
        agpmsg('Assigining domain to FireHydrant')
        arcpy.AssignDomainToField_management(fcPhotospheresOut, 'FireHydrantAccuracy', 'Accuracy')
        agpmsg('Assigning domain to FireHydrantAccuracy')

        # Merging cardinal feature classes
        arcpy.Merge_management(fcCardinalsIn, fcCardinalsOut)
        agpmsg('Merging {} Cardinals'.format(fcName))
        arcpy.AlterAliasName(fcCardinalsOut, '{} Cardinal Direction 1'.format(fcName))
        agpmsg('Changing alias: {} Cardinal Direction 1'.format(fcName))
        arcpy.AssignDomainToField_management(fcCardinalsOut, 'StopSign', 'Detection')
        agpmsg('Assigning domain to StopSign')
        arcpy.AssignDomainToField_management(fcCardinalsOut, 'StopSignAccuracy', 'Accuracy')
        agpmsg('Assigning domain to StopSignAccuracy')
        arcpy.AssignDomainToField_management(fcCardinalsOut, 'FireHydrant', 'Detection')
        agpmsg('Assigning domain to FireHydrant')
        arcpy.AssignDomainToField_management(fcCardinalsOut, 'FireHydrantAccuracy', 'Accuracy')
        agpmsg('Assigning domain to FireHydrantAccuracy')

        return


    #--------- Function: process_detection ---------#

    def process_detection(self):
        """Function: process_detection
        This function create new feature classes containing ony detections (for stop signs and fire hydrants) 
        """
        arcpy.env.workspace = self.prjagp
        arcpy.env.overwriteOutput = True

        # Anaheim area configurations
        if all('anaheim' in fc for fc in self.fclist):
            fcName = 'Anaheim'
            fcPhotospheres = ('anaheim2018', 'Photospheres')
            fcCardinals = ('anaheim2018c1', 'Cardinals')

        # North Tustin area configurations
        elif all('ntustin' in fc for fc in self.fclist):
            fcName = 'North Tustin'
            fcPhotospheres = ('ntustin2019', 'Photospheres')
            fcCardinals = ('ntustin2019c1', 'Cardinals')
        
        # For each of the type of detected objects, and for each of the Photospheres and Cardinal merged feature classes, perform SQL queries and make new feature classes.
        for outfd, sql in [('StopSign', """StopSign = 1"""), ('FireHydrant', """FireHydrant = 1""")]:
            print('\nProcessing {}s\n'.format(outfd))
            for fc in [fcPhotospheres, fcCardinals]:
                print('--------- Processing: {} ---------'.format(fc))
                infc = fc[0]
                infd = fc[1]
                fclyr = 'lyr_{}'.format(infc)
                fcout = os.path.join(self.pathgdb, '{}s'.format(outfd), '{}{}s'.format(infc, outfd))
                fcalias = '{} {} {}s'.format(fcName, infd, outfd)
                # Make new feature layer (temporary)
                arcpy.MakeFeatureLayer_management(os.path.join(self.prjgdb, infd, infc), fclyr)
                agpmsg('Creating temporary layer: {}'.format(fclyr))
                # Perform SQL query (select by attribute)
                arcpy.SelectLayerByAttribute_management(fclyr, 'NEW_SELECTION', sql)
                agpmsg('Selecting layer by attribute: {}'.format(sql))
                # Copy selected features to a new feature class
                arcpy.CopyFeatures_management(fclyr, fcout)
                agpmsg('Copying selected features to new feature class: {}'.format(fcout))
                # Perform post-processing operations to the new feature class
                arcpy.AlterAliasName(fcout, fcalias)
                agpmsg('Changing alias: {}'.format(fcalias))
                arcpy.AssignDomainToField_management(fcout, 'StopSign', 'Detection')
                agpmsg('Assigning domain to StopSign')
                arcpy.AssignDomainToField_management(fcout, 'StopSignAccuracy', 'Accuracy')
                agpmsg('Assigning domain to StopSignAccuracy')
                arcpy.AssignDomainToField_management(fcout, 'FireHydrant', 'Detection')
                agpmsg('Assigning domain to FireHydrant')
                arcpy.AssignDomainToField_management(fcout, 'FireHydrantAccuracy', 'Accuracy')
                agpmsg('Assigning domain to FireHydrantAccuracy')
                # Delete the temporary feature layer
                arcpy.Delete_management(fclyr)
                agpmsg('Deleting temporary layer {}'.format(fclyr))
                print('------------------------------------\n')

        return






#======================#
# Class 4: acvclusters #
#======================#


class acvclusters(object):
    """Class acvclusters:
    This class contains a number of functions, methods and processes for clustering detected objects and determining object coordinates and distances.

    Global Attributes
        fcname: the name of the merged feature class to be processed
        fcdataset: the feature dataset in which the feature class is located in the geodatabase
        prjagp: the folder path containing the ArcGIS Pro project structure (e.g., ACVML)
        agpname: the name of the ArcGIS Pro project
    
    Example class initialization
        acl = acvclusters(fcname, fcdataset, prjagp, agpname)
    """
    #--------- Initialize class ---------#
    def __init__(self, fcname, fcdataset, prjagp, agpname):
        """Class initalization function
        Creates a set of class-wide variables for processing
        """
        self.fcname = fcname
        self.fcdataset = fcdataset
        self.prjagp = prjagp
        self.prjaprx = '{}.aprx'.format(agpname)
        self.prjgdb = '{}.gdb'.format(agpname)
        self.pathgdb = os.path.join(self.prjagp, self.prjgdb)


        #--------- Projections for transformations ---------#

        # InProj: State Plane California Zone 6 (NAD83)
        self.inProj = Proj(init='epsg:2230', preserve_units = True)
        # OutProj: WGS84 (ESRI and ArcGIS Online default)
        self.outProj = Proj(init='epsg:4326')
        self.spref = arcpy.SpatialReference(4326)

        arcpy.env.workspace = self.pathgdb
        arcpy.env.overwriteOutput = True

        #Feature class list for Stop Signs or Fire Hydrants feature datasets
        self.fclist = arcpy.ListFeatureClasses(feature_dataset = self.fcdataset)
        # Sublist containing only cardinal direction 1 for the lists
        self.fclistc1 = arcpy.ListFeatureClasses(wild_card = '*c1*', feature_dataset = self.fcdataset)




    #--------- Function: create_point_clusters ---------#

    def create_point_clusters(self):
        """Function: create_point_clusters
        This function creates (finds) point clusters in feature classes
        """
        arcpy.env.workspace = self.pathgdb
        arcpy.env.overwriteOutput = True

        fcnew = '{}_FPC20'.format(self.fcname)
        fcin = os.path.join(self.pathgdb, self.fcdataset, self.fcname)
        fcout = os.path.join(self.pathgdb, fcnew)
        
        print('Creating Point Clusters for the {} feature class in the {} dataset'.format(self.fcname, self.fcdataset))
        # Check if the point clusters feature class exists and if it does, delete it
        if fcnew in arcpy.ListFeatureClasses():
            arcpy.Delete_management(fcnew)

        # Create new point clusters feature class (DBSCAN method, min=2 members, range=20 feet)
        arcpy.gapro.FindPointClusters(fcin, fcout, 'DBSCAN', 2, '20 Feet')
        agpmsg('Find Point Clusters: {}'.format(fcnew))

        # Perform post-processing operations to the new feature class
        arcpy.AssignDomainToField_management(fcout, 'StopSign', 'Detection')
        agpmsg('Assigning domain to StopSign')
        arcpy.AssignDomainToField_management(fcout, 'StopSignAccuracy', 'Accuracy')
        agpmsg('Assigning domain to StopSignAccuracy')
        arcpy.AssignDomainToField_management(fcout, 'FireHydrant', 'Detection')
        agpmsg('Assigning domain to FireHydrant')
        arcpy.AssignDomainToField_management(fcout, 'FireHydrantAccuracy', 'Accuracy')
        agpmsg('Assigning domain to FireHydrantAccuracy')

        return


    #--------- Function: create_clusterUUID ---------#
    def create_clusterUUID(self):
        """Function: create_clusterUUID
        This function returns a list of unique clusters (with UUID) in a point cluster feature class
        """
        arcpy.env.workspace = self.pathgdb
        arcpy.env.overwriteOutput = True

        table = os.path.join(self.pathgdb, '{}_FPC20'.format(self.fcname))

        # Add new ClusterUUID field to the feature class
        arcpy.AddField_management(table,'ClusterUUID','TEXT','','','','Cluster Unique ID','NULLABLE','')
        agpmsg('Added field ClusterUUID in feature class: {}_FPC20'.format(self.fcname))

        # Search all the clusters, and sort them by cluster number
        with arcpy.da.SearchCursor(table, 'CLUSTER_ID') as cursor:
            clist = sorted({row[0] for row in cursor})
            clist.remove(-1) # remove single-point clusters

        # create dictionary to hold UUIDs
        fcdict = {}
        # populate UUIDs
        for v in clist:
            fcdict[v] = str(uuid.uuid4())
        # update rows in the feature class table
        with arcpy.da.UpdateCursor(table, ['CLUSTER_ID', 'ClusterUUID']) as cursor:
            for row in tqdm(cursor):
                if row[0] > 0:
                    row[1] = fcdict[row[0]]
                    cursor.updateRow(row)

        return



    #--------- Function: create_object_direction ---------#
    def create_object_direction(self):
        """Function: create_object_direction
        This function adds new fields for detected objects and populates the object direction field
        """
        arcpy.env.workspace = self.pathgdb
        arcpy.env.overwriteOutput = True

        table = os.path.join(self.pathgdb, '{}_FPC20'.format(self.fcname))
        if 'StopSigns' in self.fcname:
            searchterm = 'stop sign'
        elif 'FireHydrants' in self.fcname:
            searchterm = 'fire hydrant'

        # Add new ObjectDirection field to the feature class
        arcpy.AddField_management(table,'ObjectDirection','FLOAT','','','','Detected Object Direction','NULLABLE','')
        agpmsg('Added field ObjectDirection in feature class: {}_FPC20'.format(self.fcname))
        arcpy.AddField_management(table,'ObjectLatitude','FLOAT','','','','Detected Object Latitude','NULLABLE','')
        agpmsg('Added field ObjectLatitude in feature class: {}_FPC20'.format(self.fcname))
        arcpy.AddField_management(table,'ObjectLongitude','FLOAT','','','','Detected Object Longitude','NULLABLE','')
        agpmsg('Added field ObjectLongitude in feature class: {}_FPC20'.format(self.fcname))


        # Create a field list for analysis
        fieldlist = ['OBJECTID1']
        for i in range(30):
            fieldlist.append('Object{}'.format(i+1))
            fieldlist.append('Object{}Direction'.format(i+1))
        fieldlist.append('ObjectDirection')

        # Update the row by copying the object direction from the coordinates list
        with arcpy.da.UpdateCursor(table, fieldlist) as cursor:
            for row in cursor:
                for i in range(len(row)):
                    if row[i] == str(searchterm):
                        row[-1] = row[i+1]
                        cursor.updateRow(row)

        return




    #--------- Function: calculate_object_coordinates ---------#
    def calculate_object_coordinates(self):
        """Function: calculate_object_coordinates
        This function calculates object coordinates from clusters and their statistics
        """
        arcpy.env.workspace = self.pathgdb
        arcpy.env.overwriteOutput = True

        fc = os.path.join(self.pathgdb, '{}_FPC20'.format(self.fcname))

        # Create new fields in feature class to hold the calculated data
        newfields = [('LatObjMean', 'FLOAT','Mean Object Latitude'), 
                  ('LonObjMean','FLOAT','Mean Object Longitude'),
                  ('LatObjStd','FLOAT','Latitude Detection Standard Deviation'),
                  ('LonObjStd','FLOAT','Longitude Detection Stardard Deviation'),
                  ('DrivDistMean','FLOAT','Mean Driving Distance'),
                  ('DrivDistStd','FLOAT','Standard Deviation of Driving Distance'),
                  ('ObjDistOIDMean','FLOAT','Mean Point to Object Distance'),
                  ('ObjDistOIDStd','FLOAT','Standard Deviation of Point to Object Distance'),
                  ('ObjDirMean','FLOAT','Mean Object Direction'),
                  ('ObjDirStd','FLOAT','Standard Deviation of Mean Object Directions'),
                  ('GoogleAPIObj','TEXT','Google Object Position API')]
        for field in newfields:
            arcpy.AddField_management(fc,field[0],field[1],'','','',field[2],'NULLABLE','')
            agpmsg('Added Field: {}'.format(field[2]))

        # Get a list of clusters in the feature class
        with arcpy.da.SearchCursor(fc, ['ClusterUUID']) as cursor:
            clusterUUIDlist = sorted({row[0] for row in cursor if row[0] is not None})

        # Create an empty list to hold the coordinates
        coordlist = []
        response = []

        # Loop through each cluster in the cluster list
        for cluster in tqdm(clusterUUIDlist, desc='Cluster'):

            # Create a field list to be used in calculations
            fieldlist = ['OBJECTID1','Latitude','Longitude','Direction','ObjectDirection','Northing','Easting','ClusterUUID']

            # get the rows with the fieldlist variables from the feature class
            with arcpy.da.SearchCursor(fc, fieldlist) as cursor:
                # create an empty dictionary to hold the points
                pointdict = {}
                # loop through each objectid in the feature class table
                for row in cursor:
                    # find the rows with the same cluster ID
                    if row[-1] == cluster:
                        # set the dictionary index as the ObjectID of the table (left side)
                        # and the the dictionary values as all the remaining fields in the field list
                        pointdict[row[0]] = row[1:]

            # Create a list with all the objectid records in the cluster
            ids = [point for point in pointdict]

            # Get all the paired combinations of points (no-repeat)
            combinationlist = list(combinations(ids, 2))

            # Create a new dictionary to hold all the object coordinates
            objcoorddict = {}

            # Loop through each coordinate pair in the paired combination list
            for i, coord in enumerate(combinationlist, start = 1):
                # label each pair
                pairname = 'Pair{}'.format(i)
                # create a sub-entry for each of the pairs in the object coordinate dictionary
                objcoorddict[pairname] = {}

                # Assign coordinates, angles, and slopes for first point (northing, easting, cardinal direction)
                x1, y1, θ1 = pointdict[coord[0]][4], pointdict[coord[0]][5], pointdict[coord[0]][3]
                μ1 = math.tan(θ1) # calculate slope 1

                # Assign coordinates, angles, and slopes for second point (northing, easting, cardinal direction)
                x2, y2, θ2 = pointdict[coord[1]][4], pointdict[coord[1]][5], pointdict[coord[1]][3]
                μ2 = math.tan(θ2) # calculate slope 2

                # Calculate coordinates for detected object (easting and northing)
                x3 = (y2 - y1 + (μ1 * x1) - (μ2 * x2)) / (μ1 - μ2)
                y3 = y1 - (μ1 * (x1 - x3))

                # Convert all three coordinates to Lat/Lon
                lat1, lon1 = transform(self.inProj, self.outProj, y1, x1)
                lat2, lon2 = transform(self.inProj, self.outProj, y2, x2)
                lat3, lon3 = transform(self.inProj, self.outProj, y3, x3)

                # Calculate distances
                d0 = math.sqrt((x2 - x1)**2 + (y2 - y1)**2) # distance between driving points 1 and 2
                d1 = math.sqrt((x3 - x1)**2 + (y3 - y1)**2) # distance between point 1 and object
                d2 = math.sqrt((x3 - x2)**2 + (y3 - y2)**2) # distance between point 2 and object

                # Calculate average direction between two object directional angles
                odm = (θ1 + θ2)/2

                # Populate the object coordinates dictionary for the cluster
                objcoorddict[pairname]['OID1'] = coord[0]
                objcoorddict[pairname]['OID2'] = coord[1]
                objcoorddict[pairname]['LatOID1'] = lat1
                objcoorddict[pairname]['LonOID1'] = lon1
                objcoorddict[pairname]['LatOID2'] = lat2
                objcoorddict[pairname]['LonOID2'] = lon2
                objcoorddict[pairname]['ObjDirOID1'] = θ1
                objcoorddict[pairname]['ObjDirOID2'] = θ2
                objcoorddict[pairname]['MeanObjDir'] = odm
                objcoorddict[pairname]['LatObject'] = lat3
                objcoorddict[pairname]['LonObject'] = lon3
                objcoorddict[pairname]['DrivingDistance'] = d0
                objcoorddict[pairname]['ObjDistanceOID1'] = d1
                objcoorddict[pairname]['ObjDistanceOID2'] = d2

                # Create an empty list to hold all the detected point data
                pointdata = []
                # For each row in combinations
                rowdata = {}
                # Calculate pair-wise coordinates
                for point in pointdict:
                    templist = []
                    indexlist1 = ['LatOID1', 'LonOID1', 'LatObject', 'LonObject', 
                                    'DrivingDistance', 'ObjDistanceOID1', 'MeanObjDir']
                    indexlist2 = ['LatOID2', 'LonOID2', 'LatObject', 'LonObject', 
                                    'DrivingDistance', 'ObjDistanceOID2', 'MeanObjDir']
                    outputlist = ['LatOID', 'LonOID', 'LatObject', 'LonObject', 
                                    'DrivingDistance', 'objDistanceOID', 'MeanObjDir']
                    oid = 'OID{}'.format(point)
                    rowdata[oid] = {}
                    for pair in objcoorddict:
                        if str(point) in str(objcoorddict[pair]['OID1']):
                            for i, item in enumerate(indexlist1):
                                rowdata[oid]['OID'] = point
                                rowdata[oid][outputlist[i]] = objcoorddict[pair][item]
                        elif str(point) in str(objcoorddict[pair]['OID2']):
                            for i, item in enumerate(indexlist2):
                                rowdata[oid]['OID'] = point
                                rowdata[oid][outputlist[i]] = objcoorddict[pair][item]

            # For each cluster, calculate statistics
            LatOIDMean = statistics.mean([rowdata[i]['LatOID'] for i in rowdata])
            LatOIDStd = statistics.stdev([rowdata[i]['LatOID'] for i in rowdata])
            LonOIDMean = statistics.mean([rowdata[i]['LonOID'] for i in rowdata])
            LonOIDStd = statistics.stdev([rowdata[i]['LonOID'] for i in rowdata])
            LatObjMean = statistics.mean([rowdata[i]['LatObject'] for i in rowdata])
            LatObjStd = statistics.stdev([rowdata[i]['LatObject'] for i in rowdata])
            LonObjMean = statistics.mean([rowdata[i]['LonObject'] for i in rowdata])
            LonObjStd = statistics.stdev([rowdata[i]['LonObject'] for i in rowdata])
            DrivDistMean = statistics.mean([rowdata[i]['DrivingDistance'] for i in rowdata])
            DrivDistStd = statistics.stdev([rowdata[i]['DrivingDistance'] for i in rowdata])
            ObjDistOIDMean = statistics.mean([rowdata[i]['objDistanceOID'] for i in rowdata])
            ObjDistOIDStd = statistics.stdev([rowdata[i]['objDistanceOID'] for i in rowdata])
            ObjDirMean = statistics.mean([rowdata[i]['MeanObjDir'] for i in rowdata])
            ObjDirStd = statistics.stdev([rowdata[i]['MeanObjDir'] for i in rowdata])
            GoogleAPIObj = 'https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={},{}&heading={}&pitch=10'.format(str(LonObjMean), str(LatObjMean),str(ObjDirMean))

            # Append the coordinate list with the calculated statistics
            coordlist.append((point, cluster, LatOIDMean, LatOIDStd, LonOIDMean, LonOIDStd, LatObjMean, LatObjStd, LonObjMean, LonObjStd, DrivDistMean, DrivDistStd, ObjDistOIDMean, ObjDistOIDStd, ObjDirMean, ObjDirStd, GoogleAPIObj))

            response.append((point, cluster, LatOIDMean, LatOIDStd, LonOIDMean, LonOIDStd, LatObjMean, LatObjStd, LonObjMean, LonObjStd, DrivDistMean, DrivDistStd, ObjDistOIDMean, ObjDistOIDStd, ObjDirMean, ObjDirStd, GoogleAPIObj, (LatObjMean, LonObjMean)))

            # end of the cluster-side calculations

        # This is alist for updating the data in the feature class
        updlist = ['ClusterUUID','LatObjMean','LatObjStd','LonObjMean','LonObjStd',
                   'DrivDistMean','DrivDistStd','ObjDistOIDMean','ObjDistOIDStd',
                   'ObjDirMean','ObjDirStd','GoogleAPIObj','ObjectDirection']
        
        # Loop through each of the table row in the feature class
        with arcpy.da.UpdateCursor(fc, updlist) as cursor:
            for row in cursor:
                for c in coordlist:
                    if row[0] == c[1]:
                        row[1] = c[6]
                        row[2] = c[7]
                        row[3] = c[8]
                        row[4] = c[9]
                        row[5] = c[10]
                        row[6] = c[11]
                        row[7] = c[12]
                        row[8] = c[13]
                        row[9] = c[14]
                        row[10] = c[15]
                        row[11] = c[16]
                        cursor.updateRow(row)

        # Finalize the function's response
        #response = coodrlist
        #responseCols = ['point', 'cluster', 'LatOIDMean', 'LatOIDStd', 'LonOIDMean', 'LonOIDStd', 'LatObjMean', 
        #                'LatObjStd', 'LonObjMean', 'LonObjStd', 'DrivDistMean', 'DrivDistStd', 'OIDObjDistMean',
        #                'OIDObjDistStd', 'CardDirMean', 'CardDirStd', 'GoogleAPIObj']
        #for row in coordlist:
        #    response[row[1]] = {}
        #    for i in range(0,len(responseCols)):
        #        response[row[1]][responseCols[i]] = row[i]

            
        return response



    #--------- Function: create_object_features ---------#
    def create_object_features(self, data):
        """Function: create_object_features
        This function creates a new feature class and parses the contents of each of the dictionary datasets as new rows for the created feature class (one for each of the detected objects.
        """
        arcpy.env.workspace = self.pathgdb
        arcpy.env.overwriteOutput = True

        #xydata = {}
        #for d in data:
        #    xydata[d] = {}
        #    for item in data[d]:
        #        xydata[d][item] = data[d][item]
        #    xydata[d]['ShapeXY'] = (data[d]['LatObjMean'], data[d]['LonObjMean'])

        fc = os.path.join(self.pathgdb, '{}_FPC20'.format(self.fcname))

        result = arcpy.CreateFeatureclass_management(self.pathgdb, '{}Locations'.format(self.fcname), geometry_type='POINT', spatial_reference=self.spref)
        agpmsg('Creating feature class: {}Locations'.format(fc))
        feature_class = result[0]
        fields = ['point', 'cluster', 'LatOIDMean', 'LatOIDStd', 'LonOIDMean', 'LonOIDStd', 'LatObjMean', 'LatObjStd', 'LonObjMean', 'LonObjStd', 'DrivDistMean', 'DrivDistStd', 'OIDObjDistMean','OIDObjDistStd', 'CardDirMean', 'CardDirStd', 'GoogleAPIObj']
        arcpy.AddField_management(feature_class, 'point', 'LONG', field_alias='Point ID')
        agpmsg('Creating Field: PointID')
        arcpy.AddField_management(feature_class, 'cluster', 'TEXT', field_alias='Cluster UUID')
        agpmsg('Creating field: Cluster UUID')

        for field in fields[2:-1]:
            arcpy.AddField_management(feature_class, field, 'DOUBLE')
            agpmsg('Creating field: {}'.format(field))

        arcpy.AddField_management(feature_class, 'GoogleAPIObj', 'TEXT', field_alias='Google API Location')
        agpmsg('Creating field: GoogleAPIObj')

        #fieldlist = fields.append('SHAPE@XY')
        with arcpy.da.InsertCursor(feature_class, ['point', 'cluster', 'LatOIDMean', 'LatOIDStd', 'LonOIDMean', 'LonOIDStd', 'LatObjMean', 'LatObjStd', 'LonObjMean', 'LonObjStd', 'DrivDistMean', 'DrivDistStd', 'OIDObjDistMean','OIDObjDistStd', 'CardDirMean', 'CardDirStd', 'GoogleAPIObj', 'SHAPE@XY']) as cursor:
            for row in data:
                cursor.insertRow(row)




