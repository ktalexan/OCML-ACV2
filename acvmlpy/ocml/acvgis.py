
#############################################################
#         ArcGIS Analysis for Azure 360 Photospheres        #
# v.3 for ArcGIS Pro (arcpy) and ArcGIS Python API (arcgis) #
#############################################################




#=============================================#
# Reference definitions and project libraries #
#=============================================#


import arcpy, os, glob, sys, uuid, math, statistics, json
from datetime import datetime, timedelta
from itertools import combinations
#from itertools import permutations, combinations
from tqdm import tqdm
from pyproj import Proj,  transform


# Secondary function printing ArcGIS Pro geoprocessing messages (with optional label/title)
def agpmsg(extramsg=None):
    if extramsg is not None:
        print(extramsg)
    for i in range(0, arcpy.GetMessageCount()):
        print('\t{}'.format(arcpy.GetMessage(i)))
    return

# Timedelta display
def strfdelta(start, part='Total', ntabs=0, nlines=2):
    tabs = '\t' * ntabs
    lines = '\n' * nlines
    end = datetime.now()
    tdelta = end - start
    d = {'days': tdelta.days}
    d['hours'], rem = divmod(tdelta.seconds, 3600)
    d['minutes'], d['seconds'] = divmod(rem, 60)

    if tdelta.days > 0 and d['hours'] > 0:
        elapsed = '{days} days, {hours} hours {minutes} minutes {seconds} seconds'.format(**d)
    elif tdelta.days == 0 and d['hours'] > 0:
        elapsed = '{hours} hours {minutes} minutes {seconds} seconds'.format(**d)
    elif tdelta.days == 0 and d['hours'] == 0:
        if d['minutes'] > 0:
            elapsed = '{minutes} minutes {seconds} seconds'.format(**d)
        elif d['minutes'] == 0:
            elapsed = '{seconds} seconds'.format(**d)
    strout = '{0}{1}{2} Execution Time:\n{1}\tStart Time: {3} \n{1}\tEnd Time: {4} (Elapsed Time: {5})'.format(lines, tabs, part, start.strftime('%A, %B %d %Y, %H:%M:%S %p'), end.strftime('%A, %B %d %Y, %H:%M:%S %p'), elapsed)
    print(strout)
    








#===============#
# Class: acvgis #
#===============#

