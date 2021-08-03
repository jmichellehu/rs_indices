#!/usr/bin/env python

# Calculate Normalized Difference Snow Foreset Index from WV-3 top-of-atmosphere reflectance imagery.
# As in https://www.mdpi.com/2072-4292/7/12/15882/pdf nir1 and swir2

# LANDSAT OLI BAND 5 NIR 845–885
# LANDSAT OLI BAND 6 SWIR2 1560–1660

# WV-3
    # Near-IR1: 770 - 895 nm
    # Near-IR2: 860 - 1040 nm

# 8 SWIR Bands:
    # SWIR-2: 1550 - 1590 nm
    # SWIR-3: 1640 - 1680 nm

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
parser.add_argument('-out', '--output_file', help='Where NDFSI image is to be saved', required=True)
parser.add_argument('-n', '--nir_band', help='Single band NIR 1 input', required=False)
parser.add_argument('-s2', '--swir_2_band', help='Single band SWIR 2 input', required=False)
parser.add_argument('-res', '--px_res', help='Pixel resolution, default is 1.2 m', required=False)


args = parser.parse_args()
multi_band_file = args.MS_input_file
swir_file = args.SWIR_input_file
out_fn = args.output_file

nir1_fn=args.nir_band
s2_fn=args.swir_2_band
px_res=args.px_res

# Assign pixel resolution if no input
if px_res is None:
    px_res="1.2"
    p_name="12"
else:
    p_name=px_res[0]+px_res[-1]

# Extract reflectance as numpy arrays from proper bands (TOA or SR)    
try:
    with rio.open(multi_band_file[:-4] + "_b7_" + p_name + "_refl.tif") as f:
        nir1_arr=f.read()
        prf=f.profile
        nir1_ndv=f.nodata

    with rio.open(swir_file[:-4] + "_b2_" + p_name + "_refl.tif") as f:
#     with rio.open(swir_file[:-4] + "_" + multi_band_file[:-4] + "_b3_12_refl.tif") as f:        
        swir2_arr=f.read()
        swir2_ndv=f.nodata
except:
    with rio.open(nir1_fn) as f:
        nir1_arr=f.read()
        prf=f.profile
        nir1_ndv=f.nodata

    with rio.open(s2_fn) as f:
        swir2_arr=f.read()
        swir2_ndv=f.nodata

# Calculate NDFSI
ndfsi = (nir1_arr - swir2_arr) / (nir1_arr + swir2_arr)

# Create normalized ndfsi array from 0-1 for further processing
# With min-max scaling
ndfsi_norm = (ndfsi+1)/2

# Mask with ndv areas from green and swir arrays
ndfsi[nir1_arr==nir1_ndv]=nir1_ndv
ndfsi[swir2_arr==swir2_ndv]=swir2_ndv

ndfsi_norm[nir1_arr==nir1_ndv]=nir1_ndv
ndfsi_norm[swir2_arr==swir2_ndv]=swir2_ndv

# Write these to array
with rio.Env():
    prf.update(
        dtype=rio.float32,
        count=1,
        compress='lzw')

    with rio.open(out_fn, 'w', **prf) as dst:
        dst.write(np.squeeze(ndfsi).astype(rio.float32), 1)

    with rio.open(out_fn[:-4]+"_minmax.tif", 'w', **prf) as dst:
        dst.write(np.squeeze(ndfsi_norm).astype(rio.float32), 1)