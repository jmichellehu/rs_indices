#!/usr/bin/env python

# Calculate Normalized Difference Snow Index from WV-3 top-of-atmosphere reflectance imagery and Level 1 Landsat 8 imagery.

import sys
import argparse
import struct

# import third party
import numpy as np
from osgeo import gdal
import rasterio as rio

# Have user define input and output image filenames
parser = argparse.ArgumentParser(description='NDSI Calculation Script with Normalized Difference Snow Index Measurement')
parser.add_argument('-in', '--MS_input_file', help='Multiband MS image file', required=False)
parser.add_argument('-in2', '--SWIR_input_file', help='Multiband SWIR image file for WV3', required=False)
parser.add_argument('-out', '--output_file', help='Where NDSI image is to be saved', required=True)
parser.add_argument('-g', '--green_band', help='Single band green channel input', required=False)
parser.add_argument('-s3', '--swir_3_band', help='Single band SWIR input', required=False)
parser.add_argument('-res', '--px_res', help='Pixel resolution, default is 1.2 m', required=False)


args = parser.parse_args()
multi_band_file = args.MS_input_file
swir_file = args.SWIR_input_file
out_fn = args.output_file

green_fn=args.green_band
s3_fn=args.swir_3_band
px_res=args.px_res

# Assign pixel resolution if no input
if px_res is None:
    px_res="1.2"
    p_name="12"
else:
    p_name=px_res[0]+px_res[-1]

# Extract reflectance as numpy arrays from proper bands (TOA or SR)    
try:
    with rio.open(multi_band_file[:-4] + "_b3_" + p_name + "_refl.tif") as f:
        green_arr=f.read()
        prf=f.profile
        g_ndv=f.nodata

    with rio.open(swir_file[:-4] + "_b3_" + p_name + "_refl.tif") as f:
#     with rio.open(swir_file[:-4] + "_" + multi_band_file[:-4] + "_b3_12_refl.tif") as f:        
        swir3_arr=f.read()
        swir3_ndv=f.nodata
except:
    with rio.open(green_fn) as f:
        green_arr=f.read()
        prf=f.profile
        g_ndv=f.nodata

    with rio.open(s3_fn) as f:
        swir3_arr=f.read()
        swir3_ndv=f.nodata

# Calculate NDSI
# NDSI = (green - swir) / (green + swir)
ndsi_3 = (green_arr - swir3_arr) / (green_arr + swir3_arr)

# Create normalized ndsi array from 0-1 for further processing
# With min-max scaling
ndsi_3_norm = (ndsi_3+1)/2

ndsi_ndv=9999

# Mask with ndv areas from green and swir arrays
ndsi_3[green_arr==g_ndv]=ndsi_ndv
ndsi_3[swir3_arr==swir3_ndv]=ndsi_ndv

ndsi_3_norm[green_arr==g_ndv]=ndsi_ndv
ndsi_3_norm[swir3_arr==swir3_ndv]=ndsi_ndv

# Write these to array
with rio.Env():
    prf.update(
        dtype=rio.float32,
        count=1,
        compress='lzw')

    with rio.open(out_fn, 'w', **prf) as dst:
        dst.write(np.squeeze(ndsi_3).astype(rio.float32), 1)

    with rio.open(out_fn[:-4]+"_minmax.tif", 'w', **prf) as dst:
        dst.write(np.squeeze(ndsi_3_norm).astype(rio.float32), 1)