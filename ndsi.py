#!/usr/bin/env python

# Calculate Normalized Difference Snow Index from DigitalGlobe data imagery
# that are already aligned and orthorectified
# Adapted from http://gencersumbul.bilkent.edu.tr/post/gdal_scripts/

# import libraries
from gdalconst import *
import argparse, numpy as np,  gdal, struct, sys

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

# Have user define multi-band raster and output filename
parser = argparse.ArgumentParser(description='GeoTiff Multi Spectral Image to NDVI Image Conversion Script with Normalized Difference Vegetation Index Measurement')
parser.add_argument('-in', '--input_file', help='GeoTiff multi band MS image file', required=True)
parser.add_argument('-in_sensor', '--input_satellite', help='String of satellite', required=True)
parser.add_argument('-out', '--output_file', help='Where NDVI image is to be saved', required=True)
args = parser.parse_args()

multi_band_file = args.input_file
sensor = args.input_satellite
NDSI_file = args.output_file


#Open multi-band file as general access read only
multi_band_dataset = gdal.Open(multi_band_file, GA_ReadOnly)
print(multi_band_file, "Driver:", multi_band_dataset.GetDriver().ShortName, "/", multi_band_dataset.GetDriver().LongName)
print(multi_band_file, "Size:", multi_band_dataset.RasterXSize, "x", multi_band_dataset.RasterYSize, "x", multi_band_dataset.RasterCount)

#Extract the green and SWIR bands and sizes from WV3 and L8 imagery
if sensor == 'WV3':
    green = 1
    swir = 4
else:
    green = 3
    swir = 6

green_band = multi_band_dataset.GetRasterBand(green)
swir_band = multi_band_dataset.GetRasterBand(swir)

xsize = green_band.XSize
ysize = green_band.YSize

#Create NVDI output raster with specific raster format
driver = gdal.GetDriverByName('GTiff')

NDSI_dataset = driver.Create(
    NDSI_file,
    multi_band_dataset.RasterXSize,
    multi_band_dataset.RasterYSize,
    1, # number of output bands -- just need one for NDSI
    6,) #float32

# Match the geotransform and projection to that of the input image
NDSI_dataset.SetGeoTransform(multi_band_dataset.GetGeoTransform())
NDSI_dataset.SetProjection(multi_band_dataset.GetProjection())

# Populate NDSI raster, use data blocks to save on memory usage
block_sizes = green_band.GetBlockSize()
x_block_size = block_sizes[0]
y_block_size = block_sizes[1]

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
        green_band_array = green_band.ReadAsArray(x, y, cols, rows).astype('float32')
        swir_band_array = swir_band.ReadAsArray(x, y, cols, rows).astype('float32')

        # Mask values which are undefined due to zero division (NIR + Red = 0)
        mask_array = np.not_equal((green_band_array + swir_band_array), 0)
        ndsi_array = np.choose(mask_array, (-32768, (green_band_array - swir_band_array) / (swir_band_array + green_band_array)))
        NDSI_dataset.GetRasterBand(1).WriteArray(ndsi_array.astype('float32'), x, y)

        del green_band_array
        del swir_band_array
        del mask_array
        del ndsi_array

        blocks += 1

# Set dataset and bands to None to clear memory usage
green_band = None
swir_band = None
multi_band_dataset = None
NDSI_dataset = None
