#!/usr/bin/env python

# Calculate Normalized Difference Water Index from WV-3 top-of-atmosphere reflectance imagery.
# ***McFeeters version
import sys
import argparse
import struct

# import third party
import numpy as np
from osgeo import gdal
import rasterio as rio

# Have user define input and output image filenames
parser = argparse.ArgumentParser(description='NDWI Calculation Script with Normalized Difference Vegetation Index Measurement')
parser.add_argument('-in', '--MS_input_file', help='Multiband MS image file', required=True)
parser.add_argument('-out', '--output_file', help='Where NDWI image is to be saved', required=True)
parser.add_argument('-g', '--green_band', help='Single band green input', required=False)
parser.add_argument('-n', '--nir_band', help='Single band NIR channel input', required=False)
parser.add_argument('-res', '--px_res', help='Pixel resolution, default is 1.2 m', required=False)

args = parser.parse_args()
multi_band_file = args.MS_input_file
out_fn = args.output_file

nir1_fn=args.nir_band
green_fn=args.green_band
px_res=args.px_res

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

    with rio.open(multi_band_file[:-4] + "_b7_" + p_name + "_refl.tif") as f:
        nir1_arr=f.read()
        nir1_ndv=f.nodata
        
except:
    with rio.open(green_fn) as f:
        green_arr=f.read()
        prf=f.profile
        g_ndv=f.nodata

    with rio.open(nir1_fn) as f:
        nir1_arr=f.read()
        nir1_ndv=f.nodata

# Calculate NDVI
ndwi = (green_arr - nir1_arr) / (green_arr + nir1_arr)

# Create normalized ndsi array from 0-1 for further processing
# With min-max scaling
ndwi_norm = (ndwi+1)/2

ndwi_ndv=9999

# Mask with ndv areas from green and swir arrays
ndwi[green_arr==g_ndv]=ndwi_ndv
ndwi[nir1_arr==nir1_ndv]=ndwi_ndv

ndwi_norm[green_arr==g_ndv]=ndwi_ndv
ndwi_norm[nir1_arr==nir1_ndv]=ndwi_ndv

# Write these to array
with rio.Env():
    prf.update(
        dtype=rio.float32,
        count=1,
        compress='lzw')

    with rio.open(out_fn, 'w', **prf) as dst:
        dst.write(np.squeeze(ndwi).astype(rio.float32), 1)

    with rio.open(out_fn[:-4]+"_minmax.tif", 'w', **prf) as dst:
        dst.write(np.squeeze(ndwi_norm).astype(rio.float32), 1)
