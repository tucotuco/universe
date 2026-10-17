#-------------------------------------------------------------------------
# Project     : Automated Delimitation of Maritime Zones and Boundaries
# Sub-project : Voronoi Tessellation on the ellipsoid 
# Author      : Christos Kastrisios
# Version     : v1.0
# Environment : Wing IDE 101 (Version 4.1.14-1) with Python 2.7.13
#               
# Description : This tool generates the Voronoi Diagram on the ellipsoidal Earth 
#               for a set of points (generators). It utilizes the voronoi tesselation   
#               on the spherical earth and extends the tesselation to the ellipsoid 
#               with solving the over-determined equations system created by each 
#               vertex's spherical coordinates and the distances to its three generators.
#
# Usage       : program <inFC> <outFC> <accuracy_value> 
#                <delete_duplicates><transformation>
#                       
#               inFC               : Generating points
#               outFC              : Filename with path used to store
#                                    the results 
#               accuracy_value     : The desired accuracy of Voronoi 
#                                    Vertices on the ellipsoid in 
#                                    decimal degrees.
#               delete_duplicates  : Boolean (True / False). When True, code 
#                                    removes duplicate genarators
#               transformation     : Ellipsoid to sphere transformation 
#                                    (i.e. conformal, authalic, 
#                                    equid_parallels, equid_meridians)
#
#-------------------------------------------------------------------------

# Import required libraries
import arcpy
from arcpy import gp
from arcpy import env
import os
import sys
import shutil
import numpy as np
import scipy as sp
import copy
import csv
from multiprocessing import Process, Queue
import Voronoi_Ellipsoid_lib 



#------------------------------- main -------------------------------#
# Each arcpy tool will use all the available system cores
arcpy.env.parallelProcessingFactor = "100%"

print ("Process begins..."); start_time = time.time()
print ("Reading inputs...")

# Load input arguments
inFC = sys.argv [1]
outFC = sys.argv [2] 
accuracy_value = float(sys.argv[3]) 
delete_duplicates = sys.argv[4]
transformation = sys.argv[5]

# Determine GCS_WGS_1984 as the spatial reference 
sr = arcpy.SpatialReference(4326)

# Overwriting outputs is allowed
arcpy.env.overwriteOutput = True

# Set workspace path based on the outputFC path
wksp = os.path.split(outFC)[0]

# Set up a temporary gdb in a temporary workspace
scrGDB = None
scrName = "Voronoi_Ellipsoid_Scratch_Wksp"
# Use "TEMP" directory if exists else use "ROOT"
s_wksp = gp.GetSystemEnvironment("TEMP") + os.path.sep + scrName  + ".gdb"
if not os.path.exists(s_wksp):
  arcpy.CreateFileGDB_management(*os.path.split(s_wksp))  
arcpy.env.scratchworkspace = s_wksp

# Get output filename (without the path)
outname = os.path.split(outFC)[-1]

# Get basepoints filename (without the path)
inname = os.path.split(inFC)[-1]

# Load input points as geometry objects
print "Loading coordinates..." 
gnrts_ell_list = Voronoi_Ellipsoid_lib.load_points (inFC)

# Search for and delete duplicate points 
# (duplicates are created when extracting vertices from lines or 
# polygons (first and last points coincide)
#
# gnrts_ell_list: List holding the remaining points in the format:
# [lat, long, initial point id, unique state value]
#
if delete_duplicates == "true":
  print "Deleting duplicate generators..."
  gnrts_ell_list = Voronoi_Ellipsoid_lib.delete_duplicate_points (gnrts_ell_list)

print "Transforming geodetic coordinates into spherical Cartesian..."
# gnrts_sph_cartes_list: List in the format [Xc, Yc, Zc]
(gnrts_sph_cartes_list) = Voronoi_Ellipsoid_lib.transform_coordinates_to_cartesian(gnrts_ell_list, transformation)

# Generate array from the above list to be digested from the 
# Voronoi tesselation function
gnrts_sph_cartes_array = np.asarray(gnrts_sph_cartes_list)

# Calculate Earth radius based on transformation
spher_earth_radius =  Voronoi_Ellipsoid_lib.Get_Radius(transformation)

print "Generating Voronoi Diagram on spherical earth..."
# The SphericalVoronoi function generates:
#   1. List of Voronoi Vertices' IDs and their coordinates (.vertices)
#   2. List of vertices and their generators' ids (.simplices)
voronoi_instance = Voronoi_Ellipsoid_lib.SphericalVoronoi(gnrts_sph_cartes_array,spher_earth_radius)
print "Number of Voronoi vertices: %s" % (len(voronoi_instance.vertices))

# Calculate and sort vertices creating Voronoi Regions (.regions)
voronoi_instance._calc_vertices_regions()
voronoi_instance.sort_vertices_of_regions()
print("Voronoi Tesselation on sphere is complete")

print ("\nBegin working on the ellipsoidal earth...")
# Transform the voronoi vertices' spherical cartesian coordinates 
# to spherical geographic and subsequently to geodetic
print ("Tranforming Voronoi Vertices coordinates to geodetic...")
Voronoi_Ellipsoid_lib.load_and_transform_coordinates_to_geodetic (voronoi_instance.vertices, transformation)
print ("Voronoi Vertices' approximate coordinates on ellipsoid are now available!\n")

print ("Calculating precise geodetic Voronoi Vertices coordinates...(3-point problem):\n")
# Now that the approximation of Voronoi vertices on the ellipsoid 
# and their corresponding generators are known, calculate the precise
# vertices' coordinates on ellipsoid using the least squares method
# For each dictionary key (Voronoi Vertex) create a new Voronoi Vertex (VV)
# on the ellipsoid    
vertices_coords_ellips = Voronoi_Ellipsoid_lib.calculate_VV_from_three_GNRTs (voronoi_instance.vertices, voronoi_instance.simplices, accuracy_value)
print("\nVoronoi Vertices' geodetic coordinates calculated!!")

print ("Creating Voronoi Regions...")
# Create the voronoi regions as polylines from the results of tesselation
csv_table = Voronoi_Ellipsoid_lib.csv_table_of_coordinates_for_XY_to_Line_tool(voronoi_instance.regions, vertices_coords_ellips)
out_lines_memory = Voronoi_Ellipsoid_lib.VEdges_ellipsoidal_Coord_no_2pp (csv_table)
out_lines = wksp + os.sep + outname +"_Voronoi_Edges_not_Dens"
arcpy.CopyFeatures_management(out_lines_memory, out_lines)
print ("FC with Voronoi Edges (not densified) on the ellipsoid created...\n")

print ("\nDensifying Voronoi Edges...")
# Solve the 2-point problem and add a new VV along V.Edges
#      Outputs: new FC with densified V.Edges, csv files of VV and Generators 
(csv_VV_GNRTs, csv_VV_GNRTs_2) = Voronoi_Ellipsoid_lib.Two_point_problem(out_lines_memory, gnrts_ell_list, accuracy_value, outname, voronoi_instance.simplices, vertices_coords_ellips, wksp, sr)

print ("\nCreating FC of Voronoi Vertices...")
# Create a point feature class containing the Vertices and the IDs of their Generators  
Voronoi_Ellipsoid_lib.Point_FC_from_csv_file (csv_VV_GNRTs, outname, sr)

print ("Creating construction / equidistance lines...")
#Create distance lines connecting VV with its corresponding Generators
Voronoi_Ellipsoid_lib.construction_lines_VV_GNRTs (csv_VV_GNRTs_2, gnrts_ell_list, wksp, outname)

print("Process is complete (%s sec)" % round(time.time() - start_time, 2))