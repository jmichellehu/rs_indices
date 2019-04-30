#!/usr/bin/env python

# Calculate Normalized Difference Snow Index from orthorectified, resampled, and clipped WV-3 top-of-atmosphere reflectance imagery and Level 1 Landsat 8 imagery.

# Adapted from http://gencersumbul.bilkent.edu.tr/post/gdal_scripts/

# system libraries and imports
import sys
import argparse
import struct

# import third party
import numpy as np
from osgeo import gdal

print(gdal.VersionInfo())

# Have user define input and output image filenames
parser = argparse.ArgumentParser(description='GeoTiff Multi Spectral Image to NDSI Image Conversion Script with Normalized Difference Snow Index Measurement')
parser.add_argument('-in', '--MS_input_file', help='GeoTiff multi band MS image file', required=True)
parser.add_argument('-in2', '--SWIR_input_file', help='GeoTiff multi band SWIR image file for WV3', required=False)
parser.add_argument('-in_sensor', '--input_satellite', help='Sensor name - either WV3 or L8', required=True)
parser.add_argument('-in_ndsi', '--input_thresh', help='String of NDSI outfile type: either base or hall', required=False)
parser.add_argument('-out', '--output_file', help='Where NDSI image is to be saved', required=True)
args = parser.parse_args()

multi_band_file = args.MS_input_file
swir_file = args.SWIR_input_file
sensor = args.input_satellite
NDSI_type = args.input_thresh
NDSI_file = args.output_file

# Dictionary of data type conversions between gdal and numpy
GDAL2NUMPY_DATA_TYPE_CONVERSION = {
  1: "uint8",
  2: "uint16",
  3: "int16",
  4: "uint32",
  5: "int32",
  6: "float32",
  7: "float64",
  10: "complex64",
  11: "complex128",
}


# Extract the green, NIR, and SWIR bands (should be TOA reflectance values)
if sensor == 'WV3':
    ms_noext = multi_band_file[:-4]
    swir_noext = swir_file[:-4]

    # Open single-band files as general access read only
    multi_band_dataset = gdal.Open(ms_noext + "_b3_toa_refl.tif", gdal.GA_ReadOnly)
    green_band = multi_band_dataset.GetRasterBand(1)
    print(green_band.XSize)
    nir_band = gdal.Open(ms_noext + "_b7_toa_refl.tif", gdal.GA_ReadOnly).GetRasterBand(1)
    swir_band = gdal.Open(swir_noext + "_b3_toa_refl.tif", gdal.GA_ReadOnly).GetRasterBand(1)
#     dn_range = 1    
    
else:
    # L8 sensor level 1 imagery
    green = 3
    nir = 5
    swir = 6
#     dn_range = 1

    # Open single-band files as general access read only
    multi_band_dataset = gdal.Open(multi_band_file, gdal.GA_ReadOnly)  
    green_band = multi_band_dataset.GetRasterBand(green)
    nir_band = multi_band_dataset.GetRasterBand(nir)
    swir_band = multi_band_dataset.GetRasterBand(swir)


# Print out general information on dataset - choose green band
print(multi_band_file, "Driver:", multi_band_dataset.GetDriver().ShortName, 
      "/", multi_band_dataset.GetDriver().LongName)
print(multi_band_file, "Size:", multi_band_dataset.RasterXSize, "x", 
      multi_band_dataset.RasterYSize, "x", multi_band_dataset.RasterCount)

xsize = green_band.XSize
ysize = green_band.YSize

#Create NDSI output raster with specific raster format
driver = gdal.GetDriverByName('GTiff')

NDSI_dataset = driver.Create(
    NDSI_file,
    multi_band_dataset.RasterXSize,
    multi_band_dataset.RasterYSize,
    1, # number of output bands -- just need one for NDSI
    6,) # float32

# Match the geotransform and projection to that of the input image
NDSI_dataset.SetGeoTransform(multi_band_dataset.GetGeoTransform())
NDSI_dataset.SetProjection(multi_band_dataset.GetProjection())
# NDSI_dataset.GetRasterBand(1).SetNoDataValue(-32768)

# Populate NDSI raster, use data blocks to save on memory usage
#block_sizes = green_band.GetBlockSize()
    # Set to 1024 x 1024 - when gdalwarping WV3 imagery in previous steps to get to toa_refl, these are getting messed around along the way...
x_block_size = 1024 #block_sizes[0]
y_block_size = 1024 #block_sizes[1]
    
blocks = 0

# loop through rows
for y in range(0, ysize, y_block_size):
    if y + y_block_size < ysize:
        rows = y_block_size
    else:
        rows = ysize - y
    print(rows)
    # Loop through columns
    for x in range(0, xsize, x_block_size):
        if x + x_block_size < xsize:
            cols = x_block_size
        else:
            cols = xsize - x
        print(cols)
        # Read GDAL dataset as numpy array of specified type
        green_band_array = green_band.ReadAsArray(x, y, cols, rows).astype('float32')
        print("green read")

        nir_band_array = nir_band.ReadAsArray(x, y, cols, rows).astype('float32')
        print("nir read")

        swir_band_array = swir_band.ReadAsArray(x, y, cols, rows).astype('float32')
        print("swir read")        
        
        # Omit pixels with negative reflectance values or reflectance values > 1
        green_band_array = (green_band_array >= 0) & (green_band_array <=1)
        nir_band_array = (nir_band_array >= 0) & (nir_band_array <=1)
        swir_band_array = (swir_band_array >= 0) & (swir_band_array <=1)

        # Mask values which are undefined due to zero division (Green + SWIR = 0)
        mask_array = np.not_equal((green_band_array + swir_band_array), 0)
        
        # Calculate NDSI values and put into separate array
        ndsi_array = np.choose(mask_array, (-32768, (green_band_array - swir_band_array) / (green_band_array + swir_band_array)))

        # Adjust NDSI values based on threshold method
        if NDSI_type == "hall":
            # implement threshold based on nir and green values
            ndsi_array = np.where((ndsi_array >= 0.4) & (ndsi_array <= 1.0) & (nir_band_array>=0.1) & (green_band_array>=0.1), ndsi_array, -32768)
        
        NDSI_dataset.GetRasterBand(1).WriteArray(ndsi_array.astype('float32'), x, y)
#         print(ndsi_array.shape, type(ndsi_array), ndsi_array.min(), ndsi_array.max())


        green_band_array = None
        swir_band_array = None
        nir_band_array = None
        mask_array = None
        ndsi_array = None

        blocks += 1

# Set dataset and bands to None to clear memory usage
green_band = None
swir_band = None
nir_band = None
multi_band_dataset = None
NDSI_dataset = None
