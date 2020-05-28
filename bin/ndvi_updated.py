#!/usr/bin/env python

# Script to calculate Normalized Difference Vegetation Index from input imagery (with WV-2 and WV-3 MS band or single-band inputs).
# NDVI = (red - nir) / (red + nir)
    
import argparse
import numpy as np
import rasterio as rio

def read_file(fn):
    with rio.open(fn) as f:
        arr=f.read()
        prf=f.profile
        ndv=f.nodata
    return arr, prf, ndv
    
def calc_ndvi(red_arr, nir1_arr, r_ndv=None, nir1_ndv=None):
    # Calculate NDVI
    ndvi = (nir1_arr - red_arr) / (nir1_arr + red_arr)

    # Create normalized ndvi array from 0-1 for further processing with min-max scaling
    ndvi_norm = (ndvi+1)/2

    # Mask with ndv areas from original arrays
    ndvi[red_arr==r_ndv]=r_ndv
    ndvi[nir1_arr==nir1_ndv]=nir1_ndv

    ndvi_norm[red_arr==r_ndv]=r_ndv
    ndvi_norm[nir1_arr==nir1_ndv]=nir1_ndv
    
    return ndvi, ndvi_norm

def run(multi_band_file, out_fn, nir1_fn, red_fn, px_res, p_name):
    if multi_band_file is not None:
        red_arr, prf, r_ndv = read_file(multi_band_file[:-4] + "_b5_" + p_name + "_refl.tif")
        nir1_arr, _, nir1_ndv = read_file(multi_band_file[:-4] + "_b7_" + p_name + "_refl.tif")
    elif red_fn is not None:
        red_arr, prf, r_ndv = read_file(red_fn)
        nir1_arr, _, nir1_ndv = read_file(nir1_fn)
            
    ndvi, ndvi_norm = calc_ndvi(red_arr, nir1_arr, r_ndv, nir1_ndv)
    
    # Write NDVI arrays to file
    with rio.Env():
        prf.update(
            dtype=rio.float32,
            count=1,
            compress='lzw')
        with rio.open(out_fn, 'w', **prf) as dst:
            dst.write(np.squeeze(ndvi).astype(rio.float32), 1)
        with rio.open(out_fn[:-4]+"_minmax.tif", 'w', **prf) as dst:
            dst.write(np.squeeze(ndvi_norm).astype(rio.float32), 1)

def get_parser():
    parser = argparse.ArgumentParser(description='Normalized Difference Vegetation Index Calculation Script')
    parser.add_argument('-in', '--MS_input_file', help='Multiband MS image file', required=False)
    parser.add_argument('-out', '--output_file', help='NDVI output filename', default="ndvi.tif",  required=False)
    parser.add_argument('-r', '--red_band', help='Single-band red input', required=False)
    parser.add_argument('-n', '--nir_band', help='Single-band NIR channel input', required=False)
    parser.add_argument('-res', '--px_res', help='Pixel resolution, default is 1.2m', default="1.2", required=False)
    return parser

def main():
    parser = get_parser()
    args = parser.parse_args()
    in_fn = args.MS_input_file
    out_fn = args.output_file

    nir1_fn=args.nir_band
    red_fn=args.red_band
    px_res=args.px_res    
    p_name=px_res[0]+px_res[-1]

    run(in_fn, out_fn, nir1_fn, red_fn, px_res, p_name)
    
if __name__ == "__main__":    
    main()