#!/usr/bin/env python

# Calculate Normalized Difference Snow Index from orthorectified, resampled, and clipped WV-3 top-of-atmosphere reflectance imagery, Landsat 8 Level 1 imagery, and Planet Level 3B SR imagery.

# Adapted from http://gencersumbul.bilkent.edu.tr/post/gdal_scripts/

# system libraries and imports
import sys
import argparse
import struct

# import third party
import numpy as np
from osgeo import gdal

# Have user define input and output image filenames
parser = argparse.ArgumentParser(description='GeoTiff Multi Spectral Image to NDVI Image Conversion Script with Normalized Difference Vegetation Index Measurement')
parser.add_argument('-in', '--input_file', help='Multiband MS image file', required=True)
parser.add_argument('-in_sensor', '--input_satellite', help='Sensor name - either WV3 or L8', required=True)
parser.add_argument('-out', '--output_file', help='Where NDVI image is to be saved', required=True)
args = parser.parse_args()

multi_band_file = args.input_file
sensor = args.input_satellite
NDVI_file = args.output_file

# dictionary of data type conversion between gdal and numpy
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

# Extract the red and NIR bands (should be TOA reflectance values)
if sensor == 'WV3':
    # Remove file extension
    ms_noext = multi_band_file[:-4]
    
    # Open single-band files as general access read only
    multi_band_dataset = gdal.Open(ms_noext + "_b5_toa_refl.tif", gdal.GA_ReadOnly)
    red_band = multi_band_dataset.GetRasterBand(1)
    
    nir_dataset = gdal.Open(ms_noext + "_b7_toa_refl.tif", gdal.GA_ReadOnly)
    nir_band = nir_dataset.GetRasterBand(1)

else:
    if sensor == 'Planet':
        red = 3
        nir = 4
    else:
        # L8 sensor level 1 imagery
        red = 4
        nir = 5

    # Open single-band files as general access read only
    multi_band_dataset = gdal.Open(multi_band_file, gdal.GA_ReadOnly)  
    red_band = multi_band_dataset.GetRasterBand(red)
    nir_band = multi_band_dataset.GetRasterBand(nir)

# Print out general information on dataset
print(multi_band_file, 
      "Driver:", multi_band_dataset.GetDriver().ShortName, 
      "/", multi_band_dataset.GetDriver().LongName)
print(multi_band_file, 
      "Size:", multi_band_dataset.RasterXSize, 
      "x", multi_band_dataset.RasterYSize, 
      "x", multi_band_dataset.RasterCount)

# Extract rows and columns of bands
xsize = red_band.XSize
ysize = red_band.YSize

# Populate NDSI raster, use data blocks to save on memory usage
#block_sizes = green_band.GetBlockSize()
# Set to 1024 x 1024 - when gdalwarping WV3 imagery in previous steps to get to toa_refl, these are getting messed around along the way because you are setting them in the options (see below)
x_block_size = 1024 #block_sizes[0]
y_block_size = 1024 #block_sizes[1]

# Create NDVI output raster with specific raster format
driver = gdal.GetDriverByName('GTiff')

NDVI_dataset = driver.Create(
    NDVI_file,
    multi_band_dataset.RasterXSize,
    multi_band_dataset.RasterYSize,
    1, # number of output bands -- just need one for NDVI
    6, #float32
    options=['TILED=YES', 
             'BLOCKXSIZE=%i' % x_block_size, 
             'BLOCKYSIZE=%i' % y_block_size, 
             'BIGTIFF=IF_SAFER', 
             'COMPRESS=LZW',
            ])

# Match the geotransform and projection to that of the input image
NDVI_dataset.SetGeoTransform(multi_band_dataset.GetGeoTransform())
NDVI_dataset.SetProjection(multi_band_dataset.GetProjection())

ndvi_band_out = NDVI_dataset.GetRasterBand(1)
ndvi_band_out.SetNoDataValue(-32768)

blocks = 0

# loop through rows
for y in range(0, ysize, y_block_size):
    if y + y_block_size < ysize:
        rows = y_block_size
    else:
        rows = ysize - y
    # Loop through columns
    for x in range(0, xsize, x_block_size):
        if x + x_block_size < xsize:
            cols = x_block_size
        else:
            cols = xsize - x
        
        # Read GDAL dataset as numpy array of specified type
        red_band_array = red_band.ReadAsArray(x, y, cols, rows).astype('float32')
        nir_band_array = nir_band.ReadAsArray(x, y, cols, rows).astype('float32')

        # Calculate NDVI
        ndvi_array = (nir_band_array - red_band_array) / (nir_band_array + red_band_array)
        
        # Create mask of valid pixels - positive reflectance values <=1
        valid_mask = (red_band_array >= 0) & (red_band_array <=1) & (nir_band_array >= 0) & (nir_band_array <= 1)        
        ndvi_array = np.ma.array(ndvi_array, mask=red_nir_mask, fill_value=-32768)
        ndvi_band_out.WriteArray(ndvi_array, x, y)

        red_band_array = None
        nir_band_array = None
        mask_array = None
        ndvi_array = None

        blocks += 1

# Set dataset and bands to None to clear memory usage
red_band = None
nir_band = None
multi_band_dataset = None
NDVI_dataset = None
