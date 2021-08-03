#!/usr/bin/env python

# Script to calculate Normalized Difference Indices from input imagery (with WV-2 and WV-3 MS band or single-band inputs).
    
import argparse
import numpy as np
import rasterio as rio


# NEED TO ADD HANDLING FOR OTHER SENSORS, not just WV2 and WV3
#NDFSI = (nir - swir2)/(nir+swir2) -- LS OLI
#NDWI= (NIR - SWIR band 6) / (NIR + SWIR band 6)



def read_file(fn):
    with rio.open(fn) as f:
        arr=f.read()
        prf=f.profile
        ndv=f.nodata
    return arr, prf, ndv
    
def calc_ndi(b1_arr, b2_arr, ndv=9999):
    # Calculate NDVI
    ndi = (b2_arr - b1_arr) / (b2_arr + b1_arr)
    # Create normalized ndvi array from 0-1 for further processing with min-max scaling
    ndi_norm = (ndi+1)/2
    # Mask with ndv areas from original arrays
    ndi[b1_arr==ndv]=ndv
    ndi[b2_arr==ndv]=ndv
    ndi_norm[b1_arr==ndv]=ndv
    ndi_norm[b2_arr==ndv]=ndv
    return ndi, ndi_norm

def run(multi_band_file, multi_band_file2, out_fn, b1_fn, b2_fn, px_res, p_name):
    if multi_band_file is not None:
        if multi_band_file2 is not None:
            if ndfsi is not None:
                b1="_b2_"
                b2="_b7_"
            elif ndsi is not None:
                b2="_b3_"
                b1="_b3_"
            b1_arr, prf, ndv = read_file(multi_band_file2[:-4] + b1 + p_name + "_refl.tif")
            b2_arr, _, _ = read_file(multi_band_file[:-4] + b2 + p_name + "_refl.tif")
        else:
            if ndvi is not None:
                b1="_b5_"
                b2="_b7_"
            elif ndwi is not None:
                b1="_b3_"
                b2="_b7_"
        
            b1_arr, prf, ndv = read_file(multi_band_file[:-4] + b1 + p_name + "_refl.tif")
            b2_arr, _, _ = read_file(multi_band_file[:-4] + b2 + p_name + "_refl.tif")

    elif b1_fn is not None:
        b1_arr, prf, ndv = read_file(b1_fn)
        b2_arr, _, _ = read_file(b2_fn)
            
    ndi, ndi_norm = calc_ndi(b1_arr, b2_arr, ndv)
    
    # Write NDVI arrays to file
    with rio.Env():
        prf.update(
            dtype=rio.float32,
            count=1,
            compress='lzw')
        with rio.open(out_fn, 'w', **prf) as dst:
            dst.write(np.squeeze(ndi).astype(rio.float32), 1)
        with rio.open(out_fn[:-4]+"_minmax.tif", 'w', **prf) as dst:
            dst.write(np.squeeze(ndi_norm).astype(rio.float32), 1)

def get_parser():
    parser = argparse.ArgumentParser(description='Normalized Difference Vegetation Index Calculation Script')
    parser.add_argument('-in', '--MS_input_file', help='Multiband MS image file', required=False)
    parser.add_argument('-in2', '--MS2_input_file', help='Multiband SWIR image file', required=False)
    parser.add_argument('-out', '--output_file', help='NDVI output filename', default="ndvi.tif",  required=False)
    parser.add_argument('-r', '--red_band', help='Single-band red input', required=False)
    parser.add_argument('-n', '--nir_band', help='Single-band NIR channel input', required=False)
    parser.add_argument('-res', '--px_res', help='Pixel resolution, default is 1.2m', default="1.2", required=False)
    return parser

def main():
    parser = get_parser()
    args = parser.parse_args()
    in1 = args.MS_input_file
    in2 = args.MS2_input_file
    out_fn = args.output_file

    nir1_fn=args.nir_band
    red_fn=args.red_band
    px_res=args.px_res    
    p_name=px_res[0]+px_res[-1]

    run(in1, in2, out_fn, b1_fn, b2_fn, px_res, p_name)
    
if __name__ == "__main__":    
    main()
