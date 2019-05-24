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

# Have user define input and output image filenames
parser = argparse.ArgumentParser(description='Multispectral Image to NDSI Image Conversion Script with Normalized Difference Snow Index Measurement')
parser.add_argument('-in', '--MS_input_file', help='Multiband MS image file', required=True)
parser.add_argument('-in2', '--SWIR_input_file', help='Multiband SWIR image file for WV3', required=False)
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
    nir_dataset = gdal.Open(ms_noext + "_b7_toa_refl.tif", gdal.GA_ReadOnly)
    swir_dataset = gdal.Open(swir_noext + "_b3_toa_refl.tif", gdal.GA_ReadOnly)
    nir_band = nir_dataset.GetRasterBand(1)
    swir_band = swir_dataset.GetRasterBand(1)

else:
    # L8 sensor level 1 imagery
    green = 3
    nir = 5
    swir = 6

    # Open single-band files as general access read only
    multi_band_dataset = gdal.Open(multi_band_file, gdal.GA_ReadOnly)
    green_band = multi_band_dataset.GetRasterBand(green)
    nir_band = multi_band_dataset.GetRasterBand(nir)
    swir_band = multi_band_dataset.GetRasterBand(swir)


# Print out general information on dataset - choose green band
print(multi_band_file,
      "Driver:", multi_band_dataset.GetDriver().ShortName,
      "/", multi_band_dataset.GetDriver().LongName)
print(multi_band_file,
      "Size:", multi_band_dataset.RasterXSize,
      "x", multi_band_dataset.RasterYSize,
      "x", multi_band_dataset.RasterCount)

xsize = green_band.XSize
ysize = green_band.YSize

# Populate NDSI raster, use data blocks to save on memory usage

#block_sizes = green_band.GetBlockSize()

# Set to 1024 x 1024 - when gdalwarping WV3 imagery in previous steps to get to toa_refl, these are getting messed around along the way because you are setting them in the options (see below)
x_block_size = 1024 #block_sizes[0]
y_block_size = 1024 #block_sizes[1]


#Create NDSI output raster with specific raster format
driver = gdal.GetDriverByName('GTiff')

NDSI_dataset = driver.Create(
    NDSI_file,
    multi_band_dataset.RasterXSize,
    multi_band_dataset.RasterYSize,
    1, # number of output bands -- just need one for NDSI
    6, # float32
    options=['TILED=YES',
             'BLOCKXSIZE=%i' % x_block_size,
             'BLOCKYSIZE=%i' % y_block_size,
             'BIGTIFF=IF_SAFER',
             'COMPRESS=LZW',
            ])

# Match the geotransform and projection to that of the input image
NDSI_dataset.SetGeoTransform(multi_band_dataset.GetGeoTransform())
NDSI_dataset.SetProjection(multi_band_dataset.GetProjection())

ndsi_band_out = NDSI_dataset.GetRasterBand(1)
ndsi_band_out.SetNoDataValue(-32768)

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
        green_band_array = green_band.ReadAsArray(x, y, cols, rows).astype('float32')
        nir_band_array = nir_band.ReadAsArray(x, y, cols, rows).astype('float32')
        swir_band_array = swir_band.ReadAsArray(x, y, cols, rows).astype('float32')

        # Calculate NDSI
        ndsi_array = (green_band_array - swir_band_array) / (green_band_array + swir_band_array)

        # Create mask of valid pixels - those with positive reflectance values <=1 in the green and swir bands.  Work around green + swir = 0 in denominator
        green_swir_mask = (green_band_array > 0) & (green_band_array <=1) & (swir_band_array >= 0) & (swir_band_array <=1)
        ndsi_array = np.ma.array(ndsi_array, mask=~(green_swir_mask), fill_value=-32768)

        # Adjust NDSI values based on modified version of Hall's threshold method
        if NDSI_type == "hall":
            hall_mask = (nir_band_array >= 0.1) & (nir_band_array <=1) & (ndsi_array >= 0.4) & (ndsi_array <= 1.0) & (green_band_array>=0.1)
            ndsi_array=np.ma.array(ndsi_array, mask=~(hall_mask), fill_value=-32768)

        # Write this chunk to memory
        ndsi_band_out.WriteArray(ndsi_array, x, y)

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
