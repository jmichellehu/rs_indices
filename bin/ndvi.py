#!/usr/bin/env python

# Calculate NDVI from input imagery that is already aligned and orthorectified
# Adapted from http://gencersumbul.bilkent.edu.tr/post/gdal_scripts/


# import libraries
from gdalconst import *
import argparse, numpy as np, gdal, struct, sys

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
parser.add_argument('-in', '--input_file', help='GeoTiff multi band image file', required=True)
parser.add_argument('-in_sensor', '--input_satellite', help='String of satellite', required=True)
parser.add_argument('-out', '--output_file', help='Where NDVI image is to be saved', required=True)
args = parser.parse_args()

multi_band_file = args.input_file
sensor = args.input_satellite
NDVI_file = args.output_file


#Open multi-band file as general access read only
multi_band_dataset = gdal.Open(multi_band_file, GA_ReadOnly)
print(multi_band_file, "Driver:", multi_band_dataset.GetDriver().ShortName, "/", multi_band_dataset.GetDriver().LongName)
print(multi_band_file, "Size:", multi_band_dataset.RasterXSize, "x", multi_band_dataset.RasterYSize, "x", multi_band_dataset.RasterCount)

#Extract the red and near-infrared bands and sizes the input imagery

if sensor == 'WV3':
    red = 2
    nir = 3
elif sensor == 'Planet':
    red = 3
    nir = 4
else:
    red = 4
    nir = 5

red_band = multi_band_dataset.GetRasterBand(red)
infrared_band = multi_band_dataset.GetRasterBand(nir)

xsize = red_band.XSize
ysize = red_band.YSize

#Create NVDI output raster with specific raster format
driver = gdal.GetDriverByName('GTiff')

NDVI_dataset = driver.Create(
    NDVI_file,
    multi_band_dataset.RasterXSize,
    multi_band_dataset.RasterYSize,
    1, # number of output bands -- just need one for NDVI
    6,) #float32

# Match the geotransform and projection to that of the input image
NDVI_dataset.SetGeoTransform(multi_band_dataset.GetGeoTransform())
NDVI_dataset.SetProjection(multi_band_dataset.GetProjection())

# Populate NDVI raster, use data blocks to save on memory usage
block_sizes = red_band.GetBlockSize()
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
        red_band_array = red_band.ReadAsArray(x, y, cols, rows).astype('float32')
        infrared_band_array = infrared_band.ReadAsArray(x, y, cols, rows).astype('float32')

        # Mask values which are undefined due to zero division (NIR + Red = 0)
        mask_array = np.not_equal((red_band_array + infrared_band_array), 0)
        ndvi_array = np.choose(mask_array, (-32768, (infrared_band_array - red_band_array) / (infrared_band_array + red_band_array)))
        NDVI_dataset.GetRasterBand(1).WriteArray(ndvi_array.astype('float32'), x, y)

        del red_band_array
        del infrared_band_array
        del mask_array
        del ndvi_array

        blocks += 1

# Set dataset and bands to None to clear memory usage

red_band = None
infrared_band = None
multi_band_dataset = None
NDVI_dataset = None
