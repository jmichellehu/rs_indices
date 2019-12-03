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
parser.add_argument('-in', '--MS_input_file', help='Multiband MS image file', required=True)
parser.add_argument('-in2', '--SWIR_input_file', help='Multiband SWIR image file for WV3', required=False)
parser.add_argument('-out', '--output_file', help='Where NDSI image is to be saved', required=True)
parser.add_argument('-g', '--green_band', help='Single band green channel input', required=False)
parser.add_argument('-s3', '--swir_3_band', help='Single band SWIR input', required=False)

args = parser.parse_args()
multi_band_file = args.MS_input_file
swir_file = args.SWIR_input_file
out_fn = args.output_file

green_fn=args.green_band
s3_fn=args.swir_3_band

# Extract reflectance as numpy arrays from proper bands (TOA or SR)    
try:
    with rio.open(multi_band_file[:-4] + "_b3_toa_refl.tif") as f:
        green_arr=f.read()
        prf=f.profile
        g_ndv=f.nodata

    with rio.open(swir_file[:-4] + "_" + multi_band_file[:-4] + "_b3_toa_refl.tif") as f:
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
# In ndsi.py script, NDSI is calculated with values (0, 1] for both green and SWIR bands
ndsi_3= (green_arr - swir3_arr) / (green_arr + swir3_arr)

# Mask with ndv areas from green and swir arrays
ndsi_3[green_arr==g_ndv]=g_ndv
ndsi_3[swir3_arr==swir3_ndv]=swir3_ndv

# Write these to array
with rio.Env():
    prf.update(
        dtype=rio.float32,
        count=1,
        compress='lzw')

    with rio.open(out_fn, 'w', **prf) as dst:
        dst.write(np.squeeze(ndsi_3).astype(rio.float32), 1)
        
# # Do not institute low and high bounds for initial reflectance values right now.
# # Adjust with out of bounds green and swir reflectance values
# ndsi_3[green_arr<0]=g_ndv
# ndsi_3[swir3_arr<0]=swir3_ndv
# ndsi_3[green_arr>1]=g_ndv
# ndsi_3[swir3_arr>1]=swir3_ndv

# # And write to array
# with rio.Env():
#     # Change the band count to 1, set the
#     # dtype to float 32, and specify LZW compression.
#     prf.update(
#         dtype=rio.float32,
#         count=1,
#         compress='lzw')
#     with rio.open(out_fn_3_adj, 'w', **prf) as dst:
#         dst.write(np.squeeze(ndsi_3).astype(rio.float32), 1)