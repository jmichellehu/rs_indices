#!/usr/bin/env python

# Calculate Normalized Difference Snow Index from WV-3 top-of-atmosphere reflectance imagery.

import sys
import argparse
import struct

# import third party
import numpy as np
from osgeo import gdal
import rasterio as rio

# Have user define input and output image filenames
parser = argparse.ArgumentParser(description='NDVI Calculation Script with Normalized Difference Vegetation Index Measurement')
parser.add_argument('-in', '--MS_input_file', help='Multiband MS image file', required=True)
parser.add_argument('-out', '--output_file', help='Where NDVI image is to be saved', required=True)
parser.add_argument('-r', '--red_band', help='Single band red input', required=False)
parser.add_argument('-n', '--nir_band', help='Single band NIR channel input', required=False)
parser.add_argument('-res', '--px_res', help='Pixel resolution, default is 1.2 m', required=False)

args = parser.parse_args()
multi_band_file = args.MS_input_file
out_fn = args.output_file

nir1_fn=args.nir_band
red_fn=args.red_band
px_res=args.px_res

if px_res is None:
    px_res="1.2"
    p_name="12"
else:
    p_name=px_res[0]+px_res[-1]

# Extract reflectance as numpy arrays from proper bands (TOA or SR)    
try:
    with rio.open(multi_band_file[:-4] + "_b5_" + p_name + "_refl.tif") as f:
        red_arr=f.read()
        prf=f.profile
        r_ndv=f.nodata

    with rio.open(multi_band_file[:-4] + "_b7_" + p_name + "_refl.tif") as f:
        nir1_arr=f.read()
        nir1_ndv=f.nodata
        
except:
    with rio.open(r_fn) as f:
        red_arr=f.read()
        prf=f.profile
        r_ndv=f.nodata

    with rio.open(nir1_fn) as f:
        nir1_arr=f.read()
        nir1_ndv=f.nodata

# Calculate NDVI
ndvi = (nir1_arr - red_arr) / (nir1_arr + red_arr)

# Create normalized ndsi array from 0-1 for further processing
# With min-max scaling
ndvi_norm = (ndvi+1)/2

# Mask with ndv areas from green and swir arrays
ndvi[red_arr==r_ndv]=r_ndv
ndvi[nir1_arr==nir1_ndv]=nir1_ndv

ndvi_norm[red_arr==r_ndv]=r_ndv
ndvi_norm[nir1_arr==nir1_ndv]=nir1_ndv

# Write these to array
with rio.Env():
    prf.update(
        dtype=rio.float32,
        count=1,
        compress='lzw')

    with rio.open(out_fn, 'w', **prf) as dst:
        dst.write(np.squeeze(ndvi).astype(rio.float32), 1)

    with rio.open(out_fn[:-4]+"_minmax.tif", 'w', **prf) as dst:
        dst.write(np.squeeze(ndvi_norm).astype(rio.float32), 1)