class acvgis(object):
    """Class acvgis:
    This class performs basic functions in the ArcGIS Pro project, including: (a) setting up domains and datasets

    Arguments (class initialization function)
        fclist: the names of each of the sub-datasets in an area to be processed (names of feature classes).
        area: the name of the area to be processed (e.g., Anaheim)
        prjdata: the folder path containing the project data and the geoJSON files (e.g., ACVMLPhotospheres)
        prjagp: the folder path containing the ArcGIS Pro project structure (e.g., ACVML)
        agpname: the name of the ArcGIS Pro project

    Output
        object: returns a class object for processing.

    Example class initialization
        ag = acvgis(prjagp, agpname, projection)
    """

    #--------- Initialize class ---------#
    def __init__(self, fclist, area, prjdata, prjagp, agpname):
        """Class initalization function
        Creates a set of class-wide variables for processing
        """
        self.fclist = fclist
        self.area = area
        self.prjdata = prjdata
        self.prjagp = prjagp
        self.prjaprx = '{}.aprx'.format(agpname)
        self.prjgdb = '{}.gdb'.format(agpname)
        self.pathgdb = os.path.join(self.prjagp, self.prjgdb)
        return




    #--------- Function: create domains ---------#
    def CreateDomains(self):
        """Creates domains in the default project's geodatabaase
        This function creates baseline coded value domains for the project's geodatabase.
        
        Arguments
            None: uses the domains in the project's geodatabase

        Output
            Null: returns nothing. All operations are performed in the project's geodatabase.
        """
        start = datetime.now()

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

        strfdelta(start)

        return
         

    #--------- Function: create_datasets ---------#

    def CreateDatasets(self, recreate=False):
        """Creates feature datasets in the geodatabase.
        This function creates necessary feature datasets in the project's geodatabase to be populated with the analysis data

        Arguments
            recreate (=False, default): if the datasets exist, then it determines if should delete and re-creates them.

        Output
            Null: returns nothing. Performs operations in the default project's geodatabase.
        """
        start = datetime.now()

        # Create feature dataset in geodatabase
        arcpy.env.workspace = self.prjgdb
        arcpy.env.overwriteOutput = True
        prjdatasets = arcpy.ListDatasets('*', 'Feature')
        
        # Projection for processing: WGS_1984_Web_Mercator_Auxiliary_Sphere (Projected)
        prj3857 = arcpy.SpatialReference(3857)

        arcpy.env.workspace = self.prjagp
        arcpy.env.overwriteOutput = True

        # List of feature dataset names
        dlist = ['Photospheres', 'Cardinals', 'StopSigns', 'FireHydrants']

        # For each of the feature dataset, check if it already exists. If it does not, it creates it. If it does, depends on the value of the recreate variable.
        for d in dlist:
            if d not in prjdatasets:
                print('Dataset {} does not exist in geodatabase.'.format(d))
                arcpy.CreateFeatureDataset_management(self.prjgdb, d, prj3857)
                agpmsg('\nCreating dataset: {} using {} projection ({})'.format(d, prj3857.name, prj3857.type))
            elif d in prjdatasets and recreate is True:
                print('Dataset {} already exist in geodatabase but will be deleted.'.format(d))
                arcpy.Delete_management(os.path.join(self.prjgdb, d))
                arcpy.CreateFeatureDataset_management(self.prjgdb, d, prj3857)
                agpmsg('\nCreating dataset: {} using {} projection ({})'.format(d, prj3857.name, prj3857.type))
            elif d in prjdatasets and recreate is False:
                print('Dataset {} already exist in geodatabase. No further action required.'.format(d))            

        strfdelta(start)

        return



    #--------- Function: AddGeoJSON ---------#

    def AddGeoJSON(self):
        """Creates feature classes from geoJSON string
        This function adds the geoJSON data to the project's geodatabase and creates feature class in the Photospheres feature dataset for all the sub-dataset in each of the areas.

        Arguments
            None: uses the geoJSON of the data folder and the project's geodatabase settings.

        Output
            Null: returns nothing. Performs geoprocessing operations in the project's default geodatatabase.
        """
        start = datetime.now()

        # for each of the geoJSON files
        for n, fcname in enumerate(self.fclist, start=1):
            print('\n\n-------------------- Processing {} of {}: {} --------------------\n'.format(n, len(self.fclist), fcname))
            arcpy.env.workspace = self.prjagp
            arcpy.env.overwriteOutput = True

            # Adding GeoJSON
            print('\nStep {}.1: Importing geoJSON to feature class: {}'.format(n, fcname))

            # Read the geoJSON from Azure Cognitive Vision Detection Process
            gj = 'fcjson_{}.json'.format(fcname)
            gjpath = os.path.join(self.prjdata, gj)
            fcout = os.path.join(self.prjgdb, 'Photospheres', fcname)

            # Create a feature class from the geoJSON file
            arcpy.JSONToFeatures_conversion(gjpath, fcout)
            agpmsg('...adding geoJSON: {}'.format(gj))
            
            strfdelta(start, '...Step {}.1'.format(n), 0, 0)


            # Processing Features
            print('\nStep {}.2: Processing feature class: {}'.format(n, fcname))
            
            # Changing alias names
            fcalias = fcname.replace(self.area.lower(), '{} '.format(self.area), 1)
            arcpy.AlterAliasName(os.path.join(self.prjagp, self.prjgdb, 'Photospheres', fcname), fcalias)
            agpmsg('...adding alias: {}'.format(fcalias))

            # Add fields to the feature class in the 'Photospheres' feature collection
            arcpy.AddField_management(fcout, 'ObjectList','TEXT','','','','Detected Objects List','NULLABLE','')
            agpmsg('...adding field: ObjectList')       
            arcpy.AddField_management(fcout, 'StopSign','LONG','','','','Stop Sign Detection','NULLABLE','','Detection')
            agpmsg('...adding field: StopSign')
            arcpy.AddField_management(fcout, 'StopSignAccuracy','LONG','','','','Stop Sign Detection Accuracy','NULLABLE','','Accuracy')
            agpmsg('...adding field: StopSignAccuracy')
            arcpy.AddField_management(fcout, 'FireHydrant','LONG','','','','Fire Hydrant Detection','NULLABLE','','Detection')
            agpmsg('...adding field: FireHydrant')
            arcpy.AddField_management(fcout, 'FireHydrantAccuracy','LONG','','','','Fire Hydrant Detection Accuracy','NULLABLE','','Accuracy')
            agpmsg('...Adding Field: FireHydrantAccuracy')

            strfdelta(start, '...Step {}.2'.format(n), 0, 0)

            # Populating Object List
            print('\nStep {}.3: Populating Object List for feature class: {}'.format(n, fcname))

            # The list of fields to be updated
            objlist = ['OBJECTID','ObjectList', 'StopSign', 'StopSignAccuracy','FireHydrant','FireHydrantAccuracy'] + ['Object{}'.format(i+1) for i in range(30)]

            # Loop through the rows and update data
            print('...updating rows:')
            with arcpy.da.UpdateCursor(fcout, objlist) as cursor:
                for row in tqdm(cursor, desc='\tProcessing {}'.format(fcname)):
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
            strfdelta(start, '...Step {}.3'.format(n), 0, 0)


        strfdelta(start)

        return




    #--------- Function: CreateCardinalFeatures ---------#

    def CreateCardinalFeatures(self):
        """Creates new feature class for first cardinal directions
        This function creates new feature classes for cardinal direction 1 from photosphere feature classes (in the Cardinal feature dataset) for each area.

        Arguments
            None: uses the selected area feature classes in the project's geodatabase.

        Output
            Null: returns nothing. Performs geodatabase operations in the project's default geodatabase.
        """
        start = datetime.now()

        # Create cardinal subset for first cardinal direction of all photosphere feature classes
        arcpy.env.workspace = self.prjagp
        arcpy.env.overwriteOutput = True
        
        # Loop through each of the area's feature classes
        for n, fcname in enumerate(self.fclist, start=1):
            print('\n\n-------------------- Processing {} of {}: {} --------------------\n'.format(n, len(self.fclist), fcname))

            # Basic variables for processing
            fcpath = os.path.join(self.prjgdb, 'Photospheres', fcname)
            fclyr = 'lyr_{}'.format(fcname)
            fcCardinal = '{}c1'.format(fcname)
            fcout = os.path.join(self.pathgdb, 'Cardinals', fcCardinal)
            sqlCardinals = """CardinalNumber = 1"""
        
            # Create new feature layer to hold temporary results
            arcpy.MakeFeatureLayer_management(fcpath, fclyr)
            agpmsg('...Making Temporary Layer: {}'.format(fclyr))

            # Perform query selecting only the 1st cardinal direction
            arcpy.SelectLayerByAttribute_management(fclyr, 'NEW_SELECTION', sqlCardinals)
            agpmsg('...Select Layer by Attribute: {}'.format(sqlCardinals))
        
            # Copy the selected layer features to a new feature class in the geodatabase (in the Cardinals feature dataset)
            arcpy.CopyFeatures_management(fclyr, fcout)
            agpmsg('...Copying Selected Attributes for layer: {}'.format(fclyr))
        
            # Delete the temporary layer
            arcpy.Delete_management(fclyr)
            agpmsg('...Deleting temporary layer: {}'.format(fclyr))

            # Changing Alias name of the new cardinal feature class
            fcalias = '{} Cardinal Direction 1'.format(fcname.replace(self.area.lower(), '{} '.format(self.area), 1))
            arcpy.AlterAliasName(os.path.join(self.prjagp, self.prjgdb, 'Cardinals', fcCardinal), fcalias)
            agpmsg('...Changing Alias name: {}'.format(fcalias))

            # Assign Domains to fields in the new cardinal feature class
            arcpy.AssignDomainToField_management(fcout, 'StopSign', 'Detection')
            agpmsg('...Asigning domain Detection for StopSign')
            arcpy.AssignDomainToField_management(fcout, 'StopSignAccuracy', 'Accuracy')
            agpmsg('...Asigning domain Accuracy for StopSignAccuracy')
            arcpy.AssignDomainToField_management(fcout, 'FireHydrant', 'Detection')
            agpmsg('...Asigning domain Detection for FireHydrant')
            arcpy.AssignDomainToField_management(fcout, 'FireHydrantAccuracy', 'Accuracy')
            agpmsg('...Asigning domain Accuracy for FireHydrantAccuracy')

            strfdelta(start, '...Section {}'.format(n), 0, 0)

        strfdelta(start)

        return




    #--------- Function: MergeAreas ---------#

    def MergeAreas(self):
        """Merging feature classes in area list
        This function uses all the photosphere and cardinal area groups of feature classes to generate merged feature classes (one per area)

        Arguments
            None: uses area feature classes in project's geodatabase.

        Output
            Null: returns nothing. Performs geoprocessing operations in the project's default geodatabase.
        """
        start = datetime.now()

        arcpy.env.workspace = self.prjagp
        arcpy.env.overwriteOutput = True

        print('\n\n-------------------- Merging {} feature classes for {} --------------------\n'.format(len(self.fclist), self.area))

        # Merge cardinals for all the feature classes

        # Define the photosphere and cardinals input lists of feature classes
        fcPhotospheresIn = [os.path.join(self.pathgdb, 'Photospheres', fc) for fc in self.fclist]
        fcCardinalsIn = [os.path.join(self.pathgdb, 'Cardinals', '{}c1'.format(fc)) for fc in self.fclist]
        fcname = self.area.replace(' ', '', 1)
        fcPhotospheresOut = os.path.join(self.pathgdb, 'Photospheres', fcname)
        fcCardinalsOut = os.path.join(self.pathgdb, 'Cardinals', '{}Cardinals1'.format(fcname))

       
        # Merging photosphere feature classes
        print('\nStep 1: Merging Photosphere Feature Classes')

        arcpy.Merge_management(fcPhotospheresIn, fcPhotospheresOut)
        agpmsg('...Merging {} Photospheres'.format(self.area))
        arcpy.AlterAliasName(fcPhotospheresOut, '{} Photospheres'.format(self.area))
        agpmsg('...Changing alias: {} Photospheres'.format(self.area))
        arcpy.AssignDomainToField_management(fcPhotospheresOut, 'StopSign', 'Detection')
        agpmsg('...Assigning domain to StopSign')
        arcpy.AssignDomainToField_management(fcPhotospheresOut, 'StopSignAccuracy', 'Accuracy')
        agpmsg('...Assigning domain to StopSignAccuracy')
        arcpy.AssignDomainToField_management(fcPhotospheresOut, 'FireHydrant', 'Detection')
        agpmsg('...Assigining domain to FireHydrant')
        arcpy.AssignDomainToField_management(fcPhotospheresOut, 'FireHydrantAccuracy', 'Accuracy')
        agpmsg('...Assigning domain to FireHydrantAccuracy')

        strfdelta(start, '...Step 1', 0, 0)


        # Merging cardinal feature classes
        print('\nStep 2: Merging Cardinal Direction 1 Feature Classes')

        arcpy.Merge_management(fcCardinalsIn, fcCardinalsOut)
        agpmsg('...Merging {} Cardinals'.format(self.area))
        arcpy.AlterAliasName(fcCardinalsOut, '{} Cardinal Direction 1'.format(self.area))
        agpmsg('...Changing alias: {} Cardinal Direction 1'.format(self.area))
        arcpy.AssignDomainToField_management(fcCardinalsOut, 'StopSign', 'Detection')
        agpmsg('...Assigning domain to StopSign')
        arcpy.AssignDomainToField_management(fcCardinalsOut, 'StopSignAccuracy', 'Accuracy')
        agpmsg('...Assigning domain to StopSignAccuracy')
        arcpy.AssignDomainToField_management(fcCardinalsOut, 'FireHydrant', 'Detection')
        agpmsg('...Assigning domain to FireHydrant')
        arcpy.AssignDomainToField_management(fcCardinalsOut, 'FireHydrantAccuracy', 'Accuracy')
        agpmsg('...Assigning domain to FireHydrantAccuracy')

        strfdelta(start, '...Step 2', 0, 0)

        strfdelta(start)

        return



    #--------- Function: ProcessDetections ---------#

    def ProcessDetections(self):
        """Creates new feature classes for object detections.
        This function create new feature classes containing ony detections (for stop signs and fire hydrants).

        Arguments
            None: uses the merged area feature classes in the project geodatabase.

        Output
            Null: returns nothing. Performs geodatabase operations in the project's default geodatabase.

        """
        start = datetime.now()

        arcpy.env.workspace = self.prjagp
        arcpy.env.overwriteOutput = True
        fcname = self.area.replace(' ', '', 1)
        fcPhotospheres = (fcname, 'Photospheres')
        fcCardinals = ('{}Cardinals1'.format(fcname), 'Cardinals')
        
        # For each of the type of detected objects, and for each of the Photospheres and Cardinal merged feature classes, perform SQL queries and make new feature classes.
        for outfd, sql in [('StopSign', """StopSign = 1"""), ('FireHydrant', """FireHydrant = 1""")]:
            print('\n\n-------------------- Processing Level: {} --------------------\n'.format(outfd))

            for n, fc in enumerate([fcPhotospheres, fcCardinals], start=1):
                print('\nStep {}: Processing: {}'.format(n, fc))
                infc = fc[0]
                infd = fc[1]
                fclyr = 'lyr_{}'.format(infc)
                fcout = os.path.join(self.pathgdb, '{}s'.format(outfd), '{}{}s'.format(infc, outfd))
                fcalias = '{} {} {}s'.format(fcname, infd, outfd)
                # Make new feature layer (temporary)
                arcpy.MakeFeatureLayer_management(os.path.join(self.prjgdb, infd, infc), fclyr)
                agpmsg('...Creating temporary layer: {}'.format(fclyr))
                # Perform SQL query (select by attribute)
                arcpy.SelectLayerByAttribute_management(fclyr, 'NEW_SELECTION', sql)
                agpmsg('...Selecting layer by attribute: {}'.format(sql))
                # Copy selected features to a new feature class
                arcpy.CopyFeatures_management(fclyr, fcout)
                agpmsg('...Copying selected features to new feature class: \n\t{}'.format(fcout))
                # Perform post-processing operations to the new feature class
                arcpy.AlterAliasName(fcout, fcalias)
                agpmsg('...Changing alias: {}'.format(fcalias))
                arcpy.AssignDomainToField_management(fcout, 'StopSign', 'Detection')
                agpmsg('...Assigning domain to StopSign')
                arcpy.AssignDomainToField_management(fcout, 'StopSignAccuracy', 'Accuracy')
                agpmsg('...Assigning domain to StopSignAccuracy')
                arcpy.AssignDomainToField_management(fcout, 'FireHydrant', 'Detection')
                agpmsg('...Assigning domain to FireHydrant')
                arcpy.AssignDomainToField_management(fcout, 'FireHydrantAccuracy', 'Accuracy')
                agpmsg('...Assigning domain to FireHydrantAccuracy')
                # Delete the temporary feature layer
                arcpy.Delete_management(fclyr)
                agpmsg('...Deleting temporary layer {}'.format(fclyr))

                strfdelta(start, '...Step {}'.format(n), 0, 0)

        strfdelta(start)

        return



    #--------- Function: CreatePointClusters ---------#

    def CreatePointClusters(self, fcdataset, fcname, dist=50):
        """Finds point clusters in feature class.
        This function creates (finds) point clusters in merged feature classes in the geodatabase.

        Arguments
            fcdataset: the name of the feature dataset where the feature class is located (e.g., StopSigns).
            fcname: the name of the feature class to be processed.

        Output
            Null: returns nothing. Performs geodatabase operations in the project's default geodatabase.

        """
        start = datetime.now()

        arcpy.env.workspace = self.pathgdb
        arcpy.env.overwriteOutput = True

        # InProj: State Plane California Zone 6 (NAD83)
        inProj = Proj(init='epsg:2230', preserve_units = True)
        # OutProj: WGS84 (ESRI and ArcGIS Online default)
        outProj = Proj(init='epsg:4326')

        #Path of the input dataset to be processed
        fcin = os.path.join(self.pathgdb, fcdataset, fcname)
        fpc = f'{fcname}FPC'
        fcout = os.path.join(self.pathgdb, fpc)
        
        print('\nStep 1: Creating Point Clusters for the {} feature class in the {} dataset'.format(fcname, fcdataset))
        # Check if the point clusters feature class exists and if it does, delete it
        if fpc in arcpy.ListFeatureClasses():
            arcpy.Delete_management(fpc)

        # Create new point clusters feature class (DBSCAN method, min=2 members, range=20 feet)
        arcpy.gapro.FindPointClusters(fcin, fcout, 'DBSCAN', 2, f'{dist} Feet')
        agpmsg('...Find Point Clusters: {}'.format(fpc))

        # Perform post-processing operations to the new feature class
        arcpy.AssignDomainToField_management(fcout, 'StopSign', 'Detection')
        agpmsg('...Assigning domain to StopSign')
        arcpy.AssignDomainToField_management(fcout, 'StopSignAccuracy', 'Accuracy')
        agpmsg('...Assigning domain to StopSignAccuracy')
        arcpy.AssignDomainToField_management(fcout, 'FireHydrant', 'Detection')
        agpmsg('...Assigning domain to FireHydrant')
        arcpy.AssignDomainToField_management(fcout, 'FireHydrantAccuracy', 'Accuracy')
        agpmsg('...Assigning domain to FireHydrantAccuracy')

        strfdelta(start, '...Step 1', 0, 0)


        print('\nStep 2: Generating Cluster UUID for the Point Clusters: {}'.format(fpc))

        # Set the path of the input feature class
        fpcin = os.path.join(self.pathgdb, fpc)

        # Add new ClusterUUID field to the feature class
        arcpy.AddField_management(fpcin, 'ClusterUUID','TEXT','','','','Cluster Unique ID','NULLABLE','')
        agpmsg('...Added field ClusterUUID in feature class: {}'.format(fpc))

        # Search all the clusters, and sort them by cluster number
        print('...Sorting clusters by cluster number')
        with arcpy.da.SearchCursor(fpcin, 'CLUSTER_ID') as cursor:
            clist = sorted({row[0] for row in cursor})
            clist.remove(-1) # remove single-point clusters

        # create dictionary to hold UUIDs
        fcdict = {}
        # populate UUIDs
        print('...Populating UUIDs in dictionary')
        for v in tqdm(clist, desc='\tUUID'):
            fcdict[v] = str(uuid.uuid4())

        # update rows in the feature class table
        print('...Updating attribute table rows from dictionary')
        with arcpy.da.UpdateCursor(fpcin, ['CLUSTER_ID', 'ClusterUUID']) as cursor:
            for row in tqdm(cursor, desc='\tRow'):
                if row[0] > 0:
                    row[1] = fcdict[row[0]]
                    cursor.updateRow(row)

        strfdelta(start, '...Step 2', 0, 0)


        print('\nStep 3: Generating Object Directions: {}'.format(fpc))


        if 'StopSigns' in fpc:
            searchterm = 'stop sign'
        elif 'FireHydrants' in fpc:
            searchterm = 'fire hydrant'

        # Add new ObjectDirection field to the feature class
        arcpy.AddField_management(fpcin, 'ObjectDirection','FLOAT','','','','Detected Object Direction','NULLABLE','')
        agpmsg('...Added field ObjectDirection in feature class: {}'.format(fpc))
        arcpy.AddField_management(fpcin, 'ObjectLatitude','FLOAT','','','','Detected Object Latitude','NULLABLE','')
        agpmsg('...Added field ObjectLatitude in feature class: {}'.format(fpc))
        arcpy.AddField_management(fpcin, 'ObjectLongitude','FLOAT','','','','Detected Object Longitude','NULLABLE','')
        agpmsg('...Added field ObjectLongitude in feature class: {}'.format(fpc))

        # Create a field list for analysis
        fieldlist = [arcpy.Describe(fpc).OIDFieldName] # obtains the OID name of the feature class
        print('...Creating a Field List for all 30 Objects')
        for i in range(30):
            fieldlist.append('Object{}'.format(i+1))
            fieldlist.append('Object{}Direction'.format(i+1))
        fieldlist.append('ObjectDirection')

        # Update the row by copying the object direction from the coordinates list
        print('...Running matching query on field list')
        with arcpy.da.UpdateCursor(fpcin, fieldlist) as cursor:
            for row in cursor:
                for i in range(len(row)):
                    if row[i] == str(searchterm):
                        row[-1] = row[i+1]
                        cursor.updateRow(row)

        strfdelta(start, '...Step 3', 0, 0)


        print('\nStep 4: Detecting Object Coordinates: {}'.format(fpc))

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
            arcpy.AddField_management(fcout, field[0], field[1],'','','',field[2],'NULLABLE','')
            agpmsg('...Added Field: {}'.format(field[2]))


        # Get a list of clusters in the feature class
        with arcpy.da.SearchCursor(fcout, ['ClusterUUID']) as cursor:
            clusterUUIDlist = sorted({row[0] for row in cursor if row[0] is not None})

        # Create an empty list to hold the coordinates
        coordlist = []
        response = []

        # Loop through each cluster in the cluster list
        print('...Looping through clusters:')
        for cluster in tqdm(clusterUUIDlist, desc='\tCluster'):

            # Create a field list to be used in calculations
            fieldlist = ['OBJECTID1','Latitude','Longitude','Direction','ObjectDirection','Northing','Easting','ClusterUUID']

            # get the rows with the fieldlist variables from the feature class
            with arcpy.da.SearchCursor(fcout, fieldlist) as cursor:
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
                lat1, lon1 = transform(inProj, outProj, y1, x1)
                lat2, lon2 = transform(inProj, outProj, y2, x2)
                lat3, lon3 = transform(inProj, outProj, y3, x3)

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
        print('...Updating feature class table')
        with arcpy.da.UpdateCursor(fcout, updlist) as cursor:
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

            strfdelta(start, '...Step 4', 0, 0)

        strfdelta(start)
                    
        return response

      


    #--------- Function: CreateObjectFeatures ---------#
    def CreateObjectFeatures(self, fpc, data):
        """Creates detected object feature class based on computed coordinates.
        This function creates a new feature class and parses the contents of each of the dictionary datasets as new rows for the created feature class (one for each of the detected objects.

        Arguments

        Output

        """
        start = datetime.now()

        arcpy.env.workspace = self.pathgdb
        arcpy.env.overwriteOutput = True
        # Set projection for processing: CGS_WGS_1984 (Geographic)
        prj4326 = arcpy.SpatialReference(4326)

        # Set the path of the input feature class
        fcin = os.path.join(self.pathgdb, fpc)
        fcloc = '{}Locations'.format(fpc.split('FPC')[0])


        print('\nStep 1: Adding Locations')

        # Create a new feature class to hold the detected object locations
        result = arcpy.CreateFeatureclass_management(self.pathgdb, fcloc, geometry_type='POINT', spatial_reference=prj4326)
        agpmsg('...Creating feature class: {} using {} projection ({})'.format(fcloc, prj4326.name, prj4326.type))
        fcout = result[0] # the newly created feature class
        
        # Fields of the new feature class attriubte table
        fields = ['point', 'cluster', 'LatOIDMean', 'LatOIDStd', 'LonOIDMean', 'LonOIDStd', 'LatObjMean', 'LatObjStd', 'LonObjMean', 'LonObjStd', 'DrivDistMean', 'DrivDistStd', 'OIDObjDistMean','OIDObjDistStd', 'CardDirMean', 'CardDirStd', 'GoogleAPIObj']

        strfdelta(start, '...Step 1', 0, 0)
        

        print('\nStep 2: Adding Attribute Fields from Data')

        # Adds the point ID field in the feature class (as numeric long integer)
        arcpy.AddField_management(fcout, 'point', 'LONG', field_alias='Point ID')
        agpmsg('...Creating Field: PointID')
        
        # Adds the cluster UUID field in the feature class (as string)
        arcpy.AddField_management(fcout, 'cluster', 'TEXT', field_alias='Cluster UUID')
        agpmsg('...Creating field: Cluster UUID')

        # Add all the fields from the list that are numeric (as numeric double)
        for field in fields[2:-1]:
            arcpy.AddField_management(fcout, field, 'DOUBLE')
            agpmsg('...Creating field: {}'.format(field))

        # Add the Google API location field (as string)
        arcpy.AddField_management(fcout, 'GoogleAPIObj', 'TEXT', field_alias='Google API Location')
        agpmsg('...Creating field: GoogleAPIObj')

        #Use the InsertCursor method, to insert the point rows from the list of records in the data)
        with arcpy.da.InsertCursor(fcout, ['point', 'cluster', 'LatOIDMean', 'LatOIDStd', 'LonOIDMean', 'LonOIDStd', 'LatObjMean', 'LatObjStd', 'LonObjMean', 'LonObjStd', 'DrivDistMean', 'DrivDistStd', 'OIDObjDistMean','OIDObjDistStd', 'CardDirMean', 'CardDirStd', 'GoogleAPIObj', 'SHAPE@XY']) as cursor:
            for row in data:
                cursor.insertRow(row)
        agpmsg('...Inserting fields {}'.format(fcout))

        strfdelta(start, '...Step 2', 0, 0)

        strfdelta(start)

        return




