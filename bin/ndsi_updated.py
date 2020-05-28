#!/usr/bin/env python

# Script to calculate Normalized Difference Snow Index from input imagery (with a WV-3 MS band or single-band inputs).
# NDSI = (green - swir) / (green + swir)

import argparse
import numpy as np
import rasterio as rio

def read_file(fn):
    with rio.open(fn) as f:
        arr=f.read()
        prf=f.profile
        ndv=f.nodata
    return arr, prf, ndv

def calc_ndsi(green_arr, swir3_arr, g_ndv=None, swir3_ndv=None):
    # Calculate NDSI
    ndsi_3 = (green_arr - swir3_arr) / (green_arr + swir3_arr)

    # Create normalized ndsi array from 0-1 for further processing with min-max scaling
    ndsi_3_norm = (ndsi_3+1)/2
    
    # Mask with ndv areas from original arrays
    ndsi_3[green_arr==g_ndv]=ndsi_ndv
    ndsi_3[swir3_arr==swir3_ndv]=ndsi_ndv

    ndsi_3_norm[green_arr==g_ndv]=ndsi_ndv
    ndsi_3_norm[swir3_arr==swir3_ndv]=ndsi_ndv
    
    return ndsi_3, ndsi_3_norm

def run(multi_band_file, swir_file, out_fn, green_fn, s3_fn, px_res, p_name):
    if (multi_band_file is not None) & (swir_file is not None):
        green_arr, prf, g_ndv = read_file(multi_band_file[:-4] + "_b3_" + p_name + "_refl.tif")
        swir3_arr, _, swir3_ndv = read_file(swir_file[:-4] + "_b3_" + p_name + "_refl.tif")
    elif (green_fn is not None) & (s3_fn is not None):
        green_arr, prf, g_ndv = read_file(green_fn)
        swir3_arr, _, swir3_ndv = read_file(s3_fn)
    else:
        sys.exit("Check input files, missing proper input")
        break

    ndsi_3, ndsi_3_norm = calc_ndsi(green_arr, swir3_arr, g_ndv, swir3_ndv)

    # Write NDSI arrays to file
    with rio.Env():
        prf.update(
            dtype=rio.float32,
            count=1,
            compress='lzw')
        with rio.open(out_fn, 'w', **prf) as dst:
            dst.write(np.squeeze(ndsi_3).astype(rio.float32), 1)
        with rio.open(out_fn[:-4]+"_minmax.tif", 'w', **prf) as dst:
            dst.write(np.squeeze(ndsi_3_norm).astype(rio.float32), 1)

def get_parser():
    parser = argparse.ArgumentParser(description='Normalized Difference Snow Index Calculation Script')
    parser.add_argument('-in', '--MS_input_file', help='Multiband MS image file', required=False)
    parser.add_argument('-in2', '--SWIR_input_file', help='Multiband SWIR image file for WV3', required=False)
    parser.add_argument('-out', '--output_file', help='Where NDSI image is to be saved', default="ndsi.tif", required=False)
    parser.add_argument('-g', '--green_band', help='Single band green channel input', required=False)
    parser.add_argument('-s3', '--swir_3_band', help='Single band SWIR input', required=False)
    parser.add_argument('-res', '--px_res', help='Pixel resolution, default is 1.2 m', default="1.2", required=False)
    return parser

def main():
    parser = get_parser
    args = parser.parse_args()
    in_fn = args.MS_input_file
    swir_file = args.SWIR_input_file
    out_fn = args.output_file

    green_fn=args.green_band
    s3_fn=args.swir_3_band
    px_res=args.px_res
    p_name=px_res[0]+px_res[-1]
    
    run(in_fn, swir_file, out_fn, green_fn, s3_fn, px_res, p_name)
        
if __name__ == "__main__":    
    main